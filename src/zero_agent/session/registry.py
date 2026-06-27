"""Session registry backed by SQLite."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from zero_agent.session.models import SessionKey, SessionRecord, SessionThreadRecord, ThreadStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    user_id TEXT,
    active_thread_id TEXT NOT NULL,
    locale TEXT NOT NULL,
    last_active_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS session_threads (
    thread_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    generation INTEGER NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_session_threads_session_id ON session_threads(session_id);
"""


class SessionRegistry:
    def __init__(
        self,
        db_path: str,
        default_locale: str = "zh",
        checkpoint_db_path: str | None = None,
    ) -> None:
        self._db_path = db_path
        self._default_locale = default_locale
        # Reserved for future TTL/archive of closed threads (step 11+).
        self._checkpoint_db_path = checkpoint_db_path
        self._conn: aiosqlite.Connection | None = None

    async def open(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def resolve_thread_id(self, key: SessionKey) -> str:
        record = await self._get_record(key)
        if record is None:
            now = datetime.now(UTC)
            thread_id = thread_id_for(key, 1)
            record = SessionRecord(
                key=key,
                active_thread_id=thread_id,
                locale=self._default_locale,
                generation=1,
                last_active_at=now,
            )
            await self._insert_session(record, started_at=now)
            return thread_id

        await self.touch(key)
        return record.active_thread_id

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
            now = datetime.now(UTC)
            thread_id = thread_id_for(key, 1)
            await self._insert_session(
                SessionRecord(
                    key=key,
                    active_thread_id=thread_id,
                    locale=locale,
                    generation=1,
                    last_active_at=now,
                ),
                started_at=now,
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

    async def list_threads(self, key: SessionKey) -> list[SessionThreadRecord]:
        conn = self._require_conn()
        cursor = await conn.execute(
            """
            SELECT thread_id, session_id, generation, status, started_at, ended_at
            FROM session_threads
            WHERE session_id = ?
            ORDER BY generation ASC
            """,
            (key.to_id(),),
        )
        rows = await cursor.fetchall()
        return [_row_to_thread(tuple(row)) for row in rows]

    async def reset(self, key: SessionKey) -> str:
        """Start a new conversation thread; old threads stay in session_threads."""
        record = await self._get_record(key)
        now = datetime.now(UTC)
        locale = self._default_locale
        generation = 1

        if record is None:
            thread_id = thread_id_for(key, generation)
            await self._insert_session(
                SessionRecord(
                    key=key,
                    active_thread_id=thread_id,
                    locale=locale,
                    generation=generation,
                    last_active_at=now,
                ),
                started_at=now,
            )
            return thread_id

        await self._close_active_thread(key, ended_at=now)
        generation = record.generation + 1
        new_thread_id = thread_id_for(key, generation)
        await self._activate_thread(
            key=key,
            thread_id=new_thread_id,
            generation=generation,
            locale=locale,
            started_at=now,
        )
        return new_thread_id

    def _require_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("SessionRegistry is not open")
        return self._conn

    async def _get_record(self, key: SessionKey) -> SessionRecord | None:
        conn = self._require_conn()
        cursor = await conn.execute(
            """
            SELECT s.platform, s.chat_id, s.user_id, s.active_thread_id, s.locale,
                   s.last_active_at, s.metadata_json, t.generation
            FROM sessions AS s
            JOIN session_threads AS t ON t.thread_id = s.active_thread_id
            WHERE s.session_id = ?
            """,
            (key.to_id(),),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_session_record(key.to_id(), tuple(row))

    async def _insert_session(self, record: SessionRecord, started_at: datetime) -> None:
        conn = self._require_conn()
        key = record.key
        await conn.execute(
            """
            INSERT INTO sessions (
                session_id, platform, chat_id, user_id, active_thread_id, locale, last_active_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.session_id,
                key.platform,
                key.chat_id,
                key.user_id,
                record.active_thread_id,
                record.locale,
                record.last_active_at.isoformat() if record.last_active_at else None,
                json.dumps(record.metadata),
            ),
        )
        await conn.execute(
            """
            INSERT INTO session_threads (
                thread_id, session_id, generation, status, started_at, ended_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record.active_thread_id,
                record.session_id,
                record.generation,
                ThreadStatus.ACTIVE,
                started_at.isoformat(),
                None,
            ),
        )
        await conn.commit()

    async def _close_active_thread(self, key: SessionKey, ended_at: datetime) -> None:
        conn = self._require_conn()
        await conn.execute(
            """
            UPDATE session_threads
            SET status = ?, ended_at = ?
            WHERE session_id = ? AND status = ?
            """,
            (ThreadStatus.CLOSED, ended_at.isoformat(), key.to_id(), ThreadStatus.ACTIVE),
        )
        await conn.commit()

    async def _activate_thread(
        self,
        key: SessionKey,
        thread_id: str,
        generation: int,
        locale: str,
        started_at: datetime,
    ) -> None:
        conn = self._require_conn()
        await conn.execute(
            """
            UPDATE sessions
            SET active_thread_id = ?, locale = ?, last_active_at = ?
            WHERE session_id = ?
            """,
            (thread_id, locale, started_at.isoformat(), key.to_id()),
        )
        await conn.execute(
            """
            INSERT INTO session_threads (
                thread_id, session_id, generation, status, started_at, ended_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                thread_id,
                key.to_id(),
                generation,
                ThreadStatus.ACTIVE,
                started_at.isoformat(),
                None,
            ),
        )
        await conn.commit()


def thread_id_for(key: SessionKey, generation: int) -> str:
    """Map session + generation to LangGraph thread_id."""
    base = key.to_id()
    if generation <= 1:
        return base
    return f"{base}:gen{generation}"


def _row_to_session_record(session_id: str, row: tuple[Any, ...]) -> SessionRecord:
    platform, chat_id, user_id, active_thread_id, locale, last_active_at, metadata_json, generation = row
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
        active_thread_id=str(active_thread_id),
        locale=str(locale),
        generation=int(generation),
        last_active_at=parsed_at,
        metadata=metadata if isinstance(metadata, dict) else {},
    )


def _row_to_thread(row: tuple[Any, ...]) -> SessionThreadRecord:
    thread_id, session_id, generation, status, started_at, ended_at = row
    return SessionThreadRecord(
        thread_id=str(thread_id),
        session_id=str(session_id),
        generation=int(generation),
        status=ThreadStatus(str(status)),
        started_at=datetime.fromisoformat(str(started_at)),
        ended_at=datetime.fromisoformat(ended_at) if ended_at else None,
    )
