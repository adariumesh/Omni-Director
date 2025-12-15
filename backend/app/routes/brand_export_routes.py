"""Brand Export and Compliance API routes."""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db, Asset
from app.services.brand_guard import BrandGuard, BrandGuidelines
from app.services.brand_guidelines_loader import BrandGuidelinesLoader
from app.services.export_engine import ExportEngine, ExportAsset, ExportConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["brand-export"])

# Initialize services
brand_loader = BrandGuidelinesLoader("/Users/adariprasad/weapon/Omni - Director/backend/data/brand_guidelines")
export_engine = ExportEngine("/Users/adariprasad/weapon/Omni - Director/backend/exports")


class BrandGuidelinesUpdateRequest(BaseModel):
    """Brand guidelines update request."""
    brand_name: str
    copyright_text: str
    watermark_enabled: bool = True
    logo_position: str = "bottom_right"
    logo_opacity: float = 0.8
    prohibited_words: List[str] = []
    prohibited_colors: List[str] = []
    required_colors: List[str] = []
    min_resolution: List[int] = [512, 512]


class BrandComplianceCheckRequest(BaseModel):
    """Brand compliance check request."""
    prompt: Optional[str] = None
    request_json: Optional[Dict[str, Any]] = None


class ExportRequest(BaseModel):
    """Asset export request."""
    asset_ids: List[str]
    format_type: str = "portfolio"  # portfolio, archive, presentation
    include_images: bool = True
    include_json: bool = True
    include_metadata: bool = True
    image_format: str = "PNG"
    image_quality: int = 95
    create_zip: bool = True
    apply_watermark: bool = False
    naming_convention: str = "descriptive"


@router.get("/brand/guidelines")
async def get_brand_guidelines():
    """Get current brand guidelines."""
    try:
        guidelines = brand_loader.load_guidelines()
        
        if not guidelines:
            # Return default guidelines
            return {
                "brand_name": "FIBO Omni-Director",
                "copyright_text": "Generated with FIBO Omni-Director Pro",
                "watermark_enabled": True,
                "logo_position": "bottom_right",
                "logo_opacity": 0.8,
                "prohibited_words": [],
                "prohibited_colors": [],
                "required_colors": [],
                "min_resolution": [512, 512],
                "version": "1.0",
                "status": "default"
            }
        
        # Convert loaded guidelines to simple format
        return {
            "brand_name": guidelines.brand_name,
            "copyright_text": f"Generated with {guidelines.brand_name}",
            "watermark_enabled": True,
            "logo_position": "bottom_right",
            "logo_opacity": 0.8,
            "prohibited_words": ["competitor", "unauthorized"],  # Default
            "prohibited_colors": [color.hex_code for color in guidelines.colors if color.usage == "prohibited"],
            "required_colors": [color.hex_code for color in guidelines.colors if color.usage == "primary"],
            "min_resolution": [1024, 1024],  # Default high quality
            "version": guidelines.version,
            "colors": [
                {
                    "name": color.name,
                    "hex_code": color.hex_code,
                    "usage": color.usage,
                    "description": color.description
                }
                for color in guidelines.colors
            ],
            "style": {
                "image_style": guidelines.style.image_style,
                "aspect_ratios": guidelines.style.aspect_ratios,
                "prohibited_elements": guidelines.style.prohibited_elements
            },
            "status": "loaded"
        }
        
    except Exception as e:
        logger.error(f"Failed to get guidelines: {e}")
        raise HTTPException(status_code=500, detail="Failed to load brand guidelines")


