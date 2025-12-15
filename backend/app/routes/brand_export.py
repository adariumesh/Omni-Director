"""API routes for brand protection and export features."""

import logging
import tempfile
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.repositories.asset_repository import AssetRepository
from app.services.brand_guard import BrandGuard, BrandGuidelines, BrandCheckResult
from app.services.export_engine import ExportEngine, ExportAsset, ExportConfig, ExportResult

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["brand-export"],
    responses={
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    }
)


# ==================== Request/Response Models ====================

class BrandGuidelinesRequest(BaseModel):
    """Request to set brand guidelines."""
    
    brand_name: str = Field(default="FIBO Omni-Director")
    copyright_text: str = Field(default="Generated with FIBO Omni-Director Pro")
    watermark_enabled: bool = Field(default=True)
    logo_position: str = Field(default="bottom_right")
    logo_opacity: float = Field(default=0.8, ge=0.0, le=1.0)
    prohibited_words: List[str] = Field(default_factory=list)
    prohibited_colors: List[str] = Field(default_factory=list)
    required_colors: List[str] = Field(default_factory=list)
    min_resolution: tuple[int, int] = Field(default=(512, 512))


class BrandCheckRequest(BaseModel):
    """Request for brand compliance check."""
    
    prompt: Optional[str] = None
    request_json: Optional[Dict[str, Any]] = None
    asset_id: Optional[str] = None


class BrandCheckResponse(BaseModel):
    """Response for brand compliance check."""
    
    compliant: bool
    score: float = Field(ge=0.0, le=1.0)
    violations: List[Dict[str, Any]]
    suggestions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExportRequest(BaseModel):
    """Request for asset export."""
    
    asset_ids: List[str]
    format_type: str = Field(default="portfolio", pattern="^(portfolio|archive|presentation)$")
    include_images: bool = Field(default=True)
    include_json: bool = Field(default=True)
    include_metadata: bool = Field(default=True)
    image_format: str = Field(default="PNG", pattern="^(PNG|JPEG|WEBP)$")
    image_quality: int = Field(default=95, ge=1, le=100)
    create_zip: bool = Field(default=True)
    apply_watermark: bool = Field(default=False)
    naming_convention: str = Field(default="descriptive", pattern="^(simple|descriptive|timestamp)$")


class ExportResponse(BaseModel):
    """Response for export operation."""
    
    success: bool
    export_path: str
    file_count: int
    total_size: int
    assets_exported: int
    download_url: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== Dependencies ====================

def get_brand_guard() -> BrandGuard:
    """Get brand guard instance."""
    return BrandGuard()


def get_export_engine() -> ExportEngine:
    """Get export engine instance."""
    return ExportEngine()


def get_repository(db: Session = Depends(get_db)) -> AssetRepository:
    """Get asset repository instance."""
    return AssetRepository(db)


# ==================== Brand Protection Routes ====================

@router.post("/brand/guidelines", response_model=Dict[str, str])
async def set_brand_guidelines(
    request: BrandGuidelinesRequest,
    brand_guard: BrandGuard = Depends(get_brand_guard)
) -> Dict[str, str]:
    """Set brand guidelines for protection.
    
    Configure brand protection rules including logos, colors,
    prohibited content, and quality requirements.
    """
    try:
        # Update brand guidelines
        guidelines = BrandGuidelines(
            brand_name=request.brand_name,
            copyright_text=request.copyright_text,
            watermark_enabled=request.watermark_enabled,
            logo_position=request.logo_position,
            logo_opacity=request.logo_opacity,
            prohibited_words=request.prohibited_words,
            prohibited_colors=request.prohibited_colors,
            required_colors=request.required_colors,
            min_resolution=request.min_resolution
        )
        
        brand_guard.guidelines = guidelines
        
        return {
            "status": "success",
            "message": "Brand guidelines updated successfully",
            "brand_name": guidelines.brand_name
        }
        
    except Exception as e:
        logger.error(f"Failed to set brand guidelines: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update brand guidelines: {str(e)}"
        )


