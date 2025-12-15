"""Brand Guard System for protecting brand assets and enforcing guidelines."""

import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from PIL import Image, ImageDraw, ImageFont
import json

logger = logging.getLogger(__name__)


@dataclass
class BrandGuidelines:
    """Brand guidelines and restrictions."""
    
    # Logo requirements
    logo_path: Optional[str] = None
    logo_min_size: tuple[int, int] = (50, 50)
    logo_max_size: tuple[int, int] = (300, 300)
    logo_position: str = "bottom_right"  # bottom_right, bottom_left, top_right, top_left, center
    logo_opacity: float = 0.8
    
    # Color restrictions
    prohibited_colors: List[str] = field(default_factory=list)
    required_colors: List[str] = field(default_factory=list)
    color_tolerance: float = 0.1
    
    # Text restrictions
    prohibited_words: List[str] = field(default_factory=list)
    required_disclaimers: List[str] = field(default_factory=list)
    
    # Quality requirements
    min_resolution: tuple[int, int] = (512, 512)
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_formats: List[str] = field(default_factory=lambda: ["PNG", "JPEG", "WEBP"])
    
    # Compliance rules
    brand_name: str = "FIBO Omni-Director"
    copyright_text: str = "Generated with FIBO Omni-Director Pro"
    watermark_enabled: bool = True
    metadata_protection: bool = True


