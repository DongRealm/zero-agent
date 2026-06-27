import asyncio

from zero_agent import __version__
from zero_agent.gateway.runner import start_gateway
from zero_agent.settings import settings


def main() -> None:
    print(" ┌────────────────────────────────────────┐")
    print(f" │          Zero Agent v{__version__}             │")
    print(" │     Code Self-Inspection Service       │")
    print(" └────────────────────────────────────────┘")
    print()
    print(f"  Model: {settings.openai_model}")
    print(f"  Data: {settings.data_dir}")

    print("  Zero Agent ready. Pleace Ctrl+C to stop.")
    print()

    success = asyncio.run(start_gateway())
    if not success:
        exit(1)


if __name__ == "__main__":
    main()
