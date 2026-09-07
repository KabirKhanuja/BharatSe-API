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

    # Firebase is the identity provider. Only the project id is needed: ID
    # tokens are verified against Google's public certificates, so there is no
    # service account key to store or leak.
    FIREBASE_PROJECT_ID: str = ""

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

    # Separate key for the voice to listing call, so it can sit on a project
    # with no billing and stay on the free tier.
    #
    # This is not belt and braces. Enabling billing moves a project to a paid
    # tier wholesale; there is no free allowance running alongside it. The image
    # model has no free tier at all, so the moment billing is switched on for
    # pictures, every description starts billing too. Two keys keeps the voice
    # path genuinely free.
    #
    # Falls back to GEMINI_API_KEY when unset, so nothing breaks if it is not
    # configured.
    GEMINI_LISTING_API_KEY: str = ""

    BHASHINI_USER_ID: str = ""
    BHASHINI_ULCA_API_KEY: str = ""
    BHASHINI_PIPELINE_ID: str = "64392f96daac500b55c543cd"

    SARVAM_API_KEY: str = ""

    # Image studio. The primary path is generative: Gemini redraws the piece on
    # a clean background rather than subtracting the old one. rembg stays as the
    # offline fallback.
    #
    # Never leave REMBG_MODEL unset in code. rembg's default is BRIA RMBG, which
    # requires a paid commercial agreement. isnet-general-use is Apache 2.0.
    GEMINI_IMAGE_MODEL: str = "gemini-3-pro-image"
    IMAGE_ASPECT_RATIO: str = "1:1"
    REMBG_MODEL: str = "isnet-general-use"
    REPLICATE_API_TOKEN: str = ""

    # Supabase. Storage uses the service role key, which must never reach the
    # app: it bypasses row level security by design.
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "product-assets"

    PRICE_MODEL_DIR: str = "data/models"
    FAIR_WAGE_PER_HOUR: int = 60

    PASSPORT_PRIVATE_KEY_HEX: str = ""
    PASSPORT_PUBLIC_KEY_HEX: str = ""

    @property
    def listing_api_key(self) -> str:
        """Key for the voice to listing call. Free tier key when there is one."""
        return self.GEMINI_LISTING_API_KEY or self.GEMINI_API_KEY

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
