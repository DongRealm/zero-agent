import asyncio

from zero_agent import __version__
from zero_agent.observability.setup import configure_logging
from zero_agent.runner.app import run_application
from zero_agent.settings import settings


def main() -> None:
    configure_logging(level=settings.log_level, json=settings.log_json)

    width = 40
    print(" ┌" + "─" * width + "┐")
    print(f" │{'Zero · Personal Assistant':^{width}}│")
    print(f" │{f'v{__version__}':^{width}}│")
    print(" └" + "─" * width + "┘")
    print()
    print(f"  Model: {settings.openai_model}")
    print(f"  Data: {settings.data_dir}")

    print("  Ready. Press Ctrl+C to stop.")
    print()

    success = asyncio.run(run_application())
    if not success:
        exit(1)


if __name__ == "__main__":
    main()
