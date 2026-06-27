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
