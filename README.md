# Zero Agent

Zero Agent is a personal assistant service built around enterprise WeChat (WeCom). It runs as a long-lived process that receives messages over the WeCom bot long-connection API, maintains per-user session state, and routes conversation to a [Deep Agents](https://github.com/langchain-ai/deepagents) graph backed by LangGraph.

Zero helps with problem-solving and organization in chat. Additional capabilities such as daily planning and proactive reminders are planned for future releases.

## Features

- **WeCom gateway** — WebSocket adapter with in-callback replies, streaming progress, and proactive push
- **Session management** — SQLite registry mapping chat sessions to LangGraph `thread_id`, locale persistence, and thread rotation on `/reset`
- **Local commands** — `/reset`, `/lang`, and `/help` handled without LLM calls; responses are localized (Chinese and English)
- **Structured logging** — JSON logs with `session_key` and `thread_id` correlation across gateway, dispatcher, and agent runs
- **Embeddable agent API** — `AgentService.invoke()` for programmatic use outside the WeCom daemon

## Architecture

```
Runner (ApplicationRunner, MessageDispatcher, lifecycle)
  └── Gateway (WecomAdapter, OutboundChannel)
        └── Session (SessionRegistry, checkpoints)
        └── Command (/reset, /lang, /help)
        └── Agent (AgentService → LangGraph / Deep Agents)
```

| Layer | Responsibility |
|---|---|
| **Runner** | Process lifecycle, adapter wiring, message dispatch |
| **Gateway** | Platform protocol translation, outbound delivery, per-session queuing |
| **Session** | Session index, locale, thread history; checkpoint TTL for closed threads |
| **Command** | Slash commands and i18n replies |
| **Agent** | LLM invocation and conversation state via LangGraph checkpoints |

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or another PEP 517 installer
- OpenAI-compatible LLM API credentials
- WeCom AI bot credentials (`WECOM_BOT_ID`, `WECOM_BOT_SECRET`) for the gateway

## Installation

From the repository root:

```bash
uv sync
cp .env.example .env
```

Edit `.env` with your LLM and WeCom settings, then start the service:

```bash
uv run zero
```

On startup the process writes a PID file to `{ZERO_DATA_DIR}/gateway.pid`, connects configured gateway adapters, and runs until SIGINT or SIGTERM.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | LLM API key | — |
| `OPENAI_BASE_URL` | OpenAI-compatible API base URL | — |
| `OPENAI_MODEL` | Model name | `gpt-3.5-turbo` |
| `ZERO_WORKSPACE_DIR` | Agent workspace root (notes and files for tools) | `.` |
| `WECOM_BOT_ID` | WeCom bot ID; enables the WeCom adapter when set | — |
| `WECOM_BOT_SECRET` | WeCom bot secret | — |
| `ZERO_DATA_DIR` | Runtime data directory | `.local` |
| `ZERO_DEFAULT_LOCALE` | Default session locale (`zh` or `en`) | `zh` |
| `ZERO_SESSION_TTL_SECONDS` | TTL before purging checkpoints for closed threads | `604800` (7 days) |
| `ZERO_LOG_LEVEL` | Root log level | `INFO` |
| `ZERO_LOG_JSON` | Emit structured JSON logs to stderr | `true` |

Persistent storage (under `ZERO_DATA_DIR` by default):

- `{ZERO_DATA_DIR}/session.db` — session registry
- `{ZERO_DATA_DIR}/checkpoints.db` — LangGraph checkpoints

See `.env.example` for the full list of supported variables.

## Commands

Commands are matched before the agent runs and answered with localized text.

| Trigger | Action |
|---|---|
| `/reset`, `/new`, `重置`, `新对话` | Start a new conversation thread |
| `/lang zh`, `/lang en`, `/语言 中文`, `/语言 en` | Switch session locale |
| `/help`, `帮助` | List available commands |

Send `/help` (or `帮助`) in chat to see the current list in your session language.

## Programmatic use

The agent layer can be used independently of the WeCom gateway:

```python
from zero_agent.agent import AgentService, AgentResult
from zero_agent.settings import settings

service = AgentService.from_settings(settings)
result: AgentResult = await service.invoke(
    thread_id="wecom:chat1:user1:gen1",
    message="hello",
)
print(result.content)
```

For tests or custom wiring, inject a checkpointer and model:

```python
from langgraph.checkpoint.memory import MemorySaver
from tests.agent.helpers import ToolFakeChatModel

service = AgentService.from_settings(
    settings,
    checkpointer=MemorySaver(),
    model=ToolFakeChatModel(responses=["ok"]),
)
```

## Development

Install dev dependencies and run the test suite:

```bash
uv sync --extra dev
uv run pytest
```

Other useful commands:

```bash
uv run pytest tests/integration/ -q   # end-to-end pipeline
uv run ruff check src tests
uv run mypy src
```

## License

This project is licensed under the [MIT License](LICENSE).
