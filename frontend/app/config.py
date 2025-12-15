"""Frontend configuration."""

from dataclasses import dataclass


@dataclass
class FrontendConfig:
    """Frontend configuration settings."""

    backend_url: str = "http://localhost:8000"
    page_title: str = "FIBO Omni-Director Pro"
    page_icon: str = "🎬"
    layout: str = "wide"

    # Matrix settings
    matrix_size: int = 3
    default_aspect_ratio: str = "1:1"

    # UI settings
    image_width: int = 300
    thumbnail_width: int = 150


config = FrontendConfig()
