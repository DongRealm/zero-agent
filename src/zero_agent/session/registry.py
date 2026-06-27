"""Session registry backed by SQLite."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from zero_agent.session.models import SessionKey, SessionRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    user_id TEXT,
    thread_id TEXT NOT NULL,
    locale TEXT NOT NULL,
    generation INTEGER NOT NULL DEFAULT 1,
    last_active_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
"""


class SessionRegistry:
    def __init__(self, db_path: str, default_locale: str = "zh") -> None:
        self._db_path = db_path
        self._default_locale = default_locale
        self._conn: aiosqlite.Connection | None = None

    async def open(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        await self._conn.execute(_SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def resolve_thread_id(self, key: SessionKey) -> str:
        record = await self._get_record(key)
        if record is None:
            now = datetime.now(UTC)
            record = SessionRecord(
                key=key,
                thread_id=key.to_id(),
                locale=self._default_locale,
                last_active_at=now,
            )
            await self._insert(record)
            return record.thread_id

        await self.touch(key)
        return record.thread_id

    async def touch(self, key: SessionKey) -> None:
        conn = self._require_conn()
        await conn.execute(
            "UPDATE sessions SET last_active_at = ? WHERE session_id = ?",
            (datetime.now(UTC).isoformat(), key.to_id()),
        )
        await conn.commit()

    async def get_locale(self, key: SessionKey) -> str:
        record = await self._get_record(key)
        if record is None:
            return self._default_locale
        return record.locale

    async def set_locale(self, key: SessionKey, locale: str) -> None:
        record = await self._get_record(key)
        if record is None:
            await self._insert(
                SessionRecord(
                    key=key,
                    thread_id=key.to_id(),
                    locale=locale,
                    last_active_at=datetime.now(UTC),
                )
            )
            return

        conn = self._require_conn()
        await conn.execute(
            "UPDATE sessions SET locale = ? WHERE session_id = ?",
            (locale, key.to_id()),
        )
        await conn.commit()

    async def get_record(self, key: SessionKey) -> SessionRecord | None:
        return await self._get_record(key)

    def _require_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("SessionRegistry is not open")
        return self._conn

    async def _get_record(self, key: SessionKey) -> SessionRecord | None:
        conn = self._require_conn()
        cursor = await conn.execute(
            """
            SELECT platform, chat_id, user_id, thread_id, locale, generation, last_active_at, metadata_json
            FROM sessions
            WHERE session_id = ?
            """,
            (key.to_id(),),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_record(key.to_id(), tuple(row))

    async def _insert(self, record: SessionRecord) -> None:
        conn = self._require_conn()
        key = record.key
        await conn.execute(
            """
            INSERT INTO sessions (
                session_id, platform, chat_id, user_id, thread_id, locale, generation, last_active_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.session_id,
                key.platform,
                key.chat_id,
                key.user_id,
                record.thread_id,
                record.locale,
                record.generation,
                record.last_active_at.isoformat() if record.last_active_at else None,
                json.dumps(record.metadata),
            ),
        )
        await conn.commit()


def _row_to_record(session_id: str, row: tuple[Any, ...]) -> SessionRecord:
    platform, chat_id, user_id, thread_id, locale, generation, last_active_at, metadata_json = row
    parsed_at = datetime.fromisoformat(last_active_at) if last_active_at else None
    metadata = json.loads(metadata_json)
    key = SessionKey(
        platform=str(platform),
        chat_id=str(chat_id),
        user_id=str(user_id) if user_id else None,
    )
    assert key.to_id() == session_id
    return SessionRecord(
        key=key,
        thread_id=str(thread_id),
        locale=str(locale),
        generation=int(generation),
        last_active_at=parsed_at,
        metadata=metadata if isinstance(metadata, dict) else {},
    )
