from zero_agent.settings import Settings


def test_resolved_session_db_path_default() -> None:
    settings = Settings(data_dir=".local")
    assert settings.resolved_session_db_path == ".local/session.db"
    assert settings.db_path == settings.resolved_session_db_path


def test_resolved_session_db_path_override() -> None:
    settings = Settings(session_db_path="/tmp/custom.db")
    assert settings.resolved_session_db_path == "/tmp/custom.db"


def test_resolved_checkpoint_db_path_default() -> None:
    settings = Settings(data_dir=".local")
    assert settings.resolved_checkpoint_db_path == ".local/checkpoints.db"


def test_resolved_checkpoint_db_path_override() -> None:
    settings = Settings(checkpoint_db_path="/tmp/checkpoints.db")
    assert settings.resolved_checkpoint_db_path == "/tmp/checkpoints.db"


def test_session_ttl_seconds_default() -> None:
    settings = Settings()
    assert settings.session_ttl_seconds == 604_800


def test_session_ttl_seconds_override() -> None:
    settings = Settings(session_ttl_seconds=3600)
    assert settings.session_ttl_seconds == 3600


def test_workspace_dir_default() -> None:
    settings = Settings()
    assert settings.workspace_dir == "."


def test_workspace_dir_override() -> None:
    settings = Settings(workspace_dir="/tmp/workspace")
    assert settings.workspace_dir == "/tmp/workspace"

