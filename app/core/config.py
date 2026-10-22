from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Finance Assistant API"
    APP_ENV: Literal["development", "production", "test"] = "development"
    DEBUG: bool = False

    DB_HOST: str
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASS: SecretStr
    DB_NAME: str

    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    COOKIE_PATH: str = "/"
    COOKIE_DOMAIN: str = ""

    # NoDecode отключает предварительное JSON-декодирование pydantic-settings
    # для list-полей. Без него строка "http://localhost:3000" вызывает SettingsError
    # ещё до вызова нашего валидатора.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.DB_USER,
            password=self.DB_PASS.get_secret_value(),
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
