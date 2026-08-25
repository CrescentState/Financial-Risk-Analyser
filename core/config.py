import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Set default values or allow Optional for testing/mocking environments
    ALPHA_VANTAGE_API_KEY: str = Field(default="", validation_alias="ALPHA_VANTAGE_KEY")
    GEMINI_API_KEY: str = Field(default="", validation_alias="GEMINI_API_KEY")
    
    # Configurations
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    AV_RATE_LIMIT_DELAY: int = 15
    NEWS_LOOKBACK_DAYS: int = 30
    MAX_NEWS_ARTICLES: int = 10
    HOSTILE_NEWS_THRESHOLD: float = -0.4

    # Pydantic v2 modern settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()