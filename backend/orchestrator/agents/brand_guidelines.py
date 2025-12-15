"""
Brand Guidelines Management System for FIBO Omni-Director Pro.
Manages brand asset libraries, style guidelines, and validation rules.
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import colorsys
import hashlib

from app.models.database import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class ColorGuideline:
    """Brand color specification."""
    name: str
    hex_code: str
    rgb: tuple[int, int, int]
    usage: str  # primary, secondary, accent, neutral
    description: str = ""
    accessibility_rating: str = "AA"  # AA, AAA
    
    @classmethod
    def from_hex(cls, name: str, hex_code: str, usage: str, description: str = "") -> 'ColorGuideline':
        """Create ColorGuideline from hex code."""
        hex_code = hex_code.lstrip('#')
        rgb = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        return cls(name, f"#{hex_code}", rgb, usage, description)


@dataclass
class TypographyGuideline:
    """Typography specifications."""
    font_family: str
    font_size_range: tuple[int, int]  # min, max
    line_height_ratio: float
    letter_spacing: float
    usage: str  # heading, body, caption, accent
    font_weight: str = "normal"  # normal, bold, light
    
    
@dataclass
class LogoGuideline:
    """Logo usage guidelines."""
    logo_path: str
    min_size_px: tuple[int, int]
    clear_space_ratio: float  # ratio of logo height
    background_colors: List[str]  # allowed background hex codes
    prohibited_modifications: List[str]
    file_formats: List[str] = field(default_factory=lambda: ["PNG", "SVG"])


@dataclass
class StyleGuideline:
    """Visual style guidelines."""
    image_style: str  # photographic, illustration, minimal, corporate
    contrast_requirements: Dict[str, float]
    saturation_range: tuple[float, float]
    brightness_range: tuple[float, float]
    aspect_ratios: List[str]  # "16:9", "1:1", "4:3"
    prohibited_elements: List[str]


@dataclass
class BrandGuidelines:
    """Complete brand guidelines specification."""
    brand_name: str
    version: str
    colors: List[ColorGuideline]
    typography: List[TypographyGuideline]
    logo: Optional[LogoGuideline] = None
    style: Optional[StyleGuideline] = None
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ValidationResult:
    """Brand guideline validation result."""
    compliant: bool
    score: float  # 0.0 to 1.0
    violations: List[str]
    warnings: List[str]
    recommendations: List[str]
    guideline_matches: Dict[str, bool]
    metadata: Dict[str, Any] = field(default_factory=dict)


class BrandGuidelineManager:
    """Advanced brand guidelines management and validation."""
    
    def __init__(self, guidelines_dir: Optional[Path] = None):
        """Initialize the brand guideline manager.
        
        Args:
            guidelines_dir: Directory to store guideline files.
        """
        from app.config import settings
        self.guidelines_dir = guidelines_dir or (Path(settings.data_dir) / "brand_guidelines")
        self.guidelines_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for loaded guidelines
        self._guidelines_cache: Dict[str, BrandGuidelines] = {}
        self._project_guidelines: Dict[str, str] = {}  # project_id -> guideline_id
        
        logger.info(f"📋 Brand Guidelines Manager initialized at {self.guidelines_dir}")
    
    def create_guideline(
        self, 
        brand_name: str, 
        guideline_id: Optional[str] = None
    ) -> BrandGuidelines:
        """Create a new brand guideline template.
        
        Args:
            brand_name: Name of the brand.
            guideline_id: Optional custom ID.
            
        Returns:
            BrandGuidelines template.
        """
        if not guideline_id:
            guideline_id = self._generate_guideline_id(brand_name)
        
        # Create default color palette
        default_colors = [
            ColorGuideline.from_hex("Primary Blue", "#003366", "primary", "Main brand color"),
            ColorGuideline.from_hex("Secondary Gray", "#6B7280", "secondary", "Supporting color"),
            ColorGuideline.from_hex("Accent Green", "#10B981", "accent", "Highlight color"),
            ColorGuideline.from_hex("Neutral White", "#FFFFFF", "neutral", "Background color"),
            ColorGuideline.from_hex("Text Dark", "#1F2937", "neutral", "Primary text color"),
        ]
        
        # Create default typography
        default_typography = [
            TypographyGuideline("Arial", (24, 48), 1.2, 0, "heading", "bold"),
            TypographyGuideline("Arial", (14, 18), 1.5, 0, "body", "normal"),
            TypographyGuideline("Arial", (12, 14), 1.4, 0.5, "caption", "light"),
        ]
        
        # Create default style guidelines
        default_style = StyleGuideline(
            image_style="corporate",
            contrast_requirements={"text": 4.5, "background": 3.0},
            saturation_range=(0.1, 0.8),
            brightness_range=(0.2, 0.9),
            aspect_ratios=["16:9", "1:1", "4:3"],
            prohibited_elements=["watermarks", "text_overlays", "borders"]
        )
        
        guidelines = BrandGuidelines(
            brand_name=brand_name,
            version="1.0",
            colors=default_colors,
            typography=default_typography,
            style=default_style
        )
        
        # Save to cache and file
        self._guidelines_cache[guideline_id] = guidelines
        self._save_guidelines(guideline_id, guidelines)
        
        logger.info(f"📋 Created brand guidelines for {brand_name} (ID: {guideline_id})")
        return guidelines
    
    def load_guidelines(self, guideline_id: str) -> Optional[BrandGuidelines]:
        """Load brand guidelines from storage.
        
        Args:
            guideline_id: Guideline ID to load.
            
        Returns:
            BrandGuidelines if found, None otherwise.
        """
        # Check cache first
        if guideline_id in self._guidelines_cache:
            return self._guidelines_cache[guideline_id]
        
        # Load from file
        guideline_file = self.guidelines_dir / f"{guideline_id}.json"
        if guideline_file.exists():
            try:
                with open(guideline_file, 'r') as f:
                    data = json.load(f)
                
                guidelines = self._deserialize_guidelines(data)
                self._guidelines_cache[guideline_id] = guidelines
                
                logger.info(f"📋 Loaded guidelines: {guideline_id}")
                return guidelines
                
            except Exception as e:
                logger.error(f"Failed to load guidelines {guideline_id}: {e}")
        
        return None
    
    def update_guidelines(
        self, 
        guideline_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """Update existing brand guidelines.
        
        Args:
            guideline_id: Guidelines to update.
            updates: Dictionary of updates to apply.
            
        Returns:
            True if update successful.
        """
        guidelines = self.load_guidelines(guideline_id)
        if not guidelines:
            logger.error(f"Guidelines not found: {guideline_id}")
            return False
        
        try:
            # Apply updates
            for key, value in updates.items():
                if key == "colors" and isinstance(value, list):
                    # Handle color updates
                    new_colors = []
                    for color_data in value:
                        if isinstance(color_data, dict):
                            color = ColorGuideline(**color_data)
                            new_colors.append(color)
                    guidelines.colors = new_colors
                
                elif key == "typography" and isinstance(value, list):
                    # Handle typography updates
                    new_typography = []
                    for typo_data in value:
                        if isinstance(typo_data, dict):
                            typo = TypographyGuideline(**typo_data)
                            new_typography.append(typo)
                    guidelines.typography = new_typography
                
                elif key == "logo" and isinstance(value, dict):
                    guidelines.logo = LogoGuideline(**value)
                
                elif key == "style" and isinstance(value, dict):
                    guidelines.style = StyleGuideline(**value)
                
                elif hasattr(guidelines, key):
                    setattr(guidelines, key, value)
            
            # Update timestamp
            guidelines.updated_at = datetime.utcnow()
            
            # Save updates
            self._guidelines_cache[guideline_id] = guidelines
            self._save_guidelines(guideline_id, guidelines)
            
            logger.info(f"📋 Updated guidelines: {guideline_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update guidelines {guideline_id}: {e}")
            return False
    
    def assign_to_project(self, project_id: str, guideline_id: str) -> bool:
        """Assign brand guidelines to a project.
        
        Args:
            project_id: Project ID.
            guideline_id: Guidelines ID.
            
        Returns:
            True if assignment successful.
        """
        # Verify guidelines exist
        if not self.load_guidelines(guideline_id):
            logger.error(f"Cannot assign non-existent guidelines {guideline_id} to project {project_id}")
            return False
        
        self._project_guidelines[project_id] = guideline_id
        
        # Save project assignments
        assignments_file = self.guidelines_dir / "project_assignments.json"
        try:
            with open(assignments_file, 'w') as f:
                json.dump(self._project_guidelines, f, indent=2)
            
            logger.info(f"📋 Assigned guidelines {guideline_id} to project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save project assignment: {e}")
            return False
    
    async def validate_asset(
        self, 
        image_path: Path, 
        project_id: Optional[str] = None,
        guideline_id: Optional[str] = None
    ) -> ValidationResult:
        """Validate an asset against brand guidelines.
        
        Args:
            image_path: Path to image file.
            project_id: Optional project ID for context.
            guideline_id: Optional specific guideline ID.
            
        Returns:
            ValidationResult with compliance information.
        """
        try:
            # Determine which guidelines to use
            if guideline_id:
                guidelines = self.load_guidelines(guideline_id)
            elif project_id and project_id in self._project_guidelines:
                guidelines = self.load_guidelines(self._project_guidelines[project_id])
            else:
                # No guidelines available
                return ValidationResult(
                    compliant=True,
                    score=1.0,
                    violations=[],
                    warnings=["No brand guidelines configured"],
                    recommendations=["Configure brand guidelines for better compliance checking"],
                    guideline_matches={}
                )
            
            if not guidelines:
                return ValidationResult(
                    compliant=False,
                    score=0.0,
                    violations=["Brand guidelines not found"],
                    warnings=[],
                    recommendations=["Configure valid brand guidelines"],
                    guideline_matches={}
                )
            
            logger.info(f"🔍 Validating {image_path.name} against {guidelines.brand_name} guidelines")
            
            # Load and analyze image
            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Initialize validation result
            result = ValidationResult(
                compliant=True,
                score=1.0,
                violations=[],
                warnings=[],
                recommendations=[],
                guideline_matches={}
            )
            
            # 1. Color validation
            color_score = await self._validate_colors(image, guidelines.colors)
            result.guideline_matches['colors'] = color_score > 0.7
            if color_score < 0.7:
                result.violations.append("Image colors don't match brand palette")
                result.score *= 0.8
            
            # 2. Style validation
            if guidelines.style:
                style_score = await self._validate_style(image, guidelines.style)
                result.guideline_matches['style'] = style_score > 0.7
                if style_score < 0.7:
                    result.violations.append("Image style doesn't match brand guidelines")
                    result.score *= 0.9
            
            # 3. Logo validation (if logo is present)
            if guidelines.logo:
                logo_score = await self._validate_logo_usage(image, guidelines.logo)
                result.guideline_matches['logo'] = logo_score > 0.8
                if logo_score < 0.5:
                    result.violations.append("Logo usage violates brand guidelines")
                    result.score *= 0.7
            
            # 4. Technical specifications
            tech_score = await self._validate_technical_specs(image, guidelines)
            result.guideline_matches['technical'] = tech_score > 0.8
            if tech_score < 0.8:
                result.warnings.append("Image doesn't meet all technical specifications")
                result.score *= 0.95
            
            # Generate recommendations
            result.recommendations = self._generate_guideline_recommendations(result, guidelines)
            
            # Determine overall compliance
            result.compliant = result.score > 0.7 and len(result.violations) == 0
            
            # Add metadata
            result.metadata = {
                'guideline_id': guideline_id or self._project_guidelines.get(project_id),
                'guideline_name': guidelines.brand_name,
                'guideline_version': guidelines.version,
                'validation_timestamp': datetime.utcnow().isoformat(),
                'image_info': {
                    'size': image.size,
                    'mode': image.mode,
                    'format': image.format
                }
            }
            
            logger.info(f"✅ Guideline validation completed: score {result.score:.2f}, compliant: {result.compliant}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Guideline validation failed for {image_path}: {e}")
            return ValidationResult(
                compliant=False,
                score=0.0,
                violations=[f"Validation failed: {str(e)}"],
                warnings=[],
                recommendations=["Check image file integrity"],
                guideline_matches={}
            )
    
    async def _validate_colors(self, image: Image.Image, color_guidelines: List[ColorGuideline]) -> float:
        """Validate image colors against brand color palette.
        
        Args:
            image: PIL Image object.
            color_guidelines: Brand color specifications.
            
        Returns:
            Color compliance score (0.0 to 1.0).
        """
        if not color_guidelines:
            return 1.0
        
        try:
            # Extract dominant colors from image
            quantized = image.quantize(colors=8)
            palette = quantized.getpalette()
            
            image_colors = []
            if palette:
                for i in range(0, min(24, len(palette)), 3):
                    r, g, b = palette[i:i+3]
                    image_colors.append((r, g, b))
            
            # Get brand colors
            brand_colors = [color.rgb for color in color_guidelines]
            
            # Calculate color similarity
            total_distance = 0
            matches = 0
            
            for img_color in image_colors:
                min_distance = float('inf')
                for brand_color in brand_colors:
                    distance = sum((a - b) ** 2 for a, b in zip(img_color, brand_color)) ** 0.5
                    min_distance = min(min_distance, distance)
                
                # If color is close enough to brand palette, count as match
                if min_distance < 100:  # Threshold for color similarity
                    matches += 1
                
                total_distance += min_distance
            
            # Calculate score based on matches and overall distance
            if len(image_colors) == 0:
                return 0.5
            
            match_ratio = matches / len(image_colors)
            avg_distance = total_distance / len(image_colors)
            distance_score = max(0, 1 - (avg_distance / 442))  # Max RGB distance
            
            # Combine scores
            score = (match_ratio * 0.6) + (distance_score * 0.4)
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"Color validation failed: {e}")
            return 0.5
    
    async def _validate_style(self, image: Image.Image, style_guide: StyleGuideline) -> float:
        """Validate image style against brand style guidelines.
        
        Args:
            image: PIL Image object.
            style_guide: Style guidelines.
            
        Returns:
            Style compliance score (0.0 to 1.0).
        """
        score = 1.0
        
        try:
            # Check aspect ratio
            width, height = image.size
            aspect_ratio = width / height
            
            allowed_ratios = []
            for ratio_str in style_guide.aspect_ratios:
                try:
                    w, h = map(float, ratio_str.split(':'))
                    allowed_ratios.append(w / h)
                except:
                    continue
            
            # Find closest allowed ratio
            if allowed_ratios:
                closest_ratio = min(allowed_ratios, key=lambda r: abs(r - aspect_ratio))
                ratio_diff = abs(aspect_ratio - closest_ratio)
                
                if ratio_diff > 0.1:  # 10% tolerance
                    score *= 0.8
            
            # Check brightness
            from PIL import ImageStat
            stat = ImageStat.Stat(image)
            brightness = sum(stat.mean) / (3 * 255)
            
            min_brightness, max_brightness = style_guide.brightness_range
            if not (min_brightness <= brightness <= max_brightness):
                score *= 0.9
            
            # Check saturation (simplified)
            # This would need more sophisticated color space analysis
            if hasattr(style_guide, 'saturation_range'):
                min_sat, max_sat = style_guide.saturation_range
                # Simplified saturation check would go here
                pass
            
            return score
            
        except Exception as e:
            logger.error(f"Style validation failed: {e}")
            return 0.7
    
    async def _validate_logo_usage(self, image: Image.Image, logo_guide: LogoGuideline) -> float:
        """Validate logo usage in image.
        
        Args:
            image: PIL Image object.
            logo_guide: Logo guidelines.
            
        Returns:
            Logo compliance score (0.0 to 1.0).
        """
        # This is a simplified implementation
        # In practice, would use computer vision to detect and validate logo
        
        # Check image size meets minimum requirements
        width, height = image.size
        min_width, min_height = logo_guide.min_size_px
        
        if width < min_width or height < min_height:
            return 0.3
        
        # Additional logo validation would go here
        # (logo detection, clear space validation, etc.)
        
        return 0.8  # Default passing score
    
    async def _validate_technical_specs(self, image: Image.Image, guidelines: BrandGuidelines) -> float:
        """Validate technical specifications.
        
        Args:
            image: PIL Image object.
            guidelines: Brand guidelines.
            
        Returns:
            Technical compliance score (0.0 to 1.0).
        """
        score = 1.0
        
        # Check image format
        if guidelines.logo and guidelines.logo.file_formats:
            allowed_formats = [fmt.upper() for fmt in guidelines.logo.file_formats]
            if image.format and image.format.upper() not in allowed_formats:
                score *= 0.9
        
        # Check image quality (basic)
        width, height = image.size
        megapixels = (width * height) / 1000000
        
        if megapixels < 1:  # Too low resolution
            score *= 0.8
        elif megapixels > 50:  # Unnecessarily high resolution
            score *= 0.95
        
        return score
    
    def _generate_guideline_recommendations(
        self, 
        result: ValidationResult, 
        guidelines: BrandGuidelines
    ) -> List[str]:
        """Generate recommendations based on validation results.
        
        Args:
            result: Current validation result.
            guidelines: Brand guidelines used.
            
        Returns:
            List of recommendations.
        """
        recommendations = []
        
        if not result.guideline_matches.get('colors', True):
            primary_colors = [c.hex_code for c in guidelines.colors if c.usage == 'primary']
            recommendations.append(f"Use brand colors: {', '.join(primary_colors[:3])}")
        
        if not result.guideline_matches.get('style', True) and guidelines.style:
            recommendations.append(f"Follow {guidelines.style.image_style} style guidelines")
            
            if guidelines.style.aspect_ratios:
                recommendations.append(f"Use approved aspect ratios: {', '.join(guidelines.style.aspect_ratios)}")
        
        if guidelines.logo and not result.guideline_matches.get('logo', True):
            recommendations.append("Ensure logo meets size and clear space requirements")
        
        if result.score < 0.8:
            recommendations.append("Review complete brand guidelines for better compliance")
        
        return recommendations
    
    def _save_guidelines(self, guideline_id: str, guidelines: BrandGuidelines) -> None:
        """Save guidelines to file.
        
        Args:
            guideline_id: Guideline ID.
            guidelines: Guidelines to save.
        """
        try:
            guideline_file = self.guidelines_dir / f"{guideline_id}.json"
            data = self._serialize_guidelines(guidelines)
            
            with open(guideline_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved guidelines to {guideline_file}")
            
        except Exception as e:
            logger.error(f"Failed to save guidelines {guideline_id}: {e}")
    
    def _serialize_guidelines(self, guidelines: BrandGuidelines) -> Dict[str, Any]:
        """Serialize guidelines to JSON-compatible format.
        
        Args:
            guidelines: BrandGuidelines object.
            
        Returns:
            Serialized dictionary.
        """
        data = asdict(guidelines)
        
        # Convert datetime objects to ISO strings
        if isinstance(data.get('created_at'), datetime):
            data['created_at'] = data['created_at'].isoformat()
        if isinstance(data.get('updated_at'), datetime):
            data['updated_at'] = data['updated_at'].isoformat()
        
        return data
    
    def _deserialize_guidelines(self, data: Dict[str, Any]) -> BrandGuidelines:
        """Deserialize guidelines from JSON data.
        
        Args:
            data: JSON data dictionary.
            
        Returns:
            BrandGuidelines object.
        """
        # Convert string dates back to datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Reconstruct objects
        colors = [ColorGuideline(**color) for color in data.get('colors', [])]
        typography = [TypographyGuideline(**typo) for typo in data.get('typography', [])]
        
        logo = None
        if data.get('logo'):
            logo = LogoGuideline(**data['logo'])
        
        style = None
        if data.get('style'):
            style = StyleGuideline(**data['style'])
        
        return BrandGuidelines(
            brand_name=data['brand_name'],
            version=data['version'],
            colors=colors,
            typography=typography,
            logo=logo,
            style=style,
            custom_rules=data.get('custom_rules', {}),
            created_at=data.get('created_at', datetime.utcnow()),
            updated_at=data.get('updated_at', datetime.utcnow())
        )
    
    def _generate_guideline_id(self, brand_name: str) -> str:
        """Generate unique guideline ID.
        
        Args:
            brand_name: Brand name.
            
        Returns:
            Unique ID string.
        """
        # Create ID from brand name + timestamp
        clean_name = "".join(c.lower() for c in brand_name if c.isalnum())
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        hash_suffix = hashlib.md5(brand_name.encode()).hexdigest()[:6]
        
        return f"{clean_name}_{timestamp}_{hash_suffix}"
    
    def list_guidelines(self) -> List[Dict[str, Any]]:
        """List all available brand guidelines.
        
        Returns:
            List of guideline summaries.
        """
        guidelines_list = []
        
        for guideline_file in self.guidelines_dir.glob("*.json"):
            if guideline_file.name == "project_assignments.json":
                continue
            
            try:
                with open(guideline_file, 'r') as f:
                    data = json.load(f)
                
                guideline_id = guideline_file.stem
                guidelines_list.append({
                    'id': guideline_id,
                    'brand_name': data.get('brand_name', 'Unknown'),
                    'version': data.get('version', '1.0'),
                    'color_count': len(data.get('colors', [])),
                    'has_logo': bool(data.get('logo')),
                    'has_style': bool(data.get('style')),
                    'created_at': data.get('created_at'),
                    'updated_at': data.get('updated_at')
                })
                
            except Exception as e:
                logger.warning(f"Failed to read guideline file {guideline_file}: {e}")
        
        return sorted(guidelines_list, key=lambda x: x.get('updated_at', ''), reverse=True)
    
    def export_guidelines(self, guideline_id: str, format_type: str = "json") -> Optional[str]:
        """Export guidelines in specified format.
        
        Args:
            guideline_id: Guidelines to export.
            format_type: Export format (json, pdf, etc.).
            
        Returns:
            Path to exported file or None if failed.
        """
        guidelines = self.load_guidelines(guideline_id)
        if not guidelines:
            return None
        
        try:
            if format_type.lower() == "json":
                export_path = self.guidelines_dir / f"{guideline_id}_export.json"
                data = self._serialize_guidelines(guidelines)
                
                with open(export_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                return str(export_path)
            
            # Other formats could be implemented here (PDF, etc.)
            
        except Exception as e:
            logger.error(f"Failed to export guidelines {guideline_id}: {e}")
        
        return None


# Global manager instance
_guideline_manager: Optional[BrandGuidelineManager] = None


def get_brand_guideline_manager() -> BrandGuidelineManager:
    """Get global brand guideline manager instance.
    
    Returns:
        BrandGuidelineManager instance.
    """
    global _guideline_manager
    if _guideline_manager is None:
        _guideline_manager = BrandGuidelineManager()
    return _guideline_manager