@router.post("/brand/guidelines")
async def update_brand_guidelines(request: BrandGuidelinesUpdateRequest):
    """Update brand guidelines."""
    try:
        # Save to JSON file for persistence
        guidelines_data = {
            "brand_name": request.brand_name,
            "version": "1.0",
            "colors": [
                {
                    "name": f"Brand Color {i+1}",
                    "hex_code": color,
                    "rgb": [0, 0, 0],
                    "usage": "primary" if i == 0 else "secondary",
                    "description": f"Brand color {i+1}",
                    "accessibility_rating": "AA"
                }
                for i, color in enumerate(request.required_colors[:3])
            ],
            "typography": [],
            "logo": None,
            "style": {
                "image_style": "professional",
                "contrast_requirements": {"text": 4.5, "background": 3.0},
                "saturation_range": [0.1, 0.8],
                "brightness_range": [0.2, 0.9],
                "aspect_ratios": ["16:9", "1:1", "4:3"],
                "prohibited_elements": ["watermarks", "text_overlays"]
            },
            "custom_rules": {
                "prohibited_words": request.prohibited_words,
                "prohibited_colors": request.prohibited_colors,
                "watermark_settings": {
                    "enabled": request.watermark_enabled,
                    "position": request.logo_position,
                    "opacity": request.logo_opacity
                }
            },
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Save to file
        guidelines_dir = Path("/Users/adariprasad/weapon/Omni - Director/backend/data/brand_guidelines")
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        
        safe_brand_name = request.brand_name.lower().replace(' ', '').replace('-', '')
        filename = f"{safe_brand_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        file_path = guidelines_dir / filename
        
        with open(file_path, 'w') as f:
            json.dump(guidelines_data, f, indent=2)
        
        return {
            "success": True,
            "message": "Brand guidelines updated successfully",
            "file_path": str(file_path),
            "guideline_id": filename,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update guidelines: {e}")
        raise HTTPException(status_code=500, detail="Failed to update brand guidelines")


@router.post("/brand/check")
async def check_brand_compliance(request: BrandComplianceCheckRequest):
    """Check brand compliance for prompt or JSON."""
    try:
        guidelines_spec = brand_loader.load_guidelines()
        
        if not guidelines_spec:
            raise HTTPException(status_code=400, detail="No brand guidelines configured")
        
        # Convert to BrandGuard format
        guidelines = BrandGuidelines(
            prohibited_words=["competitor", "unauthorized", "illegal"],
            required_colors=[color.hex_code for color in guidelines_spec.colors if color.usage == "primary"],
            prohibited_colors=["#FF0000", "#000000"],
            watermark_enabled=True,
            brand_name=guidelines_spec.brand_name
        )
        
        guard = BrandGuard(guidelines)
        
        if request.prompt:
            result = guard.check_prompt_compliance(request.prompt)
            
            return {
                "compliant": result.compliant,
                "score": result.score,
                "violations": [
                    {
                        "type": v.violation_type,
                        "severity": v.severity,
                        "message": v.message,
                        "fix": v.suggested_fix
                    }
                    for v in result.violations
                ],
                "suggestions": [
                    f"Consider using brand colors: {', '.join(guidelines.required_colors)}" if guidelines.required_colors else "Follow brand style guidelines"
                ],
                "metadata": result.metadata
            }
        
        elif request.request_json:
            result = guard.check_json_compliance(request.request_json)
            
            return {
                "compliant": result.compliant,
                "score": result.score,
                "violations": [
                    {
                        "type": v.violation_type,
                        "severity": v.severity,
                        "message": v.message,
                        "fix": v.suggested_fix
                    }
                    for v in result.violations
                ],
                "suggestions": [],
                "metadata": result.metadata
            }
        
        else:
            raise HTTPException(status_code=400, detail="Must provide either 'prompt' or 'request_json'")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compliance check failed: {e}")
        raise HTTPException(status_code=500, detail="Compliance check failed")


@router.post("/export")
async def export_assets(request: ExportRequest, db: Session = Depends(get_db)):
    """Export assets with brand protection."""
    try:
        assets = db.query(Asset).filter(Asset.id.in_(request.asset_ids)).all()
        
        if not assets:
            raise HTTPException(status_code=404, detail="No assets found")
        
        # Convert to export assets format
        export_assets = []
        for asset in assets:
            mock_path = f"/Users/adariprasad/weapon/Omni - Director/data/test_asset_{asset.id}.png"
            
            export_asset = ExportAsset(
                asset_id=asset.id,
                image_url=asset.image_url or f"https://api.example.com/images/{asset.id}",
                prompt=asset.prompt,
                structured_prompt=asset.structured_prompt or asset.prompt,
                request_json=asset.request_json or {},
                metadata=asset.metadata or {},
                seed=asset.seed,
                aspect_ratio=asset.aspect_ratio or "1:1",
                created_at=asset.created_at,
                local_path=mock_path if Path(mock_path).exists() else None
            )
            export_assets.append(export_asset)
        
        # Configure export
        config = ExportConfig(
            include_images=request.include_images,
            include_json=request.include_json,
            include_metadata=request.include_metadata,
            image_format=request.image_format,
            image_quality=request.image_quality,
            create_zip=request.create_zip,
            apply_watermark=request.apply_watermark,
            naming_convention=request.naming_convention,
            export_format=request.format_type
        )
        
        # Run export
        if request.format_type == "portfolio":
            result = export_engine.export_portfolio(export_assets, config)
        elif request.format_type == "archive":
            result = export_engine.export_archive(export_assets, config)
        elif request.format_type == "presentation":
            result = export_engine.export_presentation(export_assets, config)
        else:
            raise HTTPException(status_code=400, detail="Invalid format_type")
        
        return {
            "success": result.success,
            "export_path": result.export_path,
            "file_count": result.file_count,
            "total_size": result.total_size,
            "assets_exported": result.assets_exported,
            "errors": result.errors,
            "warnings": result.warnings,
            "metadata": result.metadata,
            "download_url": None,
            "timestamp": result.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/assets")
async def list_assets(db: Session = Depends(get_db)):
    """List available assets for export."""
    try:
        assets = db.query(Asset).order_by(Asset.created_at.desc()).limit(20).all()
        
        return {
            "assets": [
                {
                    "id": asset.id,
                    "prompt": asset.prompt,
                    "image_url": asset.image_url,
                    "aspect_ratio": asset.aspect_ratio,
                    "seed": asset.seed,
                    "created_at": asset.created_at.isoformat() if asset.created_at else None,
                    "project_id": asset.project_id,
                    "metadata": asset.metadata or {}
                }
                for asset in assets
            ],
            "total_count": len(assets),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to list assets: {e}")
        raise HTTPException(status_code=500, detail="Failed to list assets")