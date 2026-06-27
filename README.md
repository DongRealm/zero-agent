# Zero Agent

WeCom-first Code Self-Inspection agent service. A long-running daemon connects to enterprise WeChat (WeCom), routes inbound messages through session-aware dispatch, and invokes a [Deep Agents](https://github.com/langchain-ai/deepagents) graph for coding assistance.

## Architecture

```
Runner (ApplicationRunner, MessageDispatcher, lifecycle)
  └── Gateway (WecomAdapter, OutboundChannel)
        └── Session (SessionRegistry, checkpoints)
        └── Command (/reset, /lang — no LLM)
        └── Agent (AgentService → LangGraph / Deep Agents)
```

- **Gateway** normalizes platform frames into `MessageEvent`, handles per-session queuing, and sends replies via `OutboundChannel.reply`.
- **Session** maps `session_key` → `thread_id` and locale; `/reset` rotates threads without deleting checkpoints (TTL purge handles cleanup).
- **Command** handles local slash commands with i18n responses.
- **Agent** exposes `AgentService.invoke(thread_id, message)` as the public LLM entry point.

## Quick start

```bash
uv sync
cp .env.example .env
# Edit .env: OPENAI_* and WECOM_* credentials
uv run zero
```

The process writes a PID file to `{ZERO_DATA_DIR}/gateway.pid`, connects enabled gateway adapters, and runs until SIGINT/SIGTERM.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | LLM API key | — |
| `OPENAI_BASE_URL` | OpenAI-compatible base URL | — |
| `OPENAI_MODEL` | Model name | `gpt-3.5-turbo` |
| `ZERO_WORKSPACE_DIR` | Deep Agents filesystem root | `.` |
| `WECOM_BOT_ID` | WeCom bot ID (enables WeCom adapter when set) | — |
| `WECOM_BOT_SECRET` | WeCom bot secret | — |
| `ZERO_DATA_DIR` | SQLite data directory | `.local` |
| `ZERO_DEFAULT_LOCALE` | Default session locale (`zh` / `en`) | `zh` |
| `ZERO_SESSION_TTL_SECONDS` | Closed-thread checkpoint TTL | `604800` (7d) |
| `ZERO_LOG_LEVEL` | Log level | `INFO` |
| `ZERO_LOG_JSON` | JSON logs to stderr | `true` |

Session DB: `{ZERO_DATA_DIR}/session.db` · Checkpoints: `{ZERO_DATA_DIR}/checkpoints.db`

## Local commands

| Trigger | Action |
|---|---|
| `/reset`, `/new`, `重置`, `新对话` | Start a new conversation thread |
| `/lang zh`, `/lang en`, `/语言 中文` | Switch session locale |

Commands are handled before the LLM and reply with localized text.

## Public API

```python
from zero_agent.agent import AgentService, AgentResult
from zero_agent.settings import settings

service = AgentService.from_settings(settings)
result: AgentResult = await service.invoke(thread_id="wecom:chat1:user1:gen1", message="hello")
print(result.content)
```

For embedding or tests, inject a checkpointer and model:

```python
from langgraph.checkpoint.memory import MemorySaver
from tests.agent.helpers import ToolFakeChatModel

service = AgentService.from_settings(
    settings,
    checkpointer=MemorySaver(),
    model=ToolFakeChatModel(responses=["ok"]),
)
```

## MVP smoke checklist

Run automated checks first:

```bash
uv run pytest tests/integration/test_pipeline.py -q
```

Then verify on a real WeCom bot (or staging bot):

- [ ] **Startup** — `uv run zero` prints banner, logs `gateway.start`, no PID conflict
- [ ] **Connect** — logs `adapter.connect` / `adapter.authenticated` for `wecom`
- [ ] **Plain message** — send text; bot replies with LLM markdown within callback window
- [ ] **Multi-turn** — second message in same chat retains context (same session, same thread)
- [ ] **`/reset`** — bot confirms reset in current locale; next message starts fresh context
- [ ] **`/lang en`** then **`/lang zh`** — confirmation messages switch language; subsequent errors/commands follow locale
- [ ] **Logs** — JSON lines include `session_key` and `thread_id` on `dispatch.*` / `agent.invoke.*` events
- [ ] **Shutdown** — Ctrl+C drains and logs `gateway.stop`; PID file removed

## Development

```bash
# All tests
uv run pytest

# Integration pipeline only
uv run pytest tests/integration/ -q

# Lint & type check
uv run ruff check
uv run mypy src
```

## License

MIT License