@dataclass
class BrandViolation:
    """Represents a brand guideline violation."""
    
    violation_type: str
    severity: str  # "low", "medium", "high", "critical"
    message: str
    suggested_fix: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BrandCheckResult:
    """Result of brand compliance check."""
    
    compliant: bool
    violations: List[BrandViolation]
    score: float  # 0.0 to 1.0 compliance score
    protected_asset_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BrandGuard:
    """Brand protection and compliance system."""
    
    def __init__(self, guidelines: Optional[BrandGuidelines] = None):
        """Initialize brand guard.
        
        Args:
            guidelines: Brand guidelines to enforce.
        """
        self.guidelines = guidelines or BrandGuidelines()
        self.violation_history: List[BrandViolation] = []
        
    def check_prompt_compliance(self, prompt: str) -> BrandCheckResult:
        """Check if prompt complies with brand guidelines.
        
        Args:
            prompt: Text prompt to check.
            
        Returns:
            BrandCheckResult with compliance status.
        """
        violations = []
        
        # Check for prohibited words
        prompt_lower = prompt.lower()
        for word in self.guidelines.prohibited_words:
            if word.lower() in prompt_lower:
                violations.append(BrandViolation(
                    violation_type="prohibited_content",
                    severity="high",
                    message=f"Prohibited word '{word}' found in prompt",
                    suggested_fix=f"Remove or replace '{word}' with brand-appropriate alternative"
                ))
        
        # Check for required disclaimers (in context)
        for disclaimer in self.guidelines.required_disclaimers:
            if disclaimer.lower() not in prompt_lower:
                violations.append(BrandViolation(
                    violation_type="missing_disclaimer",
                    severity="medium",
                    message=f"Required disclaimer missing: '{disclaimer}'",
                    suggested_fix=f"Add '{disclaimer}' to prompt or metadata"
                ))
        
        # Calculate compliance score
        score = max(0.0, 1.0 - (len(violations) * 0.2))
        
        return BrandCheckResult(
            compliant=len(violations) == 0,
            violations=violations,
            score=score,
            metadata={"prompt_length": len(prompt), "check_timestamp": datetime.utcnow().isoformat()}
        )
    
    def check_json_compliance(self, request_json: Dict[str, Any]) -> BrandCheckResult:
        """Check if JSON request complies with brand guidelines.
        
        Args:
            request_json: FIBO request JSON to check.
            
        Returns:
            BrandCheckResult with compliance status.
        """
        violations = []
        
        # Check color compliance
        if "color_palette" in request_json:
            colors = request_json["color_palette"].get("primary_colors", [])
            
            # Check prohibited colors
            for color in colors:
                if color.lower() in [c.lower() for c in self.guidelines.prohibited_colors]:
                    violations.append(BrandViolation(
                        violation_type="prohibited_color",
                        severity="medium",
                        message=f"Prohibited color '{color}' used",
                        suggested_fix=f"Replace with brand-approved alternative"
                    ))
            
            # Check required colors
            if self.guidelines.required_colors:
                has_required = any(
                    req_color.lower() in [c.lower() for c in colors]
                    for req_color in self.guidelines.required_colors
                )
                if not has_required:
                    violations.append(BrandViolation(
                        violation_type="missing_required_color",
                        severity="low",
                        message="No required brand colors found",
                        suggested_fix=f"Include one of: {', '.join(self.guidelines.required_colors)}"
                    ))
        
        # Check style compliance
        style = request_json.get("style", "")
        if "competitor" in style.lower() or "unauthorized" in style.lower():
            violations.append(BrandViolation(
                violation_type="brand_conflict",
                severity="critical",
                message="Style references competitor or unauthorized content",
                suggested_fix="Use brand-neutral or approved style references"
            ))
        
        score = max(0.0, 1.0 - (len(violations) * 0.15))
        
        return BrandCheckResult(
            compliant=len(violations) == 0,
            violations=violations,
            score=score,
            metadata={"json_keys": list(request_json.keys()), "check_timestamp": datetime.utcnow().isoformat()}
        )
    
    def protect_asset(self, image_path: str, output_path: Optional[str] = None) -> BrandCheckResult:
        """Apply brand protection to generated asset.
        
        Args:
            image_path: Path to image to protect.
            output_path: Optional output path for protected image.
            
        Returns:
            BrandCheckResult with protection status.
        """
        violations = []
        
        try:
            # Load image
            image = Image.open(image_path)
            
            # Check resolution compliance
            if image.size < self.guidelines.min_resolution:
                violations.append(BrandViolation(
                    violation_type="low_resolution",
                    severity="medium",
                    message=f"Image resolution {image.size} below minimum {self.guidelines.min_resolution}",
                    suggested_fix="Regenerate with higher resolution"
                ))
            
            # Check file size
            file_size = Path(image_path).stat().st_size
            if file_size > self.guidelines.max_file_size:
                violations.append(BrandViolation(
                    violation_type="file_too_large",
                    severity="low",
                    message=f"File size {file_size} exceeds maximum {self.guidelines.max_file_size}",
                    suggested_fix="Compress image or reduce quality"
                ))
            
            # Apply brand protection
            if self.guidelines.watermark_enabled:
                image = self._apply_watermark(image)
            
            if self.guidelines.logo_path and Path(self.guidelines.logo_path).exists():
                image = self._apply_logo(image)
            
            # Add metadata protection
            if self.guidelines.metadata_protection:
                image = self._add_metadata_protection(image)
            
            # Save protected image
            if output_path is None:
                output_path = image_path.replace(".", "_protected.")
            
            image.save(output_path, quality=95, optimize=True)
            
            score = max(0.0, 1.0 - (len(violations) * 0.1))
            
            return BrandCheckResult(
                compliant=len(violations) == 0,
                violations=violations,
                score=score,
                protected_asset_path=output_path,
                metadata={
                    "original_size": Path(image_path).stat().st_size,
                    "protected_size": Path(output_path).stat().st_size,
                    "resolution": image.size,
                    "protection_applied": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Brand protection failed: {e}")
            violations.append(BrandViolation(
                violation_type="protection_error",
                severity="critical",
                message=f"Failed to apply brand protection: {str(e)}",
                suggested_fix="Check image file and try again"
            ))
            
            return BrandCheckResult(
                compliant=False,
                violations=violations,
                score=0.0
            )
    
    def _apply_watermark(self, image: Image.Image) -> Image.Image:
        """Apply subtle watermark to image.
        
        Args:
            image: PIL Image to watermark.
            
        Returns:
            Watermarked image.
        """
        try:
            # Create transparent overlay
            overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Calculate text position
            text = self.guidelines.copyright_text
            try:
                font = ImageFont.truetype("Arial.ttf", 12)
            except:
                font = ImageFont.load_default()
            
            # Get text size
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Position in bottom right
            x = image.width - text_width - 10
            y = image.height - text_height - 10
            
            # Draw semi-transparent text
            draw.text((x, y), text, fill=(255, 255, 255, 128), font=font)
            
            # Composite with original
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            return Image.alpha_composite(image, overlay).convert('RGB')
            
        except Exception as e:
            logger.warning(f"Watermark application failed: {e}")
            return image
    
    def _apply_logo(self, image: Image.Image) -> Image.Image:
        """Apply brand logo to image.
        
        Args:
            image: PIL Image to add logo to.
            
        Returns:
            Image with logo applied.
        """
        try:
            logo = Image.open(self.guidelines.logo_path)
            
            # Resize logo if needed
            logo_size = logo.size
            if (logo_size[0] > self.guidelines.logo_max_size[0] or 
                logo_size[1] > self.guidelines.logo_max_size[1]):
                
                logo.thumbnail(self.guidelines.logo_max_size, Image.Resampling.LANCZOS)
            elif (logo_size[0] < self.guidelines.logo_min_size[0] or 
                  logo_size[1] < self.guidelines.logo_min_size[1]):
                
                scale = max(
                    self.guidelines.logo_min_size[0] / logo_size[0],
                    self.guidelines.logo_min_size[1] / logo_size[1]
                )
                new_size = (int(logo_size[0] * scale), int(logo_size[1] * scale))
                logo = logo.resize(new_size, Image.Resampling.LANCZOS)
            
            # Calculate position
            logo_w, logo_h = logo.size
            img_w, img_h = image.size
            
            if self.guidelines.logo_position == "bottom_right":
                x, y = img_w - logo_w - 20, img_h - logo_h - 20
            elif self.guidelines.logo_position == "bottom_left":
                x, y = 20, img_h - logo_h - 20
            elif self.guidelines.logo_position == "top_right":
                x, y = img_w - logo_w - 20, 20
            elif self.guidelines.logo_position == "top_left":
                x, y = 20, 20
            else:  # center
                x, y = (img_w - logo_w) // 2, (img_h - logo_h) // 2
            
            # Apply logo with opacity
            if logo.mode == 'RGBA':
                # Adjust opacity
                alpha = logo.split()[-1]
                alpha = alpha.point(lambda p: p * self.guidelines.logo_opacity)
                logo.putalpha(alpha)
                image.paste(logo, (x, y), logo)
            else:
                image.paste(logo, (x, y))
            
            return image
            
        except Exception as e:
            logger.warning(f"Logo application failed: {e}")
            return image
    
    def _add_metadata_protection(self, image: Image.Image) -> Image.Image:
        """Add metadata protection to image.
        
        Args:
            image: PIL Image to protect.
            
        Returns:
            Image with metadata protection.
        """
        try:
            # Add EXIF metadata if possible
            exif_dict = {
                "0th": {
                    271: self.guidelines.brand_name,  # Make
                    272: "FIBO Omni-Director Pro",     # Model
                    305: "FIBO Advanced Generation",   # Software
                    306: datetime.utcnow().strftime("%Y:%m:%d %H:%M:%S"),  # DateTime
                    315: self.guidelines.brand_name,   # Artist
                }
            }
            
            # Generate content hash for integrity
            content_hash = hashlib.md5(image.tobytes()).hexdigest()
            
            # Store protection metadata
            image.info['brand_protected'] = 'true'
            image.info['content_hash'] = content_hash
            image.info['protection_timestamp'] = datetime.utcnow().isoformat()
            
            return image
            
        except Exception as e:
            logger.warning(f"Metadata protection failed: {e}")
            return image
    
    def generate_compliance_report(self, results: List[BrandCheckResult]) -> Dict[str, Any]:
        """Generate compliance report from multiple check results.
        
        Args:
            results: List of brand check results.
            
        Returns:
            Comprehensive compliance report.
        """
        total_checks = len(results)
        compliant_checks = sum(1 for r in results if r.compliant)
        total_violations = sum(len(r.violations) for r in results)
        
        # Calculate average score
        avg_score = sum(r.score for r in results) / total_checks if total_checks > 0 else 0.0
        
        # Categorize violations
        violations_by_type = {}
        violations_by_severity = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        for result in results:
            for violation in result.violations:
                # By type
                if violation.violation_type not in violations_by_type:
                    violations_by_type[violation.violation_type] = 0
                violations_by_type[violation.violation_type] += 1
                
                # By severity
                violations_by_severity[violation.severity] += 1
        
        return {
            "summary": {
                "total_checks": total_checks,
                "compliant_checks": compliant_checks,
                "compliance_rate": compliant_checks / total_checks if total_checks > 0 else 0.0,
                "average_score": avg_score,
                "total_violations": total_violations
            },
            "violations": {
                "by_type": violations_by_type,
                "by_severity": violations_by_severity
            },
            "recommendations": self._generate_recommendations(violations_by_type, violations_by_severity),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _generate_recommendations(self, violations_by_type: Dict[str, int], 
                                violations_by_severity: Dict[str, int]) -> List[str]:
        """Generate actionable recommendations based on violations.
        
        Args:
            violations_by_type: Violation counts by type.
            violations_by_severity: Violation counts by severity.
            
        Returns:
            List of recommendations.
        """
        recommendations = []
        
        if violations_by_severity["critical"] > 0:
            recommendations.append("🚨 Critical violations detected - immediate review required")
        
        if violations_by_severity["high"] > violations_by_severity["low"]:
            recommendations.append("Focus on resolving high-severity brand compliance issues")
        
        if "prohibited_content" in violations_by_type:
            recommendations.append("Review content guidelines and implement prompt filtering")
        
        if "prohibited_color" in violations_by_type:
            recommendations.append("Update color palette to use only brand-approved colors")
        
        if "low_resolution" in violations_by_type:
            recommendations.append("Increase default generation resolution for brand quality")
        
        if not recommendations:
            recommendations.append("✅ Brand compliance is excellent - maintain current standards")
        
        return recommendations