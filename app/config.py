from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings"""

    # LangGraph Model Configuration
    openai_api_key: str = ""
    model_name: str = "gpt-4"

    # Queue Configuration
    max_queue_size: int = 1000
    processing_timeout: int = 60  # seconds

    # SSE Configuration
    keepalive_interval: int = 30  # seconds

    # Application Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
