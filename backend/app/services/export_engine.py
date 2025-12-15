"""Export Engine for FIBO Omni-Director Pro."""

import json
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from PIL import Image, ImageDraw, ImageFont
import csv
import io
import base64

logger = logging.getLogger(__name__)


@dataclass
class ExportAsset:
    """Represents an asset to be exported."""
    
    asset_id: str
    image_url: str
    prompt: str
    structured_prompt: str
    request_json: Dict[str, Any]
    metadata: Dict[str, Any]
    seed: Optional[int] = None
    aspect_ratio: str = "1:1"
    created_at: Optional[datetime] = None
    local_path: Optional[str] = None


@dataclass
class ExportConfig:
    """Configuration for export operations."""
    
    # Output formats
    include_images: bool = True
    include_json: bool = True
    include_csv: bool = True
    include_metadata: bool = True
    
    # Image settings
    image_format: str = "PNG"  # PNG, JPEG, WEBP
    image_quality: int = 95
    resize_images: bool = False
    target_size: Optional[tuple[int, int]] = None
    
    # Package settings
    create_zip: bool = True
    folder_structure: str = "organized"  # flat, organized, by_date
    naming_convention: str = "descriptive"  # simple, descriptive, timestamp
    
    # Metadata options
    include_prompts: bool = True
    include_technical: bool = True
    include_generation_time: bool = True
    include_brand_info: bool = True
    
    # Brand protection
    apply_watermark: bool = False
    include_license: bool = True
    export_format: str = "portfolio"  # portfolio, archive, presentation


