from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://app:app@db:5432/recovery_meal"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ai_mode: str = "fake"
    app_env: str = "development"
    upload_dir: str = "/app/uploads"
    max_upload_bytes: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

