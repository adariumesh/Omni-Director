"""Backend configuration using Pydantic Settings."""

import logging
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogFormat(str, Enum):
    """Log formats."""
    TEXT = "text"
    JSON = "json"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Configuration
    bria_api_key: str = ""
    bria_api_base_url: str = "https://engine.prod.bria-api.com/v1"
    openai_api_key: str = ""

    # Database Configuration
    database_url: str = "sqlite:///./data/omni_director.db"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Environment
    environment: Environment = Environment.DEVELOPMENT

    # Logging
    log_level: LogLevel = LogLevel.INFO
    log_format: LogFormat = LogFormat.TEXT

    # Security
    secret_key: str = "change-me-in-production"
    allowed_origins: List[str] = ["http://localhost:8501", "http://127.0.0.1:8501"]

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # File Storage
    max_file_size: int = 10485760  # 10MB
    upload_path: Path = Path("./data/uploads")

    # Paths
    data_dir: Path = Path("./data")
    images_dir: Path = Path("./data/images")

    def __init__(self, **kwargs) -> None:
        """Initialize settings and create directories."""
        super().__init__(**kwargs)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.upload_path.mkdir(parents=True, exist_ok=True)

    def setup_logging(self) -> None:
        """Setup logging configuration based on environment."""
        level = getattr(logging, self.log_level.value)
        
        if self.log_format == LogFormat.JSON:
            import json
            import sys
            
            class JSONFormatter(logging.Formatter):
                def format(self, record):
                    log_data = {
                        'timestamp': self.formatTime(record),
                        'level': record.levelname,
                        'logger': record.name,
                        'message': record.getMessage(),
                        'module': record.module,
                        'function': record.funcName,
                        'line': record.lineno,
                    }
                    if record.exc_info:
                        log_data['exception'] = self.formatException(record.exc_info)
                    return json.dumps(log_data)
            
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == Environment.DEVELOPMENT


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings instance loaded from environment.
    """
    return Settings()


settings = get_settings()
