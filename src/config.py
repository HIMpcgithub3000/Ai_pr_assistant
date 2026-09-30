from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pr_assistant"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "pr_assistant"
    POSTGRES_PORT: int = 5432

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PORT: int = 6379

    # GitHub App
    GITHUB_APP_ID: str | None = None
    GITHUB_APP_PRIVATE_KEY_PATH: str | None = None
    GITHUB_WEBHOOK_SECRET: str = "development_webhook_secret_12345"
    GITHUB_TOKEN: str | None = None

    # LLM Settings
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    LLM_PROVIDER: str = "mock"  # "mock", "openai", "anthropic"

    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "ai-pr-assistant"

    # Sandbox and Git Cache
    GIT_CACHE_DIR: str = "./cache/git"
    SANDBOX_TIMEOUT_SECONDS: int = 60
    SANDBOX_IMAGE: str = "python:3.11-slim"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
