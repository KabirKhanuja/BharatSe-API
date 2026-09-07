"""Application settings, read once from the environment."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "BharatSe API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+psycopg://bharatse:bharatse@localhost:5432/bharatse"

    SECRET_KEY: str = "change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # NoDecode matters. Without it pydantic-settings tries to JSON decode any
    # list field read from .env, so a plain comma separated value raises at
    # import time before the validator below ever runs.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)

    LISTING_PROVIDER: Literal["gemini", "bhashini", "sarvam"] = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    BHASHINI_USER_ID: str = ""
    BHASHINI_ULCA_API_KEY: str = ""
    BHASHINI_PIPELINE_ID: str = "64392f96daac500b55c543cd"

    SARVAM_API_KEY: str = ""

    # Never leave this unset in code. rembg's default model is BRIA RMBG, which
    # requires a paid commercial agreement. isnet-general-use is Apache 2.0.
    REMBG_MODEL: str = "isnet-general-use"
    REPLICATE_API_TOKEN: str = ""

    PRICE_MODEL_DIR: str = "data/models"
    FAIR_WAGE_PER_HOUR: int = 60

    PASSPORT_PRIVATE_KEY_HEX: str = ""
    PASSPORT_PUBLIC_KEY_HEX: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