@dataclass
class ExportResult:
    """Result of export operation."""
    
    success: bool
    export_path: str
    file_count: int
    total_size: int
    assets_exported: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class ExportEngine:
    """Advanced export engine for FIBO generations."""
    
    def __init__(self, export_dir: str = "./exports"):
        """Initialize export engine.
        
        Args:
            export_dir: Base directory for exports.
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
    def export_portfolio(self, assets: List[ExportAsset], 
                        config: Optional[ExportConfig] = None) -> ExportResult:
        """Export assets as a professional portfolio.
        
        Args:
            assets: List of assets to export.
            config: Export configuration.
            
        Returns:
            ExportResult with export details.
        """
        config = config or ExportConfig()
        config.export_format = "portfolio"
        
        # Create portfolio-specific structure
        portfolio_name = f"FIBO_Portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        portfolio_dir = self.export_dir / portfolio_name
        
        try:
            # Create folder structure
            folders = self._create_portfolio_structure(portfolio_dir)
            
            # Export assets
            exported_count = 0
            errors = []
            warnings = []
            
            for i, asset in enumerate(assets):
                try:
                    self._export_asset_portfolio(asset, folders, config, i + 1)
                    exported_count += 1
                except Exception as e:
                    error_msg = f"Failed to export asset {asset.asset_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Generate portfolio index
            self._generate_portfolio_index(assets, folders, config)
            
            # Generate README
            self._generate_readme(folders["root"], config, assets)
            
            # Create ZIP if requested
            zip_path = None
            if config.create_zip:
                zip_path = self._create_zip_archive(portfolio_dir)
            
            # Calculate final size
            total_size = sum(f.stat().st_size for f in portfolio_dir.rglob('*') if f.is_file())
            file_count = len(list(portfolio_dir.rglob('*')))
            
            return ExportResult(
                success=len(errors) == 0,
                export_path=str(zip_path if zip_path else portfolio_dir),
                file_count=file_count,
                total_size=total_size,
                assets_exported=exported_count,
                errors=errors,
                warnings=warnings,
                metadata={
                    "portfolio_name": portfolio_name,
                    "format": "portfolio",
                    "zip_created": zip_path is not None
                }
            )
            
        except Exception as e:
            logger.error(f"Portfolio export failed: {e}")
            return ExportResult(
                success=False,
                export_path="",
                file_count=0,
                total_size=0,
                assets_exported=0,
                errors=[f"Portfolio export failed: {str(e)}"]
            )
    
    def export_archive(self, assets: List[ExportAsset], 
                      config: Optional[ExportConfig] = None) -> ExportResult:
        """Export assets as a comprehensive archive.
        
        Args:
            assets: List of assets to export.
            config: Export configuration.
            
        Returns:
            ExportResult with archive details.
        """
        config = config or ExportConfig()
        config.export_format = "archive"
        config.include_technical = True
        config.include_metadata = True
        
        archive_name = f"FIBO_Archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        archive_dir = self.export_dir / archive_name
        
        try:
            # Create archive structure
            folders = self._create_archive_structure(archive_dir)
            
            # Export all data
            self._export_complete_dataset(assets, folders, config)
            
            # Generate archive manifest
            self._generate_archive_manifest(assets, folders)
            
            # Create compressed archive
            zip_path = self._create_zip_archive(archive_dir)
            
            total_size = sum(f.stat().st_size for f in archive_dir.rglob('*') if f.is_file())
            file_count = len(list(archive_dir.rglob('*')))
            
            return ExportResult(
                success=True,
                export_path=str(zip_path),
                file_count=file_count,
                total_size=total_size,
                assets_exported=len(assets),
                metadata={
                    "archive_name": archive_name,
                    "format": "archive",
                    "compressed": True
                }
            )
            
        except Exception as e:
            logger.error(f"Archive export failed: {e}")
            return ExportResult(
                success=False,
                export_path="",
                file_count=0,
                total_size=0,
                assets_exported=0,
                errors=[f"Archive export failed: {str(e)}"]
            )
    
    def export_presentation(self, assets: List[ExportAsset],
                           config: Optional[ExportConfig] = None) -> ExportResult:
        """Export assets as a presentation-ready package.
        
        Args:
            assets: List of assets to export.
            config: Export configuration.
            
        Returns:
            ExportResult with presentation details.
        """
        config = config or ExportConfig()
        config.export_format = "presentation"
        config.image_format = "PNG"
        config.image_quality = 100
        
        presentation_name = f"FIBO_Presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        presentation_dir = self.export_dir / presentation_name
        
        try:
            # Create presentation structure
            folders = self._create_presentation_structure(presentation_dir)
            
            # Export high-quality images
            self._export_presentation_assets(assets, folders, config)
            
            # Generate presentation materials
            self._generate_presentation_materials(assets, folders, config)
            
            total_size = sum(f.stat().st_size for f in presentation_dir.rglob('*') if f.is_file())
            file_count = len(list(presentation_dir.rglob('*')))
            
            return ExportResult(
                success=True,
                export_path=str(presentation_dir),
                file_count=file_count,
                total_size=total_size,
                assets_exported=len(assets),
                metadata={
                    "presentation_name": presentation_name,
                    "format": "presentation"
                }
            )
            
        except Exception as e:
            logger.error(f"Presentation export failed: {e}")
            return ExportResult(
                success=False,
                export_path="",
                file_count=0,
                total_size=0,
                assets_exported=0,
                errors=[f"Presentation export failed: {str(e)}"]
            )
    
    def _create_portfolio_structure(self, base_dir: Path) -> Dict[str, Path]:
        """Create portfolio folder structure."""
        folders = {
            "root": base_dir,
            "images": base_dir / "images",
            "thumbnails": base_dir / "thumbnails", 
            "data": base_dir / "data",
            "metadata": base_dir / "metadata",
            "documentation": base_dir / "documentation"
        }
        
        for folder in folders.values():
            folder.mkdir(parents=True, exist_ok=True)
            
        return folders
    
    def _create_archive_structure(self, base_dir: Path) -> Dict[str, Path]:
        """Create archive folder structure."""
        folders = {
            "root": base_dir,
            "images": base_dir / "images" / "originals",
            "processed": base_dir / "images" / "processed",
            "data": base_dir / "data",
            "json": base_dir / "data" / "json",
            "csv": base_dir / "data" / "csv",
            "metadata": base_dir / "metadata",
            "logs": base_dir / "logs",
            "documentation": base_dir / "documentation"
        }
        
        for folder in folders.values():
            folder.mkdir(parents=True, exist_ok=True)
            
        return folders
    
    def _create_presentation_structure(self, base_dir: Path) -> Dict[str, Path]:
        """Create presentation folder structure."""
        folders = {
            "root": base_dir,
            "images": base_dir / "high_resolution",
            "thumbnails": base_dir / "thumbnails",
            "slides": base_dir / "slide_materials",
            "templates": base_dir / "templates"
        }
        
        for folder in folders.values():
            folder.mkdir(parents=True, exist_ok=True)
            
        return folders
    
    def _export_asset_portfolio(self, asset: ExportAsset, folders: Dict[str, Path],
                               config: ExportConfig, index: int) -> None:
        """Export single asset for portfolio."""
        # Generate filename
        filename = self._generate_filename(asset, config, index)
        
        # Save image
        if config.include_images and asset.local_path and Path(asset.local_path).exists():
            image_path = folders["images"] / f"{filename}.{config.image_format.lower()}"
            self._process_and_save_image(asset.local_path, image_path, config)
            
            # Create thumbnail
            thumbnail_path = folders["thumbnails"] / f"{filename}_thumb.{config.image_format.lower()}"
            self._create_thumbnail(asset.local_path, thumbnail_path, (300, 300))
        
        # Save JSON data
        if config.include_json:
            json_path = folders["data"] / f"{filename}.json"
            self._save_asset_json(asset, json_path, config)
        
        # Save metadata
        if config.include_metadata:
            metadata_path = folders["metadata"] / f"{filename}_meta.json"
            self._save_asset_metadata(asset, metadata_path, config)
    
    def _export_asset_archive(self, asset: ExportAsset, folders: Dict[str, Path],
                             config: ExportConfig, index: int) -> None:
        """Export single asset for archive (similar to portfolio but for archive structure)."""
        filename = self._generate_filename(asset, config, index)
        
        # Save image
        if config.include_images and asset.local_path and Path(asset.local_path).exists():
            image_path = folders["images"] / f"{filename}.{config.image_format.lower()}"
            self._process_and_save_image(asset.local_path, image_path, config)
        
        # Save JSON data
        if config.include_json:
            json_path = folders["data"] / f"{filename}.json"
            self._save_asset_json(asset, json_path, config)
        
        # Save metadata
        if config.include_metadata:
            metadata_path = folders["metadata"] / f"{filename}_meta.json"
            self._save_asset_metadata(asset, metadata_path, config)
    
    def _export_complete_dataset(self, assets: List[ExportAsset], 
                                folders: Dict[str, Path], config: ExportConfig) -> None:
        """Export complete dataset for archive."""
        # Export individual assets
        for i, asset in enumerate(assets):
            # Adapt folders for archive structure
            archive_folders = {
                "images": folders["images"],
                "thumbnails": folders.get("processed", folders["images"]),
                "data": folders["data"],
                "metadata": folders["metadata"]
            }
            self._export_asset_archive(asset, archive_folders, config, i + 1)
        
        # Export aggregate data
        if config.include_csv:
            csv_path = folders["csv"] / "assets_summary.csv"
            self._export_csv_summary(assets, csv_path)
        
        # Export complete JSON
        json_path = folders["json"] / "complete_dataset.json"
        self._export_complete_json(assets, json_path)
    
    def _export_presentation_assets(self, assets: List[ExportAsset],
                                   folders: Dict[str, Path], config: ExportConfig) -> None:
        """Export assets optimized for presentation."""
        for i, asset in enumerate(assets):
            filename = self._generate_filename(asset, config, i + 1)
            
            if asset.local_path and Path(asset.local_path).exists():
                # High-resolution version
                hr_path = folders["images"] / f"{filename}_HR.png"
                self._process_and_save_image(asset.local_path, hr_path, config, optimize_for="presentation")
                
                # Thumbnail for slide use
                thumb_path = folders["thumbnails"] / f"{filename}_slide.png"
                self._create_thumbnail(asset.local_path, thumb_path, (800, 600))
    
    def _process_and_save_image(self, source_path: str, output_path: Path,
                               config: ExportConfig, optimize_for: str = "portfolio") -> None:
        """Process and save image with optimization."""
        try:
            image = Image.open(source_path)
            
            # Resize if configured
            if config.resize_images and config.target_size:
                image = image.resize(config.target_size, Image.Resampling.LANCZOS)
            
            # Apply watermark if configured
            if config.apply_watermark:
                image = self._apply_export_watermark(image)
            
            # Optimize based on use case
            if optimize_for == "presentation":
                # Maximum quality for presentations
                save_kwargs = {"quality": 100, "optimize": True, "dpi": (300, 300)}
            else:
                save_kwargs = {"quality": config.image_quality, "optimize": True}
            
            # Save with format-specific options
            if config.image_format.upper() == "JPEG":
                if image.mode in ("RGBA", "LA", "P"):
                    image = image.convert("RGB")
                image.save(output_path, "JPEG", **save_kwargs)
            else:
                image.save(output_path, config.image_format, **save_kwargs)
                
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            raise
    
    def _create_thumbnail(self, source_path: str, output_path: Path, size: tuple[int, int]) -> None:
        """Create thumbnail image."""
        try:
            image = Image.open(source_path)
            image.thumbnail(size, Image.Resampling.LANCZOS)
            image.save(output_path, "PNG", optimize=True)
        except Exception as e:
            logger.error(f"Thumbnail creation failed: {e}")
    
    def _apply_export_watermark(self, image: Image.Image) -> Image.Image:
        """Apply subtle export watermark."""
        try:
            overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            text = "FIBO Omni-Director Pro"
            try:
                font = ImageFont.truetype("Arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = image.width - text_width - 20
            y = image.height - text_height - 20
            
            draw.text((x, y), text, fill=(255, 255, 255, 100), font=font)
            
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            return Image.alpha_composite(image, overlay).convert('RGB')
            
        except Exception as e:
            logger.warning(f"Watermark failed: {e}")
            return image
    
    def _generate_filename(self, asset: ExportAsset, config: ExportConfig, index: int) -> str:
        """Generate filename based on naming convention."""
        if config.naming_convention == "simple":
            return f"image_{index:03d}"
        elif config.naming_convention == "timestamp":
            timestamp = asset.created_at.strftime("%Y%m%d_%H%M%S") if asset.created_at else datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"fibo_{timestamp}_{index:03d}"
        else:  # descriptive
            # Create safe filename from prompt
            safe_prompt = "".join(c for c in asset.prompt[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_prompt = safe_prompt.replace(' ', '_')
            return f"{index:03d}_{safe_prompt}_{asset.seed or 'noseed'}"
    
    def _save_asset_json(self, asset: ExportAsset, output_path: Path, config: ExportConfig) -> None:
        """Save asset data as JSON."""
        data = {
            "asset_id": asset.asset_id,
            "prompt": asset.prompt,
            "structured_prompt": asset.structured_prompt,
            "request_json": asset.request_json,
            "seed": asset.seed,
            "aspect_ratio": asset.aspect_ratio
        }
        
        if config.include_metadata:
            data["metadata"] = asset.metadata
        
        if config.include_generation_time and asset.created_at:
            data["created_at"] = asset.created_at.isoformat()
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_asset_metadata(self, asset: ExportAsset, output_path: Path, config: ExportConfig) -> None:
        """Save extended metadata."""
        metadata = {
            "asset_id": asset.asset_id,
            "generation_metadata": asset.metadata,
            "export_timestamp": datetime.utcnow().isoformat(),
            "export_config": {
                "format": config.image_format,
                "quality": config.image_quality,
                "watermarked": config.apply_watermark
            }
        }
        
        if config.include_brand_info:
            metadata["brand_info"] = {
                "tool": "FIBO Omni-Director Pro",
                "version": "1.0.0",
                "license": "Generated content subject to terms of use"
            }
        
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _export_csv_summary(self, assets: List[ExportAsset], output_path: Path) -> None:
        """Export assets summary as CSV."""
        with open(output_path, 'w', newline='') as csvfile:
            fieldnames = ['asset_id', 'prompt', 'seed', 'aspect_ratio', 'created_at', 'mode', 'parameters']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for asset in assets:
                writer.writerow({
                    'asset_id': asset.asset_id,
                    'prompt': asset.prompt,
                    'seed': asset.seed,
                    'aspect_ratio': asset.aspect_ratio,
                    'created_at': asset.created_at.isoformat() if asset.created_at else '',
                    'mode': asset.metadata.get('mode', 'unknown'),
                    'parameters': json.dumps(asset.request_json)
                })
    
    def _export_complete_json(self, assets: List[ExportAsset], output_path: Path) -> None:
        """Export complete dataset as JSON."""
        dataset = {
            "export_info": {
                "tool": "FIBO Omni-Director Pro",
                "export_date": datetime.utcnow().isoformat(),
                "asset_count": len(assets)
            },
            "assets": [
                {
                    "asset_id": asset.asset_id,
                    "prompt": asset.prompt,
                    "structured_prompt": asset.structured_prompt,
                    "request_json": asset.request_json,
                    "metadata": asset.metadata,
                    "seed": asset.seed,
                    "aspect_ratio": asset.aspect_ratio,
                    "created_at": asset.created_at.isoformat() if asset.created_at else None
                }
                for asset in assets
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(dataset, f, indent=2)
    
    def _generate_portfolio_index(self, assets: List[ExportAsset], 
                                 folders: Dict[str, Path], config: ExportConfig) -> None:
        """Generate HTML portfolio index."""
        html_content = self._create_portfolio_html(assets, config)
        index_path = folders["root"] / "index.html"
        
        with open(index_path, 'w') as f:
            f.write(html_content)
    
    def _create_portfolio_html(self, assets: List[ExportAsset], config: ExportConfig) -> str:
        """Create HTML content for portfolio."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>FIBO Portfolio</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .header { text-align: center; margin-bottom: 40px; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .item { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .item img { width: 100%; border-radius: 4px; margin-bottom: 15px; }
        .prompt { font-size: 14px; color: #666; margin-bottom: 10px; }
        .metadata { font-size: 12px; color: #999; }
        .footer { text-align: center; margin-top: 40px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 FIBO Portfolio</h1>
        <p>Generated with FIBO Omni-Director Pro</p>
    </div>
    <div class="gallery">
"""
        
        for i, asset in enumerate(assets):
            filename = self._generate_filename(asset, config, i + 1)
            html += f"""
        <div class="item">
            <img src="thumbnails/{filename}_thumb.{config.image_format.lower()}" alt="Generated Image">
            <div class="prompt">"{asset.prompt}"</div>
            <div class="metadata">
                Seed: {asset.seed or 'Random'} | 
                Ratio: {asset.aspect_ratio} |
                Mode: {asset.metadata.get('mode', 'Unknown').title()}
            </div>
        </div>
"""
        
        html += """
    </div>
    <div class="footer">
        <p>Portfolio generated on """ + datetime.now().strftime("%Y-%m-%d %H:%M") + """</p>
    </div>
</body>
</html>
"""
        return html
    
    def _generate_readme(self, output_dir: Path, config: ExportConfig, assets: List[ExportAsset]) -> None:
        """Generate README file."""
        readme_content = f"""# FIBO Portfolio Export

## Overview
This portfolio contains {len(assets)} generated images created with FIBO Omni-Director Pro.

## Contents
- `images/` - Full resolution images
- `thumbnails/` - Thumbnail versions
- `data/` - JSON data files
- `metadata/` - Extended metadata
- `index.html` - Interactive portfolio viewer

## Image Details
- Format: {config.image_format}
- Quality: {config.image_quality}%
- Watermarked: {"Yes" if config.apply_watermark else "No"}

## Usage
1. Open `index.html` in a web browser to view the portfolio
2. Full resolution images are in the `images/` folder
3. JSON data contains generation parameters and prompts

## Generation Info
- Tool: FIBO Omni-Director Pro
- Export Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Total Assets: {len(assets)}

## License
Generated content subject to FIBO Omni-Director Pro terms of use.
"""
        
        with open(output_dir / "README.md", 'w') as f:
            f.write(readme_content)
    
    def _generate_archive_manifest(self, assets: List[ExportAsset], folders: Dict[str, Path]) -> None:
        """Generate archive manifest."""
        manifest = {
            "archive_info": {
                "created_at": datetime.utcnow().isoformat(),
                "tool": "FIBO Omni-Director Pro",
                "version": "1.0.0",
                "asset_count": len(assets)
            },
            "structure": {
                "images/originals/": "Original generated images",
                "images/processed/": "Processed/watermarked images", 
                "data/json/": "Individual asset JSON files",
                "data/csv/": "CSV summary data",
                "metadata/": "Extended metadata files",
                "documentation/": "README and documentation"
            },
            "assets": [asset.asset_id for asset in assets]
        }
        
        with open(folders["root"] / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def _generate_presentation_materials(self, assets: List[ExportAsset],
                                       folders: Dict[str, Path], config: ExportConfig) -> None:
        """Generate presentation materials."""
        # Create presentation outline
        outline = {
            "presentation_title": "FIBO Generation Results",
            "slide_count": len(assets),
            "assets": [
                {
                    "slide_number": i + 1,
                    "title": f"Generation {i + 1}",
                    "prompt": asset.prompt,
                    "image_file": f"{self._generate_filename(asset, config, i + 1)}_HR.png",
                    "thumbnail_file": f"{self._generate_filename(asset, config, i + 1)}_slide.png"
                }
                for i, asset in enumerate(assets)
            ]
        }
        
        with open(folders["slides"] / "presentation_outline.json", 'w') as f:
            json.dump(outline, f, indent=2)
        
        # Create PowerPoint template info
        template_info = """# Presentation Template Guide

## High-Resolution Images
- Location: `high_resolution/`
- Format: PNG (300 DPI)
- Use for: Print materials, large displays

## Slide Thumbnails
- Location: `thumbnails/`
- Size: 800x600 pixels
- Use for: PowerPoint slides, presentations

## Recommended Slide Layout
1. Title slide with overall project info
2. One slide per generation showing:
   - High-resolution image
   - Original prompt
   - Key parameters (seed, mode, etc.)
3. Summary slide with all thumbnails

## PowerPoint Tips
- Insert images using "Insert > Pictures"
- Maintain aspect ratios
- Use thumbnails for overview slides
- Use high-res images for detail slides
"""
        
        with open(folders["templates"] / "template_guide.md", 'w') as f:
            f.write(template_info)
    
    def _create_zip_archive(self, source_dir: Path) -> Path:
        """Create ZIP archive of directory."""
        zip_path = source_dir.with_suffix('.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
        
        return zip_path