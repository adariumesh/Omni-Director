"""Brand Guidelines Loader for FIBO Omni-Director Pro."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ColorGuideline:
    """Brand color guideline."""
    name: str
    hex_code: str
    rgb: List[int]
    usage: str  # primary, accent, secondary, neutral
    description: str
    accessibility_rating: str = "AA"


@dataclass
class TypographyGuideline:
    """Typography guideline."""
    font_family: str
    font_size_range: List[int]
    line_height_ratio: float
    letter_spacing: float
    usage: str  # heading, body, caption
    font_weight: str


@dataclass
class StyleGuideline:
    """Visual style guidelines."""
    image_style: str  # corporate, creative, minimal, etc.
    contrast_requirements: Dict[str, float]
    saturation_range: List[float]
    brightness_range: List[float]
    aspect_ratios: List[str]
    prohibited_elements: List[str]


@dataclass
class BrandGuidelinesSpec:
    """Complete brand guidelines specification."""
    brand_name: str
    version: str
    colors: List[ColorGuideline]
    typography: List[TypographyGuideline]
    style: StyleGuideline
    logo: Optional[str] = None
    custom_rules: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BrandGuidelinesLoader:
    """Loads and manages brand guidelines from JSON files."""
    
    def __init__(self, guidelines_dir: str = "./backend/data/brand_guidelines"):
        """Initialize loader.
        
        Args:
            guidelines_dir: Directory containing brand guideline files.
        """
        self.guidelines_dir = Path(guidelines_dir)
        self.loaded_guidelines: Dict[str, BrandGuidelinesSpec] = {}
        
    def load_guidelines(self, brand_name: Optional[str] = None) -> Optional[BrandGuidelinesSpec]:
        """Load brand guidelines from file.
        
        Args:
            brand_name: Specific brand name to load, or None for latest.
            
        Returns:
            BrandGuidelinesSpec or None if not found.
        """
        try:
            if brand_name:
                # Look for specific brand
                pattern = f"{brand_name.lower().replace(' ', '')}*.json"
                files = list(self.guidelines_dir.glob(pattern))
            else:
                # Get most recent guideline file
                files = list(self.guidelines_dir.glob("*.json"))
                
            if not files:
                logger.warning(f"No brand guidelines found in {self.guidelines_dir}")
                return None
                
            # Sort by modification time to get latest
            latest_file = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
            
            return self._load_from_file(latest_file)
            
        except Exception as e:
            logger.error(f"Failed to load brand guidelines: {e}")
            return None
    
    def _load_from_file(self, file_path: Path) -> BrandGuidelinesSpec:
        """Load guidelines from specific file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Parse colors
        colors = [
            ColorGuideline(
                name=color["name"],
                hex_code=color["hex_code"],
                rgb=color["rgb"],
                usage=color["usage"],
                description=color["description"],
                accessibility_rating=color.get("accessibility_rating", "AA")
            )
            for color in data.get("colors", [])
        ]
        
        # Parse typography
        typography = [
            TypographyGuideline(
                font_family=typo["font_family"],
                font_size_range=typo["font_size_range"],
                line_height_ratio=typo["line_height_ratio"],
                letter_spacing=typo["letter_spacing"],
                usage=typo["usage"],
                font_weight=typo["font_weight"]
            )
            for typo in data.get("typography", [])
        ]
        
        # Parse style
        style_data = data.get("style", {})
        style = StyleGuideline(
            image_style=style_data.get("image_style", "corporate"),
            contrast_requirements=style_data.get("contrast_requirements", {}),
            saturation_range=style_data.get("saturation_range", [0.0, 1.0]),
            brightness_range=style_data.get("brightness_range", [0.0, 1.0]),
            aspect_ratios=style_data.get("aspect_ratios", ["1:1"]),
            prohibited_elements=style_data.get("prohibited_elements", [])
        )
        
        # Parse timestamps
        created_at = None
        updated_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except:
                pass
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(data["updated_at"])
            except:
                pass
        
        guidelines = BrandGuidelinesSpec(
            brand_name=data.get("brand_name", "Unknown Brand"),
            version=data.get("version", "1.0"),
            colors=colors,
            typography=typography,
            style=style,
            logo=data.get("logo"),
            custom_rules=data.get("custom_rules", {}),
            created_at=created_at,
            updated_at=updated_at
        )
        
        # Cache the loaded guidelines
        self.loaded_guidelines[guidelines.brand_name] = guidelines
        
        logger.info(f"Loaded brand guidelines for '{guidelines.brand_name}' v{guidelines.version}")
        
        return guidelines
    
    def get_color_palette(self, guidelines: BrandGuidelinesSpec) -> Dict[str, str]:
        """Get color palette as hex codes.
        
        Args:
            guidelines: Brand guidelines specification.
            
        Returns:
            Dictionary mapping color usage to hex codes.
        """
        return {color.usage: color.hex_code for color in guidelines.colors}
    
    def get_primary_colors(self, guidelines: BrandGuidelinesSpec) -> List[str]:
        """Get primary brand colors.
        
        Args:
            guidelines: Brand guidelines specification.
            
        Returns:
            List of primary color hex codes.
        """
        primary_colors = [color.hex_code for color in guidelines.colors if color.usage == "primary"]
        return primary_colors
    
    def validate_colors(self, guidelines: BrandGuidelinesSpec, colors: List[str]) -> Dict[str, bool]:
        """Validate if colors comply with brand guidelines.
        
        Args:
            guidelines: Brand guidelines specification.
            colors: List of color hex codes to validate.
            
        Returns:
            Dictionary mapping colors to compliance status.
        """
        brand_colors = [color.hex_code.upper() for color in guidelines.colors]
        
        results = {}
        for color in colors:
            color_upper = color.upper()
            results[color] = color_upper in brand_colors
            
        return results
    
    def get_style_requirements(self, guidelines: BrandGuidelinesSpec) -> Dict[str, Any]:
        """Get style requirements for image generation.
        
        Args:
            guidelines: Brand guidelines specification.
            
        Returns:
            Dictionary of style requirements.
        """
        return {
            "image_style": guidelines.style.image_style,
            "allowed_aspect_ratios": guidelines.style.aspect_ratios,
            "saturation_range": guidelines.style.saturation_range,
            "brightness_range": guidelines.style.brightness_range,
            "prohibited_elements": guidelines.style.prohibited_elements,
            "contrast_requirements": guidelines.style.contrast_requirements
        }
    
    def generate_negative_prompt(self, guidelines: BrandGuidelinesSpec) -> str:
        """Generate negative prompt based on prohibited elements.
        
        Args:
            guidelines: Brand guidelines specification.
            
        Returns:
            Negative prompt string.
        """
        prohibited = guidelines.style.prohibited_elements
        
        # Base negative prompt
        negative_elements = [
            "low quality", "blurry", "distorted", "ugly", "bad anatomy",
            "text", "logo", "signature", "username", "watermark"
        ]
        
        # Add brand-specific prohibitions
        if "watermarks" in prohibited:
            negative_elements.extend(["watermark", "logo overlay", "brand mark"])
        
        if "text_overlays" in prohibited:
            negative_elements.extend(["text overlay", "caption", "subtitle"])
            
        if "borders" in prohibited:
            negative_elements.extend(["frame", "border", "edge decoration"])
        
        return ", ".join(negative_elements)
    
    def create_generation_params(self, guidelines: BrandGuidelinesSpec) -> Dict[str, Any]:
        """Create generation parameters based on brand guidelines.
        
        Args:
            guidelines: Brand guidelines specification.
            
        Returns:
            Dictionary of generation parameters.
        """
        style_map = {
            "corporate": "professional, clean, business-like, polished",
            "creative": "artistic, imaginative, vibrant, expressive",
            "minimal": "clean, simple, minimal, elegant, sophisticated",
            "modern": "contemporary, sleek, trendy, current",
            "classic": "timeless, traditional, refined, elegant"
        }
        
        style_prompt = style_map.get(guidelines.style.image_style, "professional")
        
        # Get primary colors for prompting
        primary_colors = self.get_primary_colors(guidelines)
        color_description = ""
        if primary_colors:
            color_names = [color.name for color in guidelines.colors if color.usage == "primary"]
            color_description = f", {', '.join(color_names).lower()}"
        
        return {
            "style_modifier": style_prompt + color_description,
            "negative_prompt": self.generate_negative_prompt(guidelines),
            "aspect_ratios": guidelines.style.aspect_ratios,
            "quality_requirements": {
                "min_resolution": (1024, 1024),
                "preferred_format": "PNG"
            }
        }
    
    def list_available_brands(self) -> List[str]:
        """List all available brand guidelines.
        
        Returns:
            List of available brand names.
        """
        brands = []
        try:
            for file_path in self.guidelines_dir.glob("*.json"):
                guidelines = self._load_from_file(file_path)
                brands.append(guidelines.brand_name)
        except Exception as e:
            logger.error(f"Error listing brands: {e}")
            
        return brands