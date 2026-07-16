from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = ""
    database_url: str = "postgresql+asyncpg://nosmoke:nosmoke@db:5432/nosmoke"
    webapp_url: str = "https://example.com"
    port: int = 8080
    dev_mode: bool = False
    init_data_max_age: int = 86400

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
