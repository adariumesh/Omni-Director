"""
FIBO Portfolio Generator - HTML portfolio creation service.

This service creates professional HTML portfolios with responsive design,
asset metadata integration, custom branding options, and gallery layouts.
Supports multiple templates and themes for different use cases.

Author: FIBO Omni-Director Pro
Version: 2.0.0
"""

import logging
import asyncio
import json
import zipfile
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from PIL import Image

from app.services.file_storage import StoredFile

logger = logging.getLogger(__name__)


class PortfolioTheme(Enum):
    """Available portfolio themes."""
    PROFESSIONAL = "professional"
    CREATIVE = "creative"
    MINIMAL = "minimal"
    DARK = "dark"
    GALLERY = "gallery"
    SHOWCASE = "showcase"


class LayoutStyle(Enum):
    """Portfolio layout styles."""
    GRID = "grid"
    MASONRY = "masonry"
    CAROUSEL = "carousel"
    LIST = "list"
    SLIDESHOW = "slideshow"


@dataclass
class BrandingConfig:
    """Branding configuration for portfolios."""
    
    title: str = "FIBO Portfolio"
    subtitle: str = "Generated with FIBO Omni-Director Pro"
    description: str = "A collection of AI-generated images"
    logo_url: Optional[str] = None
    brand_colors: Dict[str, str] = field(default_factory=lambda: {
        "primary": "#2563eb",
        "secondary": "#64748b", 
        "accent": "#f59e0b",
        "background": "#ffffff",
        "text": "#1e293b"
    })
    custom_css: Optional[str] = None
    footer_text: str = "© 2024 FIBO Omni-Director Pro"


@dataclass
class PortfolioConfig:
    """Configuration for portfolio generation."""
    
    name: str
    template: str = "professional"
    theme: PortfolioTheme = PortfolioTheme.PROFESSIONAL
    layout: LayoutStyle = LayoutStyle.GRID
    output_dir: Path = Path("./portfolios")
    
    # Branding
    branding: BrandingConfig = field(default_factory=BrandingConfig)
    
    # Asset display
    include_metadata: bool = True
    show_prompts: bool = True
    show_technical_info: bool = True
    show_creation_date: bool = True
    
    # Gallery settings
    thumbnail_size: tuple = (400, 400)
    enable_lightbox: bool = True
    enable_search: bool = True
    enable_filters: bool = True
    
    # Export options
    create_zip: bool = True
    include_original_files: bool = False
    include_high_res: bool = True
    
    # Custom options
    custom_pages: List[Dict[str, str]] = field(default_factory=list)
    analytics_code: Optional[str] = None


