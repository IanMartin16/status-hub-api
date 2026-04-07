from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Status Hub API"
    app_env: str = "dev"
    app_version: str = "0.1.0"
    port: int = 8080

    database_url: str = "sqlite:///./data/status_hub.db"

    status_check_interval_seconds: int = 60
    status_timeout_seconds: int = 5
    status_degraded_threshold_ms: int = 2000

    admin_token: str = "change-me"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()