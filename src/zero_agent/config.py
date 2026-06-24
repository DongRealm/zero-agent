import json
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProjectConfig(BaseSettings):
    """Configuration for a single tracked project."""

    model_config = SettingsConfigDict(extra="ignore")

    name: str
    repo_path: str
    language: str = "java"
    review_interval_hour: int = 6


class ZeroConfig(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ZERO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")
    openai_api_key: SecretStr | None = Field(default=SecretStr("sk-placeholder"), validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", validation_alias="OPENAI_MODEL")

    # Storage
    data_dir: str = Field(default=".local", description="Directory to store data")

    @property
    def db_path(self) -> str:
        """Path to the database file."""
        return f"{self.data_dir}/zero.db"

    @property
    def projects_file_path(self) -> str:
        """Path to the projects file."""
        return f"{self.data_dir}/projects.json"

    # Projects
    projects: list[ProjectConfig] = Field(default_factory=list)


def load_config() -> ZeroConfig:
    """Load configuration. Projects are loaded from the projects.json if exists."""
    config = ZeroConfig()

    Path(config.data_dir).mkdir(parents=True, exist_ok=True)

    projects_file = Path(config.projects_file_path)
    if projects_file.exists():
        raw = json.loads(projects_file.read_text(encoding="utf-8"))
        config = config.model_copy(update={"projects": [ProjectConfig(**p) for p in raw]})

    return config
