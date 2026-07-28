from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # app
    app_env: str = "development"
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # database
    database_url: str

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"

@lru_cache()
def get_settings() -> AppSettings:
    return AppSettings()

    