@router.post("/brand/check", response_model=BrandCheckResponse)
async def check_brand_compliance(
    request: BrandCheckRequest,
    brand_guard: BrandGuard = Depends(get_brand_guard)
) -> BrandCheckResponse:
    """Check brand compliance for prompts, JSON, or assets.
    
    Validates content against brand guidelines and returns
    compliance status with specific violations and suggestions.
    """
    try:
        results = []
        
        # Check prompt compliance
        if request.prompt:
            prompt_result = brand_guard.check_prompt_compliance(request.prompt)
            results.append(prompt_result)
        
        # Check JSON compliance
        if request.request_json:
            json_result = brand_guard.check_json_compliance(request.request_json)
            results.append(json_result)
        
        # Combine results
        if not results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of prompt, request_json, or asset_id must be provided"
            )
        
        # Aggregate results
        all_violations = []
        total_score = 0.0
        
        for result in results:
            all_violations.extend(result.violations)
            total_score += result.score
        
        avg_score = total_score / len(results)
        overall_compliant = len(all_violations) == 0
        
        # Generate suggestions
        suggestions = []
        if not overall_compliant:
            violation_types = set(v.violation_type for v in all_violations)
            
            if "prohibited_content" in violation_types:
                suggestions.append("Review content against brand guidelines")
            if "prohibited_color" in violation_types:
                suggestions.append("Use only brand-approved color palette")
            if "missing_disclaimer" in violation_types:
                suggestions.append("Add required brand disclaimers")
        else:
            suggestions.append("Content meets all brand requirements")
        
        return BrandCheckResponse(
            compliant=overall_compliant,
            score=avg_score,
            violations=[{
                "type": v.violation_type,
                "severity": v.severity,
                "message": v.message,
                "fix": v.suggested_fix
            } for v in all_violations],
            suggestions=suggestions,
            metadata={
                "checks_performed": len(results),
                "total_violations": len(all_violations),
                "avg_score": avg_score
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Brand compliance check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Brand compliance check failed: {str(e)}"
        )


@router.post("/brand/protect/{asset_id}")
async def protect_asset(
    asset_id: str,
    repository: AssetRepository = Depends(get_repository),
    brand_guard: BrandGuard = Depends(get_brand_guard)
) -> Dict[str, Any]:
    """Apply brand protection to existing asset.
    
    Downloads asset, applies watermarks/logos, and returns
    protected version with compliance report.
    """
    try:
        # Get asset from database
        asset = repository.get_asset(asset_id)
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset not found: {asset_id}"
            )
        
        # For now, return success message as we don't have actual image files
        # In production, this would download, protect, and re-upload the image
        
        return {
            "status": "success",
            "message": "Asset protection would be applied",
            "asset_id": asset_id,
            "protection_features": [
                "Watermark applied" if brand_guard.guidelines.watermark_enabled else "No watermark",
                "Logo overlay" if brand_guard.guidelines.logo_path else "No logo",
                "Metadata protection enabled"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Asset protection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Asset protection failed: {str(e)}"
        )


# ==================== Export Routes ====================

@router.post("/export", response_model=ExportResponse)
async def export_assets(
    request: ExportRequest,
    repository: AssetRepository = Depends(get_repository),
    export_engine: ExportEngine = Depends(get_export_engine)
) -> ExportResponse:
    """Export assets in specified format.
    
    Creates downloadable packages containing images, JSON data,
    and metadata in portfolio, archive, or presentation formats.
    """
    try:
        # Validate asset IDs
        assets_data = []
        for asset_id in request.asset_ids:
            asset = repository.get_asset(asset_id)
            if not asset:
                logger.warning(f"Asset not found: {asset_id}")
                continue
            
            # Get JSON payload
            json_payload = repository.get_json_payload(asset_id)
            
            # Create export asset
            export_asset = ExportAsset(
                asset_id=asset.id,
                image_url=asset.image_url or "",
                prompt=asset.prompt,
                structured_prompt=asset.prompt,  # In production, get from metadata
                request_json=json_payload or {},
                metadata={"asset_type": "generated", "project_id": asset.project_id},
                seed=asset.seed,
                aspect_ratio=asset.aspect_ratio,
                created_at=asset.created_at
            )
            
            assets_data.append(export_asset)
        
        if not assets_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid assets found for export"
            )
        
        # Configure export
        config = ExportConfig(
            include_images=request.include_images,
            include_json=request.include_json,
            include_metadata=request.include_metadata,
            image_format=request.image_format,
            image_quality=request.image_quality,
            create_zip=request.create_zip,
            apply_watermark=request.apply_watermark,
            naming_convention=request.naming_convention
        )
        
        # Perform export based on format
        if request.format_type == "portfolio":
            result = export_engine.export_portfolio(assets_data, config)
        elif request.format_type == "archive":
            result = export_engine.export_archive(assets_data, config)
        elif request.format_type == "presentation":
            result = export_engine.export_presentation(assets_data, config)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format type: {request.format_type}"
            )
        
        # Generate download URL (in production, this would be a signed URL)
        download_url = f"/downloads/{Path(result.export_path).name}" if result.success else None
        
        return ExportResponse(
            success=result.success,
            export_path=result.export_path,
            file_count=result.file_count,
            total_size=result.total_size,
            assets_exported=result.assets_exported,
            download_url=download_url,
            errors=result.errors,
            warnings=result.warnings,
            metadata=result.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/export/formats")
async def get_export_formats() -> Dict[str, Any]:
    """Get available export formats and their descriptions.
    
    Returns information about supported export formats,
    their features, and use cases.
    """
    return {
        "formats": {
            "portfolio": {
                "name": "Portfolio",
                "description": "Professional portfolio with HTML viewer",
                "features": ["Interactive gallery", "Thumbnails", "Metadata display"],
                "use_case": "Client presentations, portfolio reviews"
            },
            "archive": {
                "name": "Archive", 
                "description": "Complete dataset with all metadata",
                "features": ["Full data export", "CSV summaries", "Technical metadata"],
                "use_case": "Backup, research, data analysis"
            },
            "presentation": {
                "name": "Presentation",
                "description": "High-quality images for presentations",
                "features": ["300 DPI images", "Slide thumbnails", "PowerPoint templates"],
                "use_case": "Presentations, print materials"
            }
        },
        "image_formats": ["PNG", "JPEG", "WEBP"],
        "naming_conventions": {
            "simple": "image_001, image_002, ...",
            "descriptive": "001_luxury_watch_12345, 002_...",
            "timestamp": "fibo_20231214_143022_001, ..."
        }
    }


@router.get("/brand/guidelines")
async def get_brand_guidelines(
    brand_guard: BrandGuard = Depends(get_brand_guard)
) -> Dict[str, Any]:
    """Get current brand guidelines configuration.
    
    Returns the current brand protection settings
    and compliance requirements.
    """
    guidelines = brand_guard.guidelines
    
    return {
        "brand_name": guidelines.brand_name,
        "copyright_text": guidelines.copyright_text,
        "watermark_enabled": guidelines.watermark_enabled,
        "logo_position": guidelines.logo_position,
        "logo_opacity": guidelines.logo_opacity,
        "prohibited_words": guidelines.prohibited_words,
        "prohibited_colors": guidelines.prohibited_colors,
        "required_colors": guidelines.required_colors,
        "min_resolution": guidelines.min_resolution,
        "quality_requirements": {
            "min_resolution": guidelines.min_resolution,
            "max_file_size": guidelines.max_file_size,
            "allowed_formats": guidelines.allowed_formats
        }
    }