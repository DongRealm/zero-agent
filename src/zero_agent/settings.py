from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ZERO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # LLM
    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")
    openai_api_key: SecretStr | None = Field(default=SecretStr("sk-placeholder"), validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", validation_alias="OPENAI_MODEL")

    # Agent
    workspace_dir: str = Field(
        default=".",
        description="Agent workspace root for Deep Agents filesystem backend (notes and personal files)",
    )

    # Tavily
    tavily_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="TAVILY_API_KEY")

    # Gateway
    wecom_bot_id: str | None = Field(default=None, validation_alias="WECOM_BOT_ID")
    wecom_bot_secret: SecretStr = Field(default=SecretStr(""), validation_alias="WECOM_BOT_SECRET")

    # Storage
    data_dir: str = Field(default=".local", description="Directory to store data")
    session_db_path: str | None = Field(
        default=None,
        description="Path to session registry database; defaults to {data_dir}/session.db",
    )
    checkpoint_db_path: str | None = Field(
        default=None,
        description="Path to LangGraph checkpoint database; defaults to {data_dir}/checkpoints.db",
    )
    default_locale: str = Field(default="zh", description="Default locale for new sessions")
    log_level: str = Field(default="INFO", description="Root log level (DEBUG, INFO, WARNING, ...)")
    log_json: bool = Field(default=True, description="Emit structured JSON logs to stderr")
    session_ttl_seconds: int = Field(
        default=604_800,
        description="TTL for closed session threads before checkpoint purge (default 7 days)",
    )

    @property
    def resolved_session_db_path(self) -> str:
        if self.session_db_path:
            return self.session_db_path
        return f"{self.data_dir}/session.db"

    @property
    def resolved_checkpoint_db_path(self) -> str:
        if self.checkpoint_db_path:
            return self.checkpoint_db_path
        return f"{self.data_dir}/checkpoints.db"

    @property
    def db_path(self) -> str:
        """Deprecated alias for resolved_session_db_path."""
        return self.resolved_session_db_path


settings = Settings()
