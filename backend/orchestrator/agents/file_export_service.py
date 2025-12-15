"""
FIBO File Export Service - Real file export functionality.

This service handles the actual conversion and export of stored files to various formats
with support for quality settings, watermarking, and batch operations.

Author: FIBO Omni-Director Pro
Version: 2.0.0
"""

import logging
import asyncio
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import io

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats."""
    PNG = "png"
    JPEG = "jpg"
    WEBP = "webp"
    TIFF = "tiff"
    BMP = "bmp"


class WatermarkPosition(Enum):
    """Watermark positioning options."""
    BOTTOM_RIGHT = "bottom_right"
    BOTTOM_LEFT = "bottom_left"
    TOP_RIGHT = "top_right"
    TOP_LEFT = "top_left"
    CENTER = "center"
    BOTTOM_CENTER = "bottom_center"


@dataclass
class WatermarkConfig:
    """Configuration for watermarking."""
    
    text: str = "FIBO Omni-Director Pro"
    position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT
    opacity: float = 0.3  # 0.0 to 1.0
    font_size: int = 16
    font_color: tuple = (255, 255, 255)  # RGB
    background_color: Optional[tuple] = (0, 0, 0, 128)  # RGBA, None for no background
    margin: int = 20
    rotation: int = 0  # Rotation in degrees
    enable_shadow: bool = True
    shadow_offset: tuple = (2, 2)
    shadow_color: tuple = (0, 0, 0, 100)


@dataclass
class ResizeConfig:
    """Configuration for resizing operations."""
    
    width: Optional[int] = None
    height: Optional[int] = None
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    maintain_aspect: bool = True
    upscale: bool = False
    resampling: str = "LANCZOS"  # LANCZOS, BILINEAR, BICUBIC, NEAREST


@dataclass
class ExportRequest:
    """Request for file export operation."""
    
    source_path: Path
    output_format: ExportFormat
    output_filename: Optional[str] = None
    quality: int = 95  # 1-100 for JPEG/WEBP
    optimize: bool = True
    progressive: bool = True  # For JPEG
    
    # Resizing
    resize_config: Optional[ResizeConfig] = None
    
    # Watermarking
    apply_watermark: bool = False
    watermark_config: Optional[WatermarkConfig] = None
    
    # Processing options
    enhance_colors: bool = False
    sharpen: bool = False
    auto_contrast: bool = False
    
    # Metadata
    preserve_exif: bool = True
    custom_metadata: Optional[Dict[str, Any]] = None
    
    # Custom filename (overrides output_filename if provided)
    custom_filename: Optional[str] = None


@dataclass
class ExportResult:
    """Result of export operation."""
    
    success: bool
    output_path: Optional[Path] = None
    original_size: tuple = field(default_factory=tuple)  # (width, height)
    output_size: tuple = field(default_factory=tuple)    # (width, height)
    file_size_original: int = 0
    file_size_output: int = 0
    compression_ratio: float = 0.0
    processing_time: float = 0.0
    
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FileExportService:
    """
    Service for exporting files with various formats and processing options.
    
    Supports:
    - Multiple output formats (PNG, JPEG, WEBP, TIFF, BMP)
    - Quality and compression settings
    - Watermarking with customizable options
    - Image resizing and scaling
    - Color enhancement and processing
    - Metadata preservation and custom metadata
    - Batch processing capabilities
    """
    
    def __init__(self):
        """Initialize the file export service."""
        self.supported_formats = {
            ExportFormat.PNG: self._export_png,
            ExportFormat.JPEG: self._export_jpeg,
            ExportFormat.WEBP: self._export_webp,
            ExportFormat.TIFF: self._export_tiff,
            ExportFormat.BMP: self._export_bmp
        }
        
        # Default watermark configuration
        self.default_watermark = WatermarkConfig()
        
        logger.info("File Export Service initialized")
    
    async def export_file(
        self, 
        request: ExportRequest,
        output_dir: Optional[Path] = None
    ) -> ExportResult:
        """
        Export a file according to the specified request.
        
        Args:
            request: Export request with all parameters.
            output_dir: Optional output directory (uses source dir if not specified).
            
        Returns:
            ExportResult with operation details.
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate source file
            if not request.source_path.exists():
                return ExportResult(
                    success=False,
                    errors=[f"Source file not found: {request.source_path}"]
                )
            
            if not request.source_path.is_file():
                return ExportResult(
                    success=False,
                    errors=[f"Source path is not a file: {request.source_path}"]
                )
            
            # Determine output path
            output_dir = output_dir or request.source_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate output filename
            if request.custom_filename:
                output_filename = request.custom_filename
            elif request.output_filename:
                output_filename = request.output_filename
            else:
                base_name = request.source_path.stem
                output_filename = f"{base_name}_exported.{request.output_format.value}"
            
            # Ensure proper extension
            if not output_filename.lower().endswith(f".{request.output_format.value}"):
                output_filename = f"{output_filename}.{request.output_format.value}"
            
            output_path = output_dir / output_filename
            
            # Load and validate image
            try:
                image = Image.open(request.source_path)
                original_size = image.size
                file_size_original = request.source_path.stat().st_size
                
            except Exception as e:
                return ExportResult(
                    success=False,
                    errors=[f"Failed to load image: {str(e)}"]
                )
            
            # Apply processing
            processed_image = await self._process_image(image, request)
            
            # Export using format-specific handler
            if request.output_format in self.supported_formats:
                export_func = self.supported_formats[request.output_format]
                success, errors, warnings = await export_func(processed_image, output_path, request)
            else:
                return ExportResult(
                    success=False,
                    errors=[f"Unsupported export format: {request.output_format}"]
                )
            
            # Calculate results
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            if success and output_path.exists():
                file_size_output = output_path.stat().st_size
                compression_ratio = file_size_output / file_size_original if file_size_original > 0 else 1.0
                
                return ExportResult(
                    success=True,
                    output_path=output_path,
                    original_size=original_size,
                    output_size=processed_image.size,
                    file_size_original=file_size_original,
                    file_size_output=file_size_output,
                    compression_ratio=compression_ratio,
                    processing_time=processing_time,
                    warnings=warnings,
                    metadata={
                        "format": request.output_format.value,
                        "quality": request.quality,
                        "watermarked": request.apply_watermark,
                        "resized": request.resize_config is not None,
                        "enhanced": request.enhance_colors or request.sharpen or request.auto_contrast
                    }
                )
            else:
                return ExportResult(
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    processing_time=processing_time
                )
                
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Export operation failed: {e}")
            return ExportResult(
                success=False,
                errors=[f"Export operation failed: {str(e)}"],
                processing_time=processing_time
            )
    
    async def export_batch(
        self,
        requests: List[ExportRequest],
        output_dir: Path,
        max_concurrent: int = 5
    ) -> List[ExportResult]:
        """
        Export multiple files in batch with concurrency control.
        
        Args:
            requests: List of export requests.
            output_dir: Output directory for all exports.
            max_concurrent: Maximum concurrent operations.
            
        Returns:
            List of ExportResult objects.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def export_with_semaphore(request: ExportRequest) -> ExportResult:
            async with semaphore:
                return await self.export_file(request, output_dir)
        
        # Execute all exports concurrently
        tasks = [export_with_semaphore(request) for request in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ExportResult(
                    success=False,
                    errors=[f"Batch export error: {str(result)}"]
                ))
            else:
                processed_results.append(result)
        
        logger.info(f"Batch export completed: {len(processed_results)} operations")
        return processed_results
    
    async def _process_image(self, image: Image.Image, request: ExportRequest) -> Image.Image:
        """
        Apply all requested processing to the image.
        
        Args:
            image: Source image.
            request: Export request with processing options.
            
        Returns:
            Processed image.
        """
        # Convert to RGB if necessary (for JPEG compatibility)
        if request.output_format == ExportFormat.JPEG and image.mode in ("RGBA", "LA", "P"):
            # Create white background for transparent images
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            if image.mode in ("RGBA", "LA"):
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert("RGB")
        
        # Apply resizing if requested
        if request.resize_config:
            image = await self._resize_image(image, request.resize_config)
        
        # Apply enhancements
        if request.enhance_colors:
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.2)  # Boost colors by 20%
        
        if request.auto_contrast:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.1)  # Slight contrast boost
        
        if request.sharpen:
            image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=100, threshold=3))
        
        # Apply watermark last (so it appears on top)
        if request.apply_watermark:
            watermark_config = request.watermark_config or self.default_watermark
            image = await self._apply_watermark(image, watermark_config)
        
        return image
    
    async def _resize_image(self, image: Image.Image, config: ResizeConfig) -> Image.Image:
        """
        Resize image according to configuration.
        
        Args:
            image: Source image.
            config: Resize configuration.
            
        Returns:
            Resized image.
        """
        original_width, original_height = image.size
        
        # Calculate target dimensions
        target_width = config.width
        target_height = config.height
        
        # Handle max dimensions
        if config.max_width or config.max_height:
            if config.max_width and original_width > config.max_width:
                target_width = config.max_width
                if config.maintain_aspect:
                    target_height = int((target_width / original_width) * original_height)
            
            if config.max_height and (target_height or original_height) > config.max_height:
                target_height = config.max_height
                if config.maintain_aspect:
                    target_width = int((target_height / original_height) * original_width)
        
        # Handle specific dimensions with aspect ratio
        if config.maintain_aspect and target_width and target_height:
            # Calculate ratios
            width_ratio = target_width / original_width
            height_ratio = target_height / original_height
            
            # Use smaller ratio to maintain aspect ratio within bounds
            ratio = min(width_ratio, height_ratio)
            target_width = int(original_width * ratio)
            target_height = int(original_height * ratio)
        
        # Set defaults if not specified
        target_width = target_width or original_width
        target_height = target_height or original_height
        
        # Check upscaling
        if not config.upscale:
            target_width = min(target_width, original_width)
            target_height = min(target_height, original_height)
        
        # Only resize if dimensions changed
        if target_width != original_width or target_height != original_height:
            # Get resampling method
            resampling_map = {
                "LANCZOS": Image.Resampling.LANCZOS,
                "BILINEAR": Image.Resampling.BILINEAR,
                "BICUBIC": Image.Resampling.BICUBIC,
                "NEAREST": Image.Resampling.NEAREST
            }
            resampling = resampling_map.get(config.resampling, Image.Resampling.LANCZOS)
            
            image = image.resize((target_width, target_height), resampling)
        
        return image
    
    async def _apply_watermark(self, image: Image.Image, config: WatermarkConfig) -> Image.Image:
        """
        Apply watermark to image.
        
        Args:
            image: Source image.
            config: Watermark configuration.
            
        Returns:
            Watermarked image.
        """
        try:
            # Create watermark overlay
            overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Load font
            try:
                # Try to load system fonts
                font_paths = [
                    "/System/Library/Fonts/Arial.ttf",  # macOS
                    "/Windows/Fonts/arial.ttf",         # Windows
                    "/usr/share/fonts/truetype/arial.ttf"  # Linux
                ]
                
                font = None
                for font_path in font_paths:
                    try:
                        font = ImageFont.truetype(font_path, config.font_size)
                        break
                    except:
                        continue
                
                if font is None:
                    font = ImageFont.load_default()
                    
            except Exception:
                font = ImageFont.load_default()
            
            # Calculate text dimensions
            text_bbox = draw.textbbox((0, 0), config.text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Calculate position
            x, y = self._calculate_watermark_position(
                image.size, (text_width, text_height), config.position, config.margin
            )
            
            # Draw background if specified
            if config.background_color:
                bg_padding = 5
                draw.rectangle([
                    x - bg_padding,
                    y - bg_padding,
                    x + text_width + bg_padding,
                    y + text_height + bg_padding
                ], fill=config.background_color)
            
            # Draw shadow if enabled
            if config.enable_shadow:
                shadow_x = x + config.shadow_offset[0]
                shadow_y = y + config.shadow_offset[1]
                draw.text((shadow_x, shadow_y), config.text, fill=config.shadow_color, font=font)
            
            # Draw main text
            text_color = (*config.font_color, int(255 * config.opacity))
            draw.text((x, y), config.text, fill=text_color, font=font)
            
            # Apply rotation if specified
            if config.rotation != 0:
                overlay = overlay.rotate(config.rotation, expand=False)
            
            # Composite with original image
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            watermarked = Image.alpha_composite(image, overlay)
            
            # Convert back to original mode if needed
            if image.mode != 'RGBA':
                watermarked = watermarked.convert(image.mode)
            
            return watermarked
            
        except Exception as e:
            logger.warning(f"Watermark application failed: {e}")
            return image
    
    def _calculate_watermark_position(
        self, 
        image_size: tuple, 
        text_size: tuple, 
        position: WatermarkPosition, 
        margin: int
    ) -> tuple:
        """
        Calculate watermark position based on configuration.
        
        Args:
            image_size: Image dimensions (width, height).
            text_size: Text dimensions (width, height).
            position: Watermark position.
            margin: Margin from edges.
            
        Returns:
            Tuple of (x, y) coordinates.
        """
        img_width, img_height = image_size
        text_width, text_height = text_size
        
        position_map = {
            WatermarkPosition.TOP_LEFT: (margin, margin),
            WatermarkPosition.TOP_RIGHT: (img_width - text_width - margin, margin),
            WatermarkPosition.BOTTOM_LEFT: (margin, img_height - text_height - margin),
            WatermarkPosition.BOTTOM_RIGHT: (img_width - text_width - margin, img_height - text_height - margin),
            WatermarkPosition.CENTER: ((img_width - text_width) // 2, (img_height - text_height) // 2),
            WatermarkPosition.BOTTOM_CENTER: ((img_width - text_width) // 2, img_height - text_height - margin)
        }
        
        return position_map.get(position, position_map[WatermarkPosition.BOTTOM_RIGHT])
    
    async def _export_png(self, image: Image.Image, output_path: Path, request: ExportRequest) -> tuple:
        """Export image as PNG."""
        try:
            save_kwargs = {
                "format": "PNG",
                "optimize": request.optimize
            }
            
            if request.preserve_exif and hasattr(image, 'info') and 'exif' in image.info:
                save_kwargs["exif"] = image.info['exif']
            
            image.save(output_path, **save_kwargs)
            return True, [], []
            
        except Exception as e:
            return False, [f"PNG export failed: {str(e)}"], []
    
    async def _export_jpeg(self, image: Image.Image, output_path: Path, request: ExportRequest) -> tuple:
        """Export image as JPEG."""
        try:
            save_kwargs = {
                "format": "JPEG",
                "quality": request.quality,
                "optimize": request.optimize,
                "progressive": request.progressive
            }
            
            if request.preserve_exif and hasattr(image, 'info') and 'exif' in image.info:
                save_kwargs["exif"] = image.info['exif']
            
            # Ensure RGB mode for JPEG
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            
            image.save(output_path, **save_kwargs)
            return True, [], []
            
        except Exception as e:
            return False, [f"JPEG export failed: {str(e)}"], []
    
    async def _export_webp(self, image: Image.Image, output_path: Path, request: ExportRequest) -> tuple:
        """Export image as WebP."""
        try:
            save_kwargs = {
                "format": "WEBP",
                "quality": request.quality,
                "optimize": request.optimize
            }
            
            if request.preserve_exif and hasattr(image, 'info') and 'exif' in image.info:
                save_kwargs["exif"] = image.info['exif']
            
            image.save(output_path, **save_kwargs)
            return True, [], []
            
        except Exception as e:
            return False, [f"WebP export failed: {str(e)}"], []
    
    async def _export_tiff(self, image: Image.Image, output_path: Path, request: ExportRequest) -> tuple:
        """Export image as TIFF."""
        try:
            save_kwargs = {
                "format": "TIFF",
                "compression": "lzw"  # Use LZW compression
            }
            
            if request.preserve_exif and hasattr(image, 'info') and 'exif' in image.info:
                save_kwargs["exif"] = image.info['exif']
            
            image.save(output_path, **save_kwargs)
            return True, [], []
            
        except Exception as e:
            return False, [f"TIFF export failed: {str(e)}"], []
    
    async def _export_bmp(self, image: Image.Image, output_path: Path, request: ExportRequest) -> tuple:
        """Export image as BMP."""
        try:
            # BMP doesn't support transparency, convert to RGB
            if image.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                if image.mode in ("RGBA", "LA"):
                    background.paste(image, mask=image.split()[-1])
                    image = background
                else:
                    image = image.convert("RGB")
            
            image.save(output_path, "BMP")
            return True, [], ["BMP format does not support transparency or metadata"]
            
        except Exception as e:
            return False, [f"BMP export failed: {str(e)}"], []