@dataclass
class PortfolioResult:
    """Result of portfolio generation."""
    
    success: bool
    portfolio_path: Optional[Path] = None
    portfolio_url: Optional[str] = None
    archive_path: Optional[Path] = None
    asset_count: int = 0
    generation_time: float = 0.0
    
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PortfolioGenerator:
    """
    Service for generating professional HTML portfolios.
    
    Features:
    - Multiple responsive templates and themes
    - Customizable branding and colors
    - Asset metadata integration
    - Lightbox galleries with filtering
    - Search and categorization
    - Mobile-friendly design
    - SEO-optimized HTML
    - ZIP export with assets
    """
    
    def __init__(self):
        """Initialize the portfolio generator."""
        self.templates_dir = Path(__file__).parent / "export_templates"
        self.temp_dir = Path("./temp_portfolios")
        
        # Ensure directories exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Portfolio Generator initialized")
    
    async def create_portfolio(
        self,
        files: List[StoredFile],
        config: PortfolioConfig,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> PortfolioResult:
        """
        Create a complete HTML portfolio with specified files.
        
        Args:
            files: List of StoredFile objects to include.
            config: Portfolio configuration.
            progress_callback: Optional progress callback function.
            
        Returns:
            PortfolioResult with generation details.
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate inputs
            if not files:
                return PortfolioResult(
                    success=False,
                    errors=["No files provided for portfolio"]
                )
            
            if progress_callback:
                progress_callback(0.05)
            
            # Create portfolio directory
            portfolio_name = self._sanitize_filename(config.name)
            portfolio_dir = config.output_dir / portfolio_name
            portfolio_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            assets_dir = portfolio_dir / "assets"
            images_dir = portfolio_dir / "images"
            thumbnails_dir = portfolio_dir / "thumbnails"
            css_dir = portfolio_dir / "css"
            js_dir = portfolio_dir / "js"
            
            for directory in [assets_dir, images_dir, thumbnails_dir, css_dir, js_dir]:
                directory.mkdir(exist_ok=True)
            
            if progress_callback:
                progress_callback(0.1)
            
            # Process assets
            asset_data = await self._process_assets(files, images_dir, thumbnails_dir, config)
            
            if progress_callback:
                progress_callback(0.4)
            
            # Generate HTML content
            html_content = await self._generate_html(asset_data, config)
            
            # Generate CSS
            css_content = await self._generate_css(config)
            
            # Generate JavaScript
            js_content = await self._generate_javascript(config)
            
            if progress_callback:
                progress_callback(0.7)
            
            # Write files
            (portfolio_dir / "index.html").write_text(html_content, encoding='utf-8')
            (css_dir / "style.css").write_text(css_content, encoding='utf-8')
            (js_dir / "script.js").write_text(js_content, encoding='utf-8')
            
            # Generate metadata file
            metadata = {
                "portfolio_info": {
                    "name": config.name,
                    "created_at": datetime.utcnow().isoformat(),
                    "asset_count": len(files),
                    "theme": config.theme.value,
                    "layout": config.layout.value
                },
                "assets": asset_data,
                "config": {
                    "theme": config.theme.value,
                    "layout": config.layout.value,
                    "include_metadata": config.include_metadata,
                    "show_prompts": config.show_prompts
                }
            }
            
            (portfolio_dir / "portfolio.json").write_text(
                json.dumps(metadata, indent=2), encoding='utf-8'
            )
            
            if progress_callback:
                progress_callback(0.9)
            
            # Create ZIP if requested
            archive_path = None
            if config.create_zip:
                archive_path = await self._create_portfolio_archive(portfolio_dir, config)
            
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            if progress_callback:
                progress_callback(1.0)
            
            result = PortfolioResult(
                success=True,
                portfolio_path=portfolio_dir,
                portfolio_url=f"file://{portfolio_dir / 'index.html'}",
                archive_path=archive_path,
                asset_count=len(files),
                generation_time=generation_time,
                metadata={
                    "theme": config.theme.value,
                    "layout": config.layout.value,
                    "total_files": len(list(portfolio_dir.rglob("*"))),
                    "portfolio_size": sum(f.stat().st_size for f in portfolio_dir.rglob("*") if f.is_file())
                }
            )
            
            logger.info(f"Portfolio created: {portfolio_dir} ({len(files)} assets)")
            return result
            
        except Exception as e:
            logger.error(f"Portfolio generation failed: {e}")
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            return PortfolioResult(
                success=False,
                errors=[f"Portfolio generation failed: {str(e)}"],
                generation_time=generation_time
            )
    
    async def _process_assets(
        self,
        files: List[StoredFile],
        images_dir: Path,
        thumbnails_dir: Path,
        config: PortfolioConfig
    ) -> List[Dict[str, Any]]:
        """
        Process assets for portfolio inclusion.
        
        Args:
            files: List of files to process.
            images_dir: Directory for full-size images.
            thumbnails_dir: Directory for thumbnails.
            config: Portfolio configuration.
            
        Returns:
            List of asset data dictionaries.
        """
        asset_data = []
        
        for i, file in enumerate(files):
            try:
                if not file.stored_path.exists():
                    logger.warning(f"File not found: {file.stored_path}")
                    continue
                
                # Copy main image (or create high-res if requested)
                image_filename = f"img_{i+1:03d}_{self._sanitize_filename(file.original_filename)}"
                image_path = images_dir / image_filename
                
                if config.include_high_res:
                    # Copy original or create high-quality version
                    await self._copy_or_process_image(file.stored_path, image_path, quality=95)
                else:
                    # Create web-optimized version
                    await self._copy_or_process_image(file.stored_path, image_path, quality=85, max_size=(1920, 1920))
                
                # Create thumbnail
                thumbnail_filename = f"thumb_{i+1:03d}_{self._sanitize_filename(file.original_filename)}"
                thumbnail_path = thumbnails_dir / thumbnail_filename
                await self._create_thumbnail(file.stored_path, thumbnail_path, config.thumbnail_size)
                
                # Get image dimensions
                try:
                    with Image.open(file.stored_path) as img:
                        width, height = img.size
                        image_format = img.format
                except Exception:
                    width, height = 0, 0
                    image_format = "Unknown"
                
                # Extract metadata
                metadata = file.metadata or {}
                
                asset_info = {
                    "id": f"asset_{i+1:03d}",
                    "file_id": file.file_id,
                    "original_filename": file.original_filename,
                    "image_filename": image_filename,
                    "thumbnail_filename": thumbnail_filename,
                    "title": self._generate_title(file, metadata),
                    "description": self._generate_description(file, metadata),
                    "width": width,
                    "height": height,
                    "format": image_format,
                    "file_size": file.file_size,
                    "created_at": file.created_at.isoformat() if file.created_at else None,
                    "metadata": metadata,
                    "tags": self._extract_tags(metadata),
                    "category": self._extract_category(metadata)
                }
                
                # Add prompt information if available
                if metadata and config.show_prompts:
                    asset_info["prompt"] = metadata.get("prompt", "")
                    asset_info["structured_prompt"] = metadata.get("structured_prompt", "")
                
                # Add technical information if available
                if metadata and config.show_technical_info:
                    asset_info["technical_info"] = {
                        "seed": metadata.get("seed"),
                        "aspect_ratio": metadata.get("aspect_ratio"),
                        "mode": metadata.get("mode"),
                        "parameters": metadata.get("parameters", {})
                    }
                
                asset_data.append(asset_info)
                
            except Exception as e:
                logger.warning(f"Failed to process asset {file.file_id}: {e}")
                continue
        
        return asset_data
    
    async def _copy_or_process_image(
        self,
        source_path: Path,
        target_path: Path,
        quality: int = 95,
        max_size: Optional[tuple] = None
    ) -> None:
        """
        Copy or process an image file.
        
        Args:
            source_path: Source image path.
            target_path: Target image path.
            quality: JPEG quality if conversion needed.
            max_size: Maximum dimensions (width, height).
        """
        try:
            with Image.open(source_path) as img:
                # Resize if max_size specified
                if max_size:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save with appropriate format
                if target_path.suffix.lower() in ['.jpg', '.jpeg']:
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    img.save(target_path, 'JPEG', quality=quality, optimize=True)
                else:
                    img.save(target_path, optimize=True)
                    
        except Exception as e:
            logger.warning(f"Image processing failed, copying original: {e}")
            # Fallback: copy original file
            import shutil
            shutil.copy2(source_path, target_path)
    
    async def _create_thumbnail(self, source_path: Path, target_path: Path, size: tuple) -> None:
        """
        Create a thumbnail image.
        
        Args:
            source_path: Source image path.
            target_path: Target thumbnail path.
            size: Thumbnail size (width, height).
        """
        try:
            with Image.open(source_path) as img:
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Ensure RGB for JPEG
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode in ('RGBA', 'LA'):
                        background.paste(img, mask=img.split()[-1])
                        img = background
                
                # Save as JPEG with high quality
                img.save(target_path.with_suffix('.jpg'), 'JPEG', quality=90, optimize=True)
                
        except Exception as e:
            logger.warning(f"Thumbnail creation failed: {e}")
    
    async def _generate_html(self, asset_data: List[Dict[str, Any]], config: PortfolioConfig) -> str:
        """
        Generate HTML content for the portfolio.
        
        Args:
            asset_data: Processed asset data.
            config: Portfolio configuration.
            
        Returns:
            HTML content string.
        """
        # Check if template file exists
        template_path = self.templates_dir / f"{config.template}.html"
        
        if template_path.exists():
            # Load custom template
            template_content = template_path.read_text(encoding='utf-8')
            # TODO: Implement template variable replacement
            html_content = template_content
        else:
            # Use built-in template
            html_content = await self._generate_builtin_template(asset_data, config)
        
        return html_content
    
    async def _generate_builtin_template(self, asset_data: List[Dict[str, Any]], config: PortfolioConfig) -> str:
        """
        Generate HTML using built-in template.
        
        Args:
            asset_data: Processed asset data.
            config: Portfolio configuration.
            
        Returns:
            HTML content string.
        """
        # Generate asset cards
        asset_cards = []
        for asset in asset_data:
            card_html = f"""
            <div class="asset-card" data-category="{asset.get('category', 'uncategorized')}" data-tags="{','.join(asset.get('tags', []))}">
                <div class="asset-image">
                    <img src="thumbnails/{asset['thumbnail_filename']}" 
                         alt="{asset['title']}" 
                         data-fullsize="images/{asset['image_filename']}"
                         loading="lazy">
                    <div class="asset-overlay">
                        <button class="view-btn" onclick="openLightbox('{asset['id']}')">View</button>
                    </div>
                </div>
                <div class="asset-info">
                    <h3 class="asset-title">{asset['title']}</h3>
                    <p class="asset-description">{asset.get('description', '')}</p>
                    <div class="asset-meta">
                        <span class="asset-size">{asset['width']} × {asset['height']}</span>
                        {f'<span class="asset-date">{asset["created_at"][:10]}</span>' if asset.get('created_at') else ''}
                    </div>
            """
            
            if config.show_prompts and asset.get('prompt'):
                card_html += f'<div class="asset-prompt">"{asset["prompt"]}"</div>'
            
            if config.show_technical_info and asset.get('technical_info'):
                tech_info = asset['technical_info']
                card_html += f"""
                <div class="asset-technical">
                    {f'<span>Seed: {tech_info.get("seed", "N/A")}</span>' if tech_info.get("seed") else ''}
                    {f'<span>Mode: {tech_info.get("mode", "N/A")}</span>' if tech_info.get("mode") else ''}
                </div>
                """
            
            card_html += "</div></div>"
            asset_cards.append(card_html)
        
        assets_html = "\n".join(asset_cards)
        
        # Build search and filter HTML
        search_html = ""
        if config.enable_search or config.enable_filters:
            search_html = '<div class="portfolio-controls">'
            
            if config.enable_search:
                search_html += '''
                <div class="search-container">
                    <input type="text" id="search-input" placeholder="Search assets..." onkeyup="filterAssets()">
                </div>
                '''
            
            if config.enable_filters:
                # Get unique categories
                categories = sorted(set(asset.get('category', 'uncategorized') for asset in asset_data))
                category_options = ''.join(f'<option value="{cat}">{cat.title()}</option>' for cat in categories)
                
                search_html += f'''
                <div class="filter-container">
                    <select id="category-filter" onchange="filterAssets()">
                        <option value="">All Categories</option>
                        {category_options}
                    </select>
                </div>
                '''
            
            search_html += '</div>'
        
        # Main HTML template
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.branding.title}</title>
    <meta name="description" content="{config.branding.description}">
    <link rel="stylesheet" href="css/style.css">
    {f'<style>{config.branding.custom_css}</style>' if config.branding.custom_css else ''}
    {config.analytics_code or ''}
</head>
<body class="theme-{config.theme.value}">
    <header class="portfolio-header">
        <div class="container">
            {f'<img src="{config.branding.logo_url}" alt="Logo" class="logo">' if config.branding.logo_url else ''}
            <h1 class="portfolio-title">{config.branding.title}</h1>
            <p class="portfolio-subtitle">{config.branding.subtitle}</p>
            <p class="portfolio-description">{config.branding.description}</p>
        </div>
    </header>
    
    <main class="portfolio-main">
        <div class="container">
            {search_html}
            
            <div class="portfolio-stats">
                <span class="stat-item">{len(asset_data)} Assets</span>
                <span class="stat-item">Generated {datetime.now().strftime('%B %Y')}</span>
            </div>
            
            <div class="portfolio-gallery layout-{config.layout.value}">
                {assets_html}
            </div>
        </div>
    </main>
    
    {'<div id="lightbox" class="lightbox" onclick="closeLightbox()"><img id="lightbox-img" src="" alt=""><div class="lightbox-close">&times;</div></div>' if config.enable_lightbox else ''}
    
    <footer class="portfolio-footer">
        <div class="container">
            <p>{config.branding.footer_text}</p>
            <p class="generator-credit">Generated with FIBO Omni-Director Pro</p>
        </div>
    </footer>
    
    <script src="js/script.js"></script>
</body>
</html>"""
        
        return html_content
    
    async def _generate_css(self, config: PortfolioConfig) -> str:
        """
        Generate CSS styles for the portfolio.
        
        Args:
            config: Portfolio configuration.
            
        Returns:
            CSS content string.
        """
        colors = config.branding.brand_colors
        
        css_content = f"""
/* FIBO Portfolio Styles */
:root {{
    --color-primary: {colors.get('primary', '#2563eb')};
    --color-secondary: {colors.get('secondary', '#64748b')};
    --color-accent: {colors.get('accent', '#f59e0b')};
    --color-background: {colors.get('background', '#ffffff')};
    --color-text: {colors.get('text', '#1e293b')};
    --color-border: #e2e8f0;
    --color-shadow: rgba(0, 0, 0, 0.1);
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: var(--color-text);
    background-color: var(--color-background);
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}}

/* Header */
.portfolio-header {{
    background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
    color: white;
    padding: 60px 0;
    text-align: center;
}}

.portfolio-title {{
    font-size: 3em;
    font-weight: 700;
    margin-bottom: 10px;
}}

.portfolio-subtitle {{
    font-size: 1.2em;
    opacity: 0.9;
    margin-bottom: 20px;
}}

.portfolio-description {{
    font-size: 1.1em;
    opacity: 0.8;
    max-width: 600px;
    margin: 0 auto;
}}

.logo {{
    height: 60px;
    margin-bottom: 20px;
}}

/* Controls */
.portfolio-controls {{
    display: flex;
    gap: 20px;
    margin: 40px 0;
    align-items: center;
}}

.search-container input,
.filter-container select {{
    padding: 12px 16px;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    font-size: 16px;
    background: white;
}}

.search-container input {{
    min-width: 300px;
}}

/* Stats */
.portfolio-stats {{
    margin-bottom: 40px;
    text-align: center;
}}

.stat-item {{
    display: inline-block;
    margin: 0 20px;
    padding: 8px 16px;
    background: var(--color-primary);
    color: white;
    border-radius: 20px;
    font-size: 14px;
}}

/* Gallery Layouts */
.portfolio-gallery {{
    margin-bottom: 60px;
}}

.layout-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 30px;
}}

.layout-masonry {{
    columns: 3;
    column-gap: 30px;
}}

.layout-masonry .asset-card {{
    break-inside: avoid;
    margin-bottom: 30px;
}}

.layout-list {{
    display: flex;
    flex-direction: column;
    gap: 20px;
}}

.layout-list .asset-card {{
    display: flex;
    align-items: center;
    gap: 20px;
}}

.layout-list .asset-image {{
    flex-shrink: 0;
    width: 150px;
    height: 150px;
}}

/* Asset Cards */
.asset-card {{
    background: white;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 6px var(--color-shadow);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}}

.asset-card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 8px 25px var(--color-shadow);
}}

.asset-image {{
    position: relative;
    overflow: hidden;
}}

.asset-image img {{
    width: 100%;
    height: 250px;
    object-fit: cover;
    transition: transform 0.3s ease;
}}

.asset-card:hover .asset-image img {{
    transform: scale(1.05);
}}

.asset-overlay {{
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.3s ease;
}}

.asset-card:hover .asset-overlay {{
    opacity: 1;
}}

.view-btn {{
    padding: 10px 20px;
    background: var(--color-primary);
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    transition: background 0.3s ease;
}}

.view-btn:hover {{
    background: var(--color-accent);
}}

.asset-info {{
    padding: 20px;
}}

.asset-title {{
    font-size: 1.2em;
    font-weight: 600;
    margin-bottom: 8px;
    color: var(--color-text);
}}

.asset-description {{
    color: var(--color-secondary);
    margin-bottom: 15px;
    font-size: 14px;
    line-height: 1.4;
}}

.asset-meta {{
    display: flex;
    gap: 15px;
    font-size: 12px;
    color: var(--color-secondary);
    margin-bottom: 10px;
}}

.asset-prompt {{
    background: #f8fafc;
    padding: 12px;
    border-radius: 6px;
    font-style: italic;
    font-size: 13px;
    color: var(--color-secondary);
    margin-top: 10px;
    border-left: 3px solid var(--color-primary);
}}

.asset-technical {{
    margin-top: 10px;
    font-size: 11px;
    color: var(--color-secondary);
}}

.asset-technical span {{
    display: inline-block;
    margin-right: 10px;
    padding: 2px 6px;
    background: #e2e8f0;
    border-radius: 3px;
}}

/* Lightbox */
.lightbox {{
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.9);
    z-index: 1000;
    align-items: center;
    justify-content: center;
}}

.lightbox img {{
    max-width: 90%;
    max-height: 90%;
    object-fit: contain;
}}

.lightbox-close {{
    position: absolute;
    top: 30px;
    right: 50px;
    color: white;
    font-size: 40px;
    cursor: pointer;
}}

/* Footer */
.portfolio-footer {{
    background: #1e293b;
    color: white;
    text-align: center;
    padding: 40px 0;
}}

.generator-credit {{
    font-size: 14px;
    opacity: 0.7;
    margin-top: 10px;
}}

/* Themes */
.theme-dark {{
    --color-background: #0f172a;
    --color-text: #f1f5f9;
    --color-border: #334155;
}}

.theme-dark .asset-card {{
    background: #1e293b;
    color: var(--color-text);
}}

.theme-minimal {{
    --color-primary: #000000;
    --color-secondary: #6b7280;
    --color-accent: #000000;
}}

/* Responsive */
@media (max-width: 768px) {{
    .portfolio-title {{
        font-size: 2em;
    }}
    
    .layout-grid {{
        grid-template-columns: 1fr;
        gap: 20px;
    }}
    
    .layout-masonry {{
        columns: 1;
    }}
    
    .layout-list .asset-card {{
        flex-direction: column;
    }}
    
    .layout-list .asset-image {{
        width: 100%;
        height: 200px;
    }}
    
    .portfolio-controls {{
        flex-direction: column;
        gap: 10px;
    }}
    
    .search-container input {{
        min-width: 100%;
    }}
}}

/* Animations */
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.asset-card {{
    animation: fadeIn 0.5s ease;
}}

/* Hidden class for filtering */
.hidden {{
    display: none !important;
}}
        """
        
        return css_content
    
    async def _generate_javascript(self, config: PortfolioConfig) -> str:
        """
        Generate JavaScript for portfolio functionality.
        
        Args:
            config: Portfolio configuration.
            
        Returns:
            JavaScript content string.
        """
        js_content = """
// FIBO Portfolio JavaScript

// Lightbox functionality
function openLightbox(assetId) {
    const assetCard = document.querySelector(`[data-id="${assetId}"], .asset-card:has([onclick*="${assetId}"])`);
    if (assetCard) {
        const img = assetCard.querySelector('img[data-fullsize]');
        if (img) {
            const lightbox = document.getElementById('lightbox');
            const lightboxImg = document.getElementById('lightbox-img');
            
            lightboxImg.src = img.dataset.fullsize;
            lightboxImg.alt = img.alt;
            lightbox.style.display = 'flex';
        }
    }
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    lightbox.style.display = 'none';
}

// Search and filter functionality
function filterAssets() {
    const searchInput = document.getElementById('search-input');
    const categoryFilter = document.getElementById('category-filter');
    const assetCards = document.querySelectorAll('.asset-card');
    
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    const selectedCategory = categoryFilter ? categoryFilter.value : '';
    
    assetCards.forEach(card => {
        const title = card.querySelector('.asset-title')?.textContent.toLowerCase() || '';
        const description = card.querySelector('.asset-description')?.textContent.toLowerCase() || '';
        const prompt = card.querySelector('.asset-prompt')?.textContent.toLowerCase() || '';
        const category = card.dataset.category || '';
        const tags = card.dataset.tags || '';
        
        const matchesSearch = !searchTerm || 
            title.includes(searchTerm) || 
            description.includes(searchTerm) || 
            prompt.includes(searchTerm) ||
            tags.includes(searchTerm);
        
        const matchesCategory = !selectedCategory || category === selectedCategory;
        
        if (matchesSearch && matchesCategory) {
            card.classList.remove('hidden');
        } else {
            card.classList.add('hidden');
        }
    });
    
    // Update visible count
    updateVisibleCount();
}

function updateVisibleCount() {
    const visibleCards = document.querySelectorAll('.asset-card:not(.hidden)');
    const totalCards = document.querySelectorAll('.asset-card');
    
    // Find and update stats if they exist
    const statsContainer = document.querySelector('.portfolio-stats');
    if (statsContainer) {
        const statItem = statsContainer.querySelector('.stat-item');
        if (statItem && visibleCards.length !== totalCards.length) {
            statItem.textContent = `${visibleCards.length} of ${totalCards.length} Assets`;
        } else if (statItem) {
            statItem.textContent = `${totalCards.length} Assets`;
        }
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeLightbox();
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Setup lazy loading for images
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src || img.src;
                    img.classList.remove('lazy');
                    observer.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[loading="lazy"]').forEach(img => {
            imageObserver.observe(img);
        });
    }
    
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    console.log('FIBO Portfolio initialized');
});
        """
        
        if not config.enable_lightbox:
            # Remove lightbox functions if not enabled
            js_content = js_content.replace(
                "// Lightbox functionality\nfunction openLightbox", 
                "// Lightbox disabled\n// function openLightbox"
            ).replace(
                "function closeLightbox", 
                "// function closeLightbox"
            )
        
        return js_content
    
    async def _create_portfolio_archive(self, portfolio_dir: Path, config: PortfolioConfig) -> Path:
        """
        Create a ZIP archive of the portfolio.
        
        Args:
            portfolio_dir: Portfolio directory to archive.
            config: Portfolio configuration.
            
        Returns:
            Path to created archive.
        """
        archive_name = f"{self._sanitize_filename(config.name)}_portfolio.zip"
        archive_path = portfolio_dir.parent / archive_name
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in portfolio_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(portfolio_dir)
                    zipf.write(file_path, arcname)
        
        return archive_path
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem safety."""
        import re
        # Remove or replace unsafe characters
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        if len(safe_filename) > 100:
            safe_filename = safe_filename[:100]
        return safe_filename
    
    def _generate_title(self, file: StoredFile, metadata: Dict[str, Any]) -> str:
        """Generate a title for an asset."""
        if metadata and metadata.get('prompt'):
            # Use first few words of prompt as title
            prompt = metadata['prompt']
            words = prompt.split()[:5]
            return ' '.join(words).title()
        else:
            # Use filename without extension
            return Path(file.original_filename).stem.replace('_', ' ').title()
    
    def _generate_description(self, file: StoredFile, metadata: Dict[str, Any]) -> str:
        """Generate a description for an asset."""
        if metadata and metadata.get('prompt'):
            return metadata['prompt']
        else:
            return f"Generated image from {file.original_filename}"
    
    def _extract_tags(self, metadata: Dict[str, Any]) -> List[str]:
        """Extract tags from metadata."""
        tags = []
        if metadata:
            # Extract from prompt
            prompt = metadata.get('prompt', '')
            if prompt:
                # Simple tag extraction - split on commas
                potential_tags = [tag.strip().lower() for tag in prompt.split(',')]
                tags.extend(potential_tags[:5])  # Limit to 5 tags
        
        return tags
    
    def _extract_category(self, metadata: Dict[str, Any]) -> str:
        """Extract category from metadata."""
        if metadata:
            mode = metadata.get('mode', '')
            if mode:
                return mode.lower()
            
            # Try to infer from prompt
            prompt = metadata.get('prompt', '').lower()
            if any(word in prompt for word in ['portrait', 'person', 'face']):
                return 'portraits'
            elif any(word in prompt for word in ['landscape', 'nature', 'outdoor']):
                return 'landscapes'
            elif any(word in prompt for word in ['abstract', 'artistic', 'creative']):
                return 'abstract'
            elif any(word in prompt for word in ['product', 'object', 'item']):
                return 'products'
        
        return 'general'