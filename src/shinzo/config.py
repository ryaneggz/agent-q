import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings"""
    
    model_config = ConfigDict(
        extra='ignore',
        env_file='.env',
        env_file_encoding='utf-8'
    )

    # LangGraph/OpenAI Model Configuration
    openai_api_key: str = ""
    model: str = "xai:grok-4-1-fast"

    # Anthropic Configuration
    anthropic_api_key: Optional[str] = None
    anthropic_model_name: Optional[str] = None

    # xAI (Grok) Configuration
    xai_api_key: Optional[str] = None
    xai_model_name: Optional[str] = None

    # Google Generative AI / Gemini Configuration
    google_genai_api_key: Optional[str] = None
    google_genai_model_name: Optional[str] = None
    google_api_key: Optional[str] = None  # Alias for google_genai_api_key

    # Groq Configuration
    groq_api_key: Optional[str] = None
    groq_model_name: Optional[str] = None

    # --- OS API Key Support ---
    # Allow loading of any supported model provider's API key from a generic OS API key environment variable
    os_api_key: Optional[str] = None

    def __init__(self, **kwargs):
        # First, ask pydantic settings to initialize as usual
        super().__init__(**kwargs)

        # Handle google_api_key as an alias for google_genai_api_key
        if self.google_api_key and not self.google_genai_api_key:
            self.google_genai_api_key = self.google_api_key

        # Apply os_api_key to any unset model provider keys
        os_api_key = self.os_api_key or os.environ.get("OS_API_KEY")
        if os_api_key:
            if not self.openai_api_key:
                self.openai_api_key = os_api_key
            if not self.anthropic_api_key:
                self.anthropic_api_key = os_api_key
            if not self.xai_api_key:
                self.xai_api_key = os_api_key
            if not self.google_genai_api_key:
                self.google_genai_api_key = os_api_key
            if not self.groq_api_key:
                self.groq_api_key = os_api_key

        # Set environment variables for LangChain's init_chat_model to use
        if self.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.openai_api_key
        if self.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.anthropic_api_key
        if self.xai_api_key:
            os.environ["XAI_API_KEY"] = self.xai_api_key
        if self.google_genai_api_key:
            os.environ["GOOGLE_API_KEY"] = self.google_genai_api_key
        if self.groq_api_key:
            os.environ["GROQ_API_KEY"] = self.groq_api_key

    # Queue Configuration
    max_queue_size: int = 1000
    processing_timeout: int = 60  # seconds

    # SSE Configuration
    keepalive_interval: int = 30  # seconds

    # Application Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


# Global settings instance
settings = Settings()
