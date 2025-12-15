"""
Brand Compliance Checker for FIBO Omni-Director Pro.
Implements content filtering, brand validation, and compliance scoring.
"""

import logging
import cv2
import numpy as np
from PIL import Image, ImageStat, ImageDraw
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import colorsys
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class ColorProfile:
    """Color profile analysis."""
    dominant_colors: List[Tuple[int, int, int]]
    color_distribution: Dict[str, float]
    brightness: float
    contrast: float
    saturation: float
    temperature: str  # warm, cool, neutral


@dataclass
class ContentAnalysis:
    """Content analysis results."""
    text_detected: bool
    text_confidence: float
    inappropriate_content: bool
    safety_score: float
    quality_score: float
    resolution_analysis: Dict[str, Any]


@dataclass
class ComplianceResult:
    """Brand compliance check result."""
    score: float  # 0.0 to 1.0
    violations: List[str]
    warnings: List[str]
    recommendations: List[str]
    color_profile: Optional[ColorProfile] = None
    content_analysis: Optional[ContentAnalysis] = None
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComplianceChecker:
    """Advanced compliance checker with real analysis capabilities."""
    
    def __init__(self):
        """Initialize the compliance checker."""
        # Default brand color palette (can be customized per project)
        self.default_brand_colors = [
            (0, 51, 102),    # Deep Blue
            (255, 255, 255), # White
            (220, 220, 220), # Light Gray
            (51, 51, 51),    # Dark Gray
        ]
        
        # Quality thresholds
        self.min_resolution = (800, 600)
        self.min_quality_score = 0.7
        self.max_brightness = 0.9
        self.min_contrast = 0.3
        
        # Content filtering keywords (expandable)
        self.prohibited_content_patterns = [
            'inappropriate', 'offensive', 'violent', 'explicit'
        ]
        
        logger.info("🔍 Compliance Checker initialized")
    
    async def check_compliance(
        self, 
        image_path: Path, 
        project_id: Optional[str] = None,
        custom_rules: Optional[Dict[str, Any]] = None
    ) -> ComplianceResult:
        """Perform comprehensive compliance check on an image.
        
        Args:
            image_path: Path to image file.
            project_id: Optional project ID for context-specific rules.
            custom_rules: Optional custom compliance rules.
            
        Returns:
            ComplianceResult with analysis.
        """
        start_time = datetime.utcnow()
        
        try:
            if not image_path.exists():
                return ComplianceResult(
                    score=0.0,
                    violations=['Image file not found'],
                    warnings=[],
                    recommendations=['Ensure image file exists and is accessible']
                )
            
            logger.info(f"🔍 Starting compliance check for {image_path.name}")
            
            # Load image
            image = Image.open(image_path)
            original_format = image.format
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                rgb_image = image.convert('RGB')
            else:
                rgb_image = image
            
            # Initialize result
            result = ComplianceResult(
                score=1.0,  # Start with perfect score
                violations=[],
                warnings=[],
                recommendations=[]
            )
            
            # 1. Resolution and Quality Analysis
            resolution_analysis = self._analyze_resolution(rgb_image)
            result.metadata['resolution'] = resolution_analysis
            
            if resolution_analysis['width'] < self.min_resolution[0] or resolution_analysis['height'] < self.min_resolution[1]:
                result.violations.append(f"Resolution too low: {resolution_analysis['width']}x{resolution_analysis['height']}")
                result.score -= 0.2
            
            # 2. Color Profile Analysis
            color_profile = await self._analyze_color_profile(rgb_image)
            result.color_profile = color_profile
            
            # Check color compliance
            color_score = self._check_color_compliance(color_profile, custom_rules)
            result.score = min(result.score, color_score)
            
            # 3. Content Analysis
            content_analysis = await self._analyze_content(rgb_image, image_path)
            result.content_analysis = content_analysis
            
            # Apply content analysis to score
            if content_analysis.inappropriate_content:
                result.violations.append("Inappropriate content detected")
                result.score -= 0.5
            
            if content_analysis.safety_score < 0.8:
                result.warnings.append(f"Low safety score: {content_analysis.safety_score:.2f}")
                result.score -= 0.1
            
            if content_analysis.quality_score < self.min_quality_score:
                result.warnings.append(f"Low quality score: {content_analysis.quality_score:.2f}")
                result.score -= 0.1
            
            # 4. Technical Compliance Checks
            technical_score = self._check_technical_compliance(rgb_image, original_format)
            result.score = min(result.score, technical_score)
            
            # 5. Brand Guidelines Compliance (if available)
            if project_id:
                brand_score = await self._check_brand_guidelines(rgb_image, project_id)
                result.score = min(result.score, brand_score)
            
            # 6. Generate recommendations
            result.recommendations.extend(self._generate_recommendations(result))
            
            # Ensure score is within bounds
            result.score = max(0.0, min(1.0, result.score))
            
            # Calculate processing time
            end_time = datetime.utcnow()
            result.processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Add metadata
            result.metadata.update({
                'file_size_kb': round(image_path.stat().st_size / 1024, 1),
                'format': original_format,
                'mode': image.mode,
                'processing_timestamp': end_time.isoformat(),
                'checker_version': '1.0'
            })
            
            logger.info(f"✅ Compliance check completed: score {result.score:.2f}, {len(result.violations)} violations")
            return result
            
        except Exception as e:
            logger.error(f"❌ Compliance check failed for {image_path}: {e}")
            return ComplianceResult(
                score=0.0,
                violations=[f"Compliance check failed: {str(e)}"],
                warnings=[],
                recommendations=['Review image file integrity and format']
            )
    
    def _analyze_resolution(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze image resolution and dimensions.
        
        Args:
            image: PIL Image object.
            
        Returns:
            Resolution analysis dict.
        """
        width, height = image.size
        megapixels = (width * height) / 1000000
        aspect_ratio = width / height
        
        # Determine quality tier
        if megapixels >= 12:
            quality_tier = "high"
        elif megapixels >= 5:
            quality_tier = "medium"
        elif megapixels >= 2:
            quality_tier = "low"
        else:
            quality_tier = "very_low"
        
        return {
            'width': width,
            'height': height,
            'megapixels': round(megapixels, 2),
            'aspect_ratio': round(aspect_ratio, 2),
            'quality_tier': quality_tier,
            'is_portrait': height > width,
            'is_landscape': width > height,
            'is_square': abs(aspect_ratio - 1.0) < 0.1
        }
    
    async def _analyze_color_profile(self, image: Image.Image) -> ColorProfile:
        """Analyze image color profile and characteristics.
        
        Args:
            image: PIL Image object.
            
        Returns:
            ColorProfile with analysis.
        """
        try:
            # Get dominant colors using quantization
            quantized = image.quantize(colors=8, method=2)
            palette = quantized.getpalette()
            
            # Extract dominant colors
            dominant_colors = []
            if palette:
                for i in range(0, min(24, len(palette)), 3):  # Up to 8 colors
                    r, g, b = palette[i:i+3]
                    dominant_colors.append((r, g, b))
            
            # Calculate color statistics
            stat = ImageStat.Stat(image)
            
            # Calculate brightness (0-1)
            brightness = sum(stat.mean) / (3 * 255)
            
            # Calculate contrast (simplified)
            contrast = sum(stat.stddev) / (3 * 255)
            
            # Calculate saturation
            hsv_values = []
            for color in dominant_colors[:5]:  # Use top 5 colors
                r, g, b = [x/255.0 for x in color]
                h, s, v = colorsys.rgb_to_hsv(r, g, b)
                hsv_values.append((h, s, v))
            
            avg_saturation = sum(hsv[1] for hsv in hsv_values) / len(hsv_values) if hsv_values else 0
            
            # Determine temperature
            warm_colors = sum(1 for color in dominant_colors if self._is_warm_color(color))
            cool_colors = sum(1 for color in dominant_colors if self._is_cool_color(color))
            
            if warm_colors > cool_colors:
                temperature = "warm"
            elif cool_colors > warm_colors:
                temperature = "cool"
            else:
                temperature = "neutral"
            
            # Color distribution
            color_distribution = self._analyze_color_distribution(image)
            
            return ColorProfile(
                dominant_colors=dominant_colors,
                color_distribution=color_distribution,
                brightness=brightness,
                contrast=contrast,
                saturation=avg_saturation,
                temperature=temperature
            )
            
        except Exception as e:
            logger.error(f"Color profile analysis failed: {e}")
            return ColorProfile(
                dominant_colors=[],
                color_distribution={},
                brightness=0.5,
                contrast=0.5,
                saturation=0.5,
                temperature="neutral"
            )
    
    async def _analyze_content(self, image: Image.Image, image_path: Path) -> ContentAnalysis:
        """Analyze image content for safety and quality.
        
        Args:
            image: PIL Image object.
            image_path: Path to image file.
            
        Returns:
            ContentAnalysis with results.
        """
        try:
            # Convert to numpy for OpenCV processing
            img_array = np.array(image)
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Text detection using basic edge detection
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            text_density = np.count_nonzero(edges) / edges.size
            text_detected = text_density > 0.1  # Threshold for text presence
            text_confidence = min(1.0, text_density * 10)
            
            # Basic content safety check (simplified)
            # In production, this would integrate with content moderation APIs
            inappropriate_content = False
            safety_score = 1.0
            
            # Check filename for inappropriate content
            filename_lower = image_path.name.lower()
            for pattern in self.prohibited_content_patterns:
                if pattern in filename_lower:
                    inappropriate_content = True
                    safety_score = 0.0
                    break
            
            # Image quality analysis
            quality_score = self._calculate_quality_score(img_cv)
            
            # Resolution analysis
            resolution_analysis = {
                'sharpness': self._calculate_sharpness(gray),
                'noise_level': self._calculate_noise_level(gray),
                'compression_artifacts': self._detect_compression_artifacts(img_cv)
            }
            
            return ContentAnalysis(
                text_detected=text_detected,
                text_confidence=text_confidence,
                inappropriate_content=inappropriate_content,
                safety_score=safety_score,
                quality_score=quality_score,
                resolution_analysis=resolution_analysis
            )
            
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return ContentAnalysis(
                text_detected=False,
                text_confidence=0.0,
                inappropriate_content=False,
                safety_score=0.8,  # Default safe score
                quality_score=0.7,  # Default quality
                resolution_analysis={}
            )
    
    def _check_color_compliance(
        self, 
        color_profile: ColorProfile, 
        custom_rules: Optional[Dict[str, Any]]
    ) -> float:
        """Check color compliance against brand guidelines.
        
        Args:
            color_profile: Analyzed color profile.
            custom_rules: Optional custom color rules.
            
        Returns:
            Compliance score (0.0 to 1.0).
        """
        score = 1.0
        
        # Check brightness
        if color_profile.brightness < 0.1 or color_profile.brightness > 0.9:
            score -= 0.1
        
        # Check contrast
        if color_profile.contrast < 0.2:
            score -= 0.1
        
        # Check if dominant colors align with brand palette
        brand_colors = custom_rules.get('brand_colors', self.default_brand_colors) if custom_rules else self.default_brand_colors
        
        if brand_colors:
            color_alignment = self._calculate_color_alignment(color_profile.dominant_colors, brand_colors)
            if color_alignment < 0.5:
                score -= 0.2
        
        return max(0.0, score)
    
    def _check_technical_compliance(self, image: Image.Image, format_type: str) -> float:
        """Check technical compliance requirements.
        
        Args:
            image: PIL Image object.
            format_type: Image format.
            
        Returns:
            Compliance score (0.0 to 1.0).
        """
        score = 1.0
        
        # Check supported formats
        supported_formats = ['JPEG', 'PNG', 'WEBP']
        if format_type not in supported_formats:
            score -= 0.2
        
        # Check for transparency in inappropriate formats
        if format_type == 'JPEG' and image.mode in ['RGBA', 'LA']:
            score -= 0.1
        
        # Check image mode
        if image.mode not in ['RGB', 'RGBA', 'L']:
            score -= 0.1
        
        return max(0.0, score)
    
    async def _check_brand_guidelines(self, image: Image.Image, project_id: str) -> float:
        """Check compliance with project-specific brand guidelines.
        
        Args:
            image: PIL Image object.
            project_id: Project ID.
            
        Returns:
            Compliance score (0.0 to 1.0).
        """
        # This would typically load project-specific guidelines from database
        # For now, return a default score
        return 0.9
    
    def _generate_recommendations(self, result: ComplianceResult) -> List[str]:
        """Generate actionable recommendations based on compliance results.
        
        Args:
            result: ComplianceResult to analyze.
            
        Returns:
            List of recommendations.
        """
        recommendations = []
        
        if result.score < 0.5:
            recommendations.append("Image requires significant improvement for brand compliance")
        
        if result.color_profile:
            if result.color_profile.contrast < 0.3:
                recommendations.append("Increase image contrast for better visibility")
            
            if result.color_profile.brightness > 0.85:
                recommendations.append("Image may be too bright - consider adjusting exposure")
            
            if result.color_profile.brightness < 0.15:
                recommendations.append("Image may be too dark - consider brightening")
        
        if result.content_analysis:
            if result.content_analysis.quality_score < 0.7:
                recommendations.append("Consider using higher quality source image")
            
            if result.content_analysis.text_detected and result.content_analysis.text_confidence > 0.8:
                recommendations.append("Text detected - ensure it meets brand typography guidelines")
        
        if 'resolution' in result.metadata:
            res = result.metadata['resolution']
            if res['quality_tier'] == 'low':
                recommendations.append("Consider using higher resolution image for better quality")
        
        return recommendations
    
    def _is_warm_color(self, color: Tuple[int, int, int]) -> bool:
        """Check if color is warm (red, orange, yellow tones).
        
        Args:
            color: RGB color tuple.
            
        Returns:
            True if warm color.
        """
        r, g, b = color
        # Simple heuristic for warm colors
        return r > g and r > b
    
    def _is_cool_color(self, color: Tuple[int, int, int]) -> bool:
        """Check if color is cool (blue, green, purple tones).
        
        Args:
            color: RGB color tuple.
            
        Returns:
            True if cool color.
        """
        r, g, b = color
        # Simple heuristic for cool colors
        return b > r or g > r
    
    def _analyze_color_distribution(self, image: Image.Image) -> Dict[str, float]:
        """Analyze distribution of color types in image.
        
        Args:
            image: PIL Image object.
            
        Returns:
            Color distribution percentages.
        """
        try:
            # Sample colors from image
            width, height = image.size
            sample_size = min(1000, width * height // 100)
            
            colors = []
            step_x = max(1, width // int(np.sqrt(sample_size)))
            step_y = max(1, height // int(np.sqrt(sample_size)))
            
            for x in range(0, width, step_x):
                for y in range(0, height, step_y):
                    if len(colors) >= sample_size:
                        break
                    colors.append(image.getpixel((x, y)))
                if len(colors) >= sample_size:
                    break
            
            # Categorize colors
            warm = cool = neutral = grayscale = 0
            
            for color in colors:
                if len(color) == 3:  # RGB
                    r, g, b = color
                else:  # Handle other formats
                    continue
                
                # Check if grayscale
                if abs(r - g) < 10 and abs(g - b) < 10 and abs(r - b) < 10:
                    grayscale += 1
                elif self._is_warm_color((r, g, b)):
                    warm += 1
                elif self._is_cool_color((r, g, b)):
                    cool += 1
                else:
                    neutral += 1
            
            total = len(colors)
            if total == 0:
                return {}
            
            return {
                'warm_percent': round(warm / total * 100, 1),
                'cool_percent': round(cool / total * 100, 1),
                'neutral_percent': round(neutral / total * 100, 1),
                'grayscale_percent': round(grayscale / total * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"Color distribution analysis failed: {e}")
            return {}
    
    def _calculate_color_alignment(
        self, 
        image_colors: List[Tuple[int, int, int]], 
        brand_colors: List[Tuple[int, int, int]]
    ) -> float:
        """Calculate how well image colors align with brand colors.
        
        Args:
            image_colors: Colors from image.
            brand_colors: Brand palette colors.
            
        Returns:
            Alignment score (0.0 to 1.0).
        """
        if not image_colors or not brand_colors:
            return 0.5
        
        total_distance = 0
        comparisons = 0
        
        for img_color in image_colors[:5]:  # Top 5 colors
            min_distance = float('inf')
            for brand_color in brand_colors:
                # Calculate Euclidean distance in RGB space
                distance = np.sqrt(sum((a - b) ** 2 for a, b in zip(img_color, brand_color)))
                min_distance = min(min_distance, distance)
            
            total_distance += min_distance
            comparisons += 1
        
        if comparisons == 0:
            return 0.5
        
        # Normalize distance (max possible distance in RGB is ~441)
        avg_distance = total_distance / comparisons
        alignment = max(0, 1 - (avg_distance / 441))
        
        return alignment
    
    def _calculate_quality_score(self, img_cv: np.ndarray) -> float:
        """Calculate overall image quality score.
        
        Args:
            img_cv: OpenCV image array.
            
        Returns:
            Quality score (0.0 to 1.0).
        """
        try:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Sharpness
            sharpness = self._calculate_sharpness(gray)
            
            # Noise level
            noise = self._calculate_noise_level(gray)
            
            # Combine metrics
            quality = (sharpness * 0.6) + ((1 - noise) * 0.4)
            
            return max(0.0, min(1.0, quality))
            
        except Exception as e:
            logger.error(f"Quality score calculation failed: {e}")
            return 0.7
    
    def _calculate_sharpness(self, gray: np.ndarray) -> float:
        """Calculate image sharpness using Laplacian variance.
        
        Args:
            gray: Grayscale image array.
            
        Returns:
            Sharpness score (0.0 to 1.0).
        """
        try:
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            variance = laplacian.var()
            
            # Normalize (empirical threshold)
            sharpness = min(1.0, variance / 1000)
            
            return sharpness
            
        except Exception as e:
            logger.error(f"Sharpness calculation failed: {e}")
            return 0.5
    
    def _calculate_noise_level(self, gray: np.ndarray) -> float:
        """Calculate image noise level.
        
        Args:
            gray: Grayscale image array.
            
        Returns:
            Noise level (0.0 to 1.0).
        """
        try:
            # Use standard deviation of differences as noise metric
            h, w = gray.shape
            
            # Calculate differences in x and y directions
            diff_x = np.diff(gray.astype(np.float32), axis=1)
            diff_y = np.diff(gray.astype(np.float32), axis=0)
            
            # Standard deviation of differences
            noise_x = np.std(diff_x)
            noise_y = np.std(diff_y)
            
            noise = (noise_x + noise_y) / 2
            
            # Normalize (empirical threshold)
            noise_level = min(1.0, noise / 50)
            
            return noise_level
            
        except Exception as e:
            logger.error(f"Noise calculation failed: {e}")
            return 0.3
    
    def _detect_compression_artifacts(self, img_cv: np.ndarray) -> bool:
        """Detect compression artifacts in image.
        
        Args:
            img_cv: OpenCV image array.
            
        Returns:
            True if artifacts detected.
        """
        try:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Use DCT to detect block artifacts (simplified)
            # This is a basic check - more sophisticated methods exist
            h, w = gray.shape
            
            if h < 16 or w < 16:
                return False
            
            # Sample 8x8 blocks and check for regularity
            block_variance = []
            for y in range(0, h - 8, 8):
                for x in range(0, w - 8, 8):
                    block = gray[y:y+8, x:x+8]
                    block_variance.append(np.var(block))
            
            # High variance in variance suggests artifacts
            variance_of_variance = np.var(block_variance)
            
            return variance_of_variance > 1000  # Empirical threshold
            
        except Exception as e:
            logger.error(f"Compression artifact detection failed: {e}")
            return False
    
    def set_brand_colors(self, colors: List[Tuple[int, int, int]]) -> None:
        """Set brand color palette for compliance checking.
        
        Args:
            colors: List of RGB color tuples.
        """
        self.default_brand_colors = colors
        logger.info(f"🎨 Updated brand color palette: {len(colors)} colors")
    
    def get_compliance_summary(self, results: List[ComplianceResult]) -> Dict[str, Any]:
        """Generate summary statistics from multiple compliance results.
        
        Args:
            results: List of ComplianceResult objects.
            
        Returns:
            Summary statistics dictionary.
        """
        if not results:
            return {}
        
        total_results = len(results)
        avg_score = sum(r.score for r in results) / total_results
        
        all_violations = []
        all_warnings = []
        for result in results:
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)
        
        # Count unique violations
        unique_violations = {}
        for violation in all_violations:
            unique_violations[violation] = unique_violations.get(violation, 0) + 1
        
        return {
            'total_checks': total_results,
            'average_score': round(avg_score, 3),
            'passing_score_threshold': 0.7,
            'passing_count': len([r for r in results if r.score >= 0.7]),
            'failing_count': len([r for r in results if r.score < 0.7]),
            'total_violations': len(all_violations),
            'total_warnings': len(all_warnings),
            'common_violations': sorted(unique_violations.items(), key=lambda x: x[1], reverse=True)[:5],
            'score_distribution': {
                'excellent': len([r for r in results if r.score >= 0.9]),
                'good': len([r for r in results if 0.7 <= r.score < 0.9]),
                'fair': len([r for r in results if 0.5 <= r.score < 0.7]),
                'poor': len([r for r in results if r.score < 0.5])
            }
        }