import asyncio
import contextlib
import signal
import sys

from zero_agent import __version__
from zero_agent.config import load_config


async def _async_main() -> None:
    """Async main entry point."""
    config = load_config()

    print(" ┌────────────────────────────────────────┐")
    print(f" │          Zero Agent v{__version__}             │")
    print(" │     Code Self-Inspection Service       │")
    print(" └────────────────────────────────────────┘")
    print()
    print(f"  Model: {config.openai_model}")
    print(f"  Data: {config.data_dir}")
    print(f"  Projects: {len(config.projects)}")
    for project in config.projects:
        print(f"    {project.name} ({project.language}) → {project.repo_path}")
    print()

    if not config.projects:
        print(f"  No projects configured. Please add projects to {config.projects_file_path}")
        print('  Example: [{"name": "my-project", "repo_path": "path/to/repo"}]')
        sys.exit(0)

    print("  Zero Agent ready. Pleace Ctrl+C to stop.")
    print()

    # Gracefully shutdown
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()
    print("\n  Shutting down...")


def main() -> None:
    """Start the Zero Agent service."""
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_async_main())


if __name__ == "__main__":
    main()
