from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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

    # Gateway
    wecom_bot_id: str | None = Field(default=None, validation_alias="WECOM_BOT_ID")
    wecom_bot_secret: SecretStr = Field(default=SecretStr(""), validation_alias="WECOM_BOT_SECRET")

    # Storage
    data_dir: str = Field(default=".local", description="Directory to store data")
    session_db_path: str | None = Field(
        default=None,
        description="Path to session registry database; defaults to {data_dir}/session.db",
    )
    default_locale: str = Field(default="zh", description="Default locale for new sessions")

    @property
    def resolved_session_db_path(self) -> str:
        if self.session_db_path:
            return self.session_db_path
        return f"{self.data_dir}/session.db"

    @property
    def db_path(self) -> str:
        """Deprecated alias for resolved_session_db_path."""
        return self.resolved_session_db_path


settings = Settings()
