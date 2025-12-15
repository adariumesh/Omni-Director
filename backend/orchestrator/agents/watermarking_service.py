"""
Advanced Image Watermarking Service for FIBO Omni-Director Pro.
Provides real watermarking capabilities with PIL and OpenCV.
"""

import logging
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union, List
from dataclasses import dataclass
from datetime import datetime
import math
import io

logger = logging.getLogger(__name__)


@dataclass
class WatermarkResult:
    """Result of watermarking operation."""
    success: bool
    processing_time_ms: float
    original_size: Tuple[int, int]
    output_path: Optional[Path] = None
    error: Optional[str] = None
    file_size_changed: bool = False
    new_file_size: Optional[int] = None
    watermark_info: Dict[str, Any] = None


class WatermarkingService:
    """Advanced watermarking service with multiple techniques."""
    
    def __init__(self):
        """Initialize the watermarking service."""
        self.default_font_size = 24
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
        logger.info("🎨 Watermarking Service initialized")
    
    async def apply_watermark(
        self, 
        input_path: Path, 
        output_path: Path, 
        config: Any,
        logo_path: Optional[Path] = None
    ) -> WatermarkResult:
        """Apply watermark to an image using advanced techniques.
        
        Args:
            input_path: Input image path.
            output_path: Output image path.
            config: Watermark configuration.
            logo_path: Optional custom logo path.
            
        Returns:
            WatermarkResult with operation details.
        """
        start_time = datetime.utcnow()
        
        try:
            if not input_path.exists():
                return WatermarkResult(
                    success=False,
                    processing_time_ms=0,
                    original_size=(0, 0),
                    error=f"Input file not found: {input_path}"
                )
            
            # Validate file format
            if input_path.suffix.lower() not in self.supported_formats:
                return WatermarkResult(
                    success=False,
                    processing_time_ms=0,
                    original_size=(0, 0),
                    error=f"Unsupported format: {input_path.suffix}"
                )
            
            # Load the image
            original_image = Image.open(input_path).convert('RGBA')
            original_size = original_image.size
            original_file_size = input_path.stat().st_size
            
            logger.info(f"🖼️ Processing image: {original_size[0]}x{original_size[1]}")
            
            # Apply watermark based on configuration
            if logo_path and logo_path.exists():
                watermarked_image = await self._apply_logo_watermark(
                    original_image, logo_path, config
                )
            else:
                watermarked_image = await self._apply_text_watermark(
                    original_image, config
                )
            
            # Apply additional effects if configured
            if hasattr(config, 'blend_mode') and config.blend_mode != 'normal':
                watermarked_image = self._apply_blend_mode(
                    original_image, watermarked_image, config.blend_mode
                )
            
            # Convert back to RGB if needed for JPEG
            output_format = self._get_output_format(output_path)
            if output_format in ('JPEG', 'JPG'):
                # Create white background for transparent areas
                final_image = Image.new('RGB', watermarked_image.size, (255, 255, 255))
                final_image.paste(watermarked_image, mask=watermarked_image.split()[-1])
                watermarked_image = final_image
            
            # Save the watermarked image
            save_kwargs = self._get_save_kwargs(output_format, config)
            watermarked_image.save(output_path, format=output_format, **save_kwargs)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds() * 1000
            
            # Check if file size changed
            new_file_size = output_path.stat().st_size
            file_size_changed = abs(new_file_size - original_file_size) > 1024  # 1KB threshold
            
            # Create watermark info
            watermark_info = {
                "position": getattr(config, 'position', 'bottom-right'),
                "opacity": getattr(config, 'opacity', 0.7),
                "size_percent": getattr(config, 'size_percent', 10.0),
                "blend_mode": getattr(config, 'blend_mode', 'normal'),
                "format": output_format,
                "original_size": original_size,
                "has_logo": logo_path is not None and logo_path.exists()
            }
            
            logger.info(f"✅ Watermark applied successfully in {processing_time:.1f}ms")
            
            return WatermarkResult(
                success=True,
                processing_time_ms=processing_time,
                original_size=original_size,
                output_path=output_path,
                file_size_changed=file_size_changed,
                new_file_size=new_file_size,
                watermark_info=watermark_info
            )
            
        except Exception as e:
            error_msg = f"Watermarking failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds() * 1000
            
            return WatermarkResult(
                success=False,
                processing_time_ms=processing_time,
                original_size=(0, 0),
                error=error_msg
            )
    
    async def _apply_logo_watermark(
        self, 
        image: Image.Image, 
        logo_path: Path, 
        config: Any
    ) -> Image.Image:
        """Apply logo watermark to image.
        
        Args:
            image: Source image.
            logo_path: Logo file path.
            config: Watermark configuration.
            
        Returns:
            Watermarked image.
        """
        try:
            # Load and process logo
            logo = Image.open(logo_path).convert('RGBA')
            
            # Calculate logo size based on image dimensions
            img_width, img_height = image.size
            size_percent = getattr(config, 'size_percent', 10.0) / 100.0
            
            # Maintain logo aspect ratio
            logo_ratio = logo.width / logo.height
            if logo.width > logo.height:
                logo_width = int(img_width * size_percent)
                logo_height = int(logo_width / logo_ratio)
            else:
                logo_height = int(img_height * size_percent)
                logo_width = int(logo_height * logo_ratio)
            
            # Resize logo
            logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
            
            # Apply opacity
            opacity = getattr(config, 'opacity', 0.7)
            if opacity < 1.0:
                # Create alpha mask for opacity
                alpha = logo.split()[-1]
                alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
                logo.putalpha(alpha)
            
            # Calculate position
            position = self._calculate_position(
                image.size, 
                logo.size, 
                getattr(config, 'position', 'bottom-right'),
                getattr(config, 'margin_percent', 5.0)
            )
            
            # Create a copy of the original image
            watermarked = image.copy()
            
            # Paste logo with alpha blending
            watermarked.paste(logo, position, logo)
            
            logger.debug(f"Logo watermark applied at position {position}")
            return watermarked
            
        except Exception as e:
            logger.error(f"Logo watermark failed: {e}")
            raise
    
    async def _apply_text_watermark(
        self, 
        image: Image.Image, 
        config: Any
    ) -> Image.Image:
        """Apply text watermark when no logo is available.
        
        Args:
            image: Source image.
            config: Watermark configuration.
            
        Returns:
            Watermarked image.
        """
        try:
            watermarked = image.copy()
            
            # Create drawing context
            draw = ImageDraw.Draw(watermarked)
            
            # Calculate font size based on image size
            img_width, img_height = image.size
            font_size = max(16, int(min(img_width, img_height) * 0.03))
            
            # Try to load a font
            font = self._get_font(font_size)
            
            # Default watermark text
            watermark_text = "FIBO PROTECTED"
            
            # Calculate text size and position
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            position = self._calculate_position(
                image.size,
                (text_width, text_height),
                getattr(config, 'position', 'bottom-right'),
                getattr(config, 'margin_percent', 5.0)
            )
            
            # Apply opacity
            opacity = getattr(config, 'opacity', 0.7)
            text_alpha = int(255 * opacity)
            
            # Draw text with shadow for better visibility
            shadow_offset = 2
            draw.text(
                (position[0] + shadow_offset, position[1] + shadow_offset),
                watermark_text,
                font=font,
                fill=(0, 0, 0, text_alpha // 2)  # Shadow
            )
            draw.text(
                position,
                watermark_text,
                font=font,
                fill=(255, 255, 255, text_alpha)  # Main text
            )
            
            logger.debug(f"Text watermark applied at position {position}")
            return watermarked
            
        except Exception as e:
            logger.error(f"Text watermark failed: {e}")
            raise
    
    def _apply_blend_mode(
        self, 
        original: Image.Image, 
        watermarked: Image.Image, 
        blend_mode: str
    ) -> Image.Image:
        """Apply advanced blend modes using OpenCV.
        
        Args:
            original: Original image.
            watermarked: Watermarked image.
            blend_mode: Blend mode to apply.
            
        Returns:
            Blended image.
        """
        try:
            if blend_mode == 'normal':
                return watermarked
            
            # Convert PIL to OpenCV format
            orig_cv = cv2.cvtColor(np.array(original), cv2.COLOR_RGBA2BGRA)
            water_cv = cv2.cvtColor(np.array(watermarked), cv2.COLOR_RGBA2BGRA)
            
            # Apply blend mode
            if blend_mode == 'multiply':
                blended = cv2.multiply(orig_cv.astype(np.float32) / 255.0, 
                                    water_cv.astype(np.float32) / 255.0)
                blended = (blended * 255).astype(np.uint8)
            
            elif blend_mode == 'overlay':
                # Overlay blend mode
                orig_norm = orig_cv.astype(np.float32) / 255.0
                water_norm = water_cv.astype(np.float32) / 255.0
                
                mask = orig_norm < 0.5
                blended = np.zeros_like(orig_norm)
                blended[mask] = 2 * orig_norm[mask] * water_norm[mask]
                blended[~mask] = 1 - 2 * (1 - orig_norm[~mask]) * (1 - water_norm[~mask])
                
                blended = (blended * 255).astype(np.uint8)
            
            else:
                logger.warning(f"Unknown blend mode: {blend_mode}, using normal")
                return watermarked
            
            # Convert back to PIL
            blended_pil = Image.fromarray(cv2.cvtColor(blended, cv2.COLOR_BGRA2RGBA))
            
            logger.debug(f"Applied blend mode: {blend_mode}")
            return blended_pil
            
        except Exception as e:
            logger.error(f"Blend mode {blend_mode} failed: {e}")
            return watermarked
    
    def _calculate_position(
        self, 
        image_size: Tuple[int, int], 
        watermark_size: Tuple[int, int], 
        position: str, 
        margin_percent: float
    ) -> Tuple[int, int]:
        """Calculate watermark position on image.
        
        Args:
            image_size: Image dimensions (width, height).
            watermark_size: Watermark dimensions (width, height).
            position: Position specification.
            margin_percent: Margin from edges as percentage.
            
        Returns:
            Position coordinates (x, y).
        """
        img_width, img_height = image_size
        mark_width, mark_height = watermark_size
        
        margin_x = int(img_width * margin_percent / 100.0)
        margin_y = int(img_height * margin_percent / 100.0)
        
        if position == 'top-left':
            return (margin_x, margin_y)
        elif position == 'top-right':
            return (img_width - mark_width - margin_x, margin_y)
        elif position == 'bottom-left':
            return (margin_x, img_height - mark_height - margin_y)
        elif position == 'bottom-right':
            return (img_width - mark_width - margin_x, img_height - mark_height - margin_y)
        elif position == 'center':
            return ((img_width - mark_width) // 2, (img_height - mark_height) // 2)
        elif position.startswith('custom:'):
            # Custom position in format "custom:x,y" or "custom:x%,y%"
            try:
                coords = position.split(':')[1]
                x_str, y_str = coords.split(',')
                
                if x_str.endswith('%'):
                    x = int(img_width * float(x_str[:-1]) / 100.0)
                else:
                    x = int(x_str)
                
                if y_str.endswith('%'):
                    y = int(img_height * float(y_str[:-1]) / 100.0)
                else:
                    y = int(y_str)
                
                return (max(0, min(x, img_width - mark_width)), 
                       max(0, min(y, img_height - mark_height)))
            except:
                logger.warning(f"Invalid custom position: {position}, using bottom-right")
                return (img_width - mark_width - margin_x, img_height - mark_height - margin_y)
        else:
            # Default to bottom-right
            return (img_width - mark_width - margin_x, img_height - mark_height - margin_y)
    
    def _get_font(self, size: int) -> ImageFont.ImageFont:
        """Get font for text watermark.
        
        Args:
            size: Font size.
            
        Returns:
            Font object.
        """
        try:
            # Try common system fonts
            font_names = [
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
                "C:/Windows/Fonts/arial.ttf",  # Windows
            ]
            
            for font_path in font_names:
                if Path(font_path).exists():
                    return ImageFont.truetype(font_path, size)
            
            # Fallback to default font
            return ImageFont.load_default()
            
        except Exception as e:
            logger.warning(f"Font loading failed: {e}, using default")
            return ImageFont.load_default()
    
    def _get_output_format(self, output_path: Path) -> str:
        """Get output format from file extension.
        
        Args:
            output_path: Output file path.
            
        Returns:
            Format string for PIL.
        """
        extension = output_path.suffix.lower()
        
        format_map = {
            '.jpg': 'JPEG',
            '.jpeg': 'JPEG',
            '.png': 'PNG',
            '.webp': 'WEBP',
            '.bmp': 'BMP',
            '.tiff': 'TIFF',
            '.tif': 'TIFF'
        }
        
        return format_map.get(extension, 'PNG')
    
    def _get_save_kwargs(self, format_type: str, config: Any) -> Dict[str, Any]:
        """Get save parameters for different formats.
        
        Args:
            format_type: Output format.
            config: Watermark configuration.
            
        Returns:
            Save parameters dictionary.
        """
        quality = getattr(config, 'quality', 90)
        
        if format_type == 'JPEG':
            return {
                'quality': quality,
                'optimize': True,
                'progressive': True
            }
        elif format_type == 'PNG':
            return {
                'optimize': True
            }
        elif format_type == 'WEBP':
            return {
                'quality': quality,
                'method': 6
            }
        else:
            return {}
    
    async def batch_watermark(
        self, 
        file_pairs: List[Tuple[Path, Path]], 
        config: Any,
        logo_path: Optional[Path] = None
    ) -> List[WatermarkResult]:
        """Apply watermarks to multiple images in batch.
        
        Args:
            file_pairs: List of (input_path, output_path) tuples.
            config: Watermark configuration.
            logo_path: Optional logo path.
            
        Returns:
            List of WatermarkResult objects.
        """
        logger.info(f"🔄 Starting batch watermarking for {len(file_pairs)} images")
        
        results = []
        successful = 0
        
        for input_path, output_path in file_pairs:
            try:
                result = await self.apply_watermark(input_path, output_path, config, logo_path)
                results.append(result)
                
                if result.success:
                    successful += 1
                
            except Exception as e:
                logger.error(f"Batch watermark failed for {input_path}: {e}")
                results.append(WatermarkResult(
                    success=False,
                    processing_time_ms=0,
                    original_size=(0, 0),
                    error=str(e)
                ))
        
        logger.info(f"✅ Batch watermarking completed: {successful}/{len(file_pairs)} successful")
        return results
    
    def validate_logo(self, logo_path: Path) -> Dict[str, Any]:
        """Validate logo file for watermarking.
        
        Args:
            logo_path: Logo file path.
            
        Returns:
            Validation result with recommendations.
        """
        try:
            if not logo_path.exists():
                return {
                    "valid": False,
                    "error": "Logo file not found"
                }
            
            # Check file format
            if logo_path.suffix.lower() not in self.supported_formats:
                return {
                    "valid": False,
                    "error": f"Unsupported format: {logo_path.suffix}"
                }
            
            # Load and analyze logo
            logo = Image.open(logo_path)
            
            recommendations = []
            
            # Check dimensions
            if logo.width < 100 or logo.height < 100:
                recommendations.append("Logo is quite small - consider using a higher resolution")
            
            if logo.width > 2000 or logo.height > 2000:
                recommendations.append("Logo is very large - consider resizing for better performance")
            
            # Check format recommendations
            if logo_path.suffix.lower() in ['.jpg', '.jpeg'] and logo.mode in ['RGBA', 'LA']:
                recommendations.append("JPEG doesn't support transparency - consider PNG for better results")
            
            # Check aspect ratio
            aspect_ratio = logo.width / logo.height
            if aspect_ratio > 3 or aspect_ratio < 0.33:
                recommendations.append("Extreme aspect ratio may cause positioning issues")
            
            return {
                "valid": True,
                "width": logo.width,
                "height": logo.height,
                "format": logo.format,
                "mode": logo.mode,
                "has_transparency": logo.mode in ['RGBA', 'LA'] or 'transparency' in logo.info,
                "file_size_kb": round(logo_path.stat().st_size / 1024, 1),
                "aspect_ratio": round(aspect_ratio, 2),
                "recommendations": recommendations
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Logo validation failed: {str(e)}"
            }