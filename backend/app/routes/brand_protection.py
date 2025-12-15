"""
Brand Protection API routes for FIBO Omni-Director Pro.
Provides endpoints for watermarking, compliance checking, and brand guidelines.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db, Asset
from app.services.file_storage import get_file_storage
from orchestrator.agents import (
    get_brand_protection_agent,
    get_brand_guideline_manager,
    WatermarkConfig,
    BrandProtectionConfig,
    ColorGuideline
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/brand-protection", tags=["brand-protection"])


class WatermarkConfigRequest(BaseModel):
    """Watermark configuration request."""
    enabled: bool = True
    position: str = Field(default="bottom-right", description="Watermark position")
    opacity: float = Field(default=0.7, ge=0.0, le=1.0, description="Watermark opacity")
    size_percent: float = Field(default=10.0, ge=1.0, le=50.0, description="Size as % of image")
    margin_percent: float = Field(default=5.0, ge=0.0, le=20.0, description="Margin from edges")
    blend_mode: str = Field(default="normal", description="Blend mode")
    quality: int = Field(default=90, ge=1, le=100, description="Output quality")


class BrandProtectionConfigRequest(BaseModel):
    """Brand protection configuration request."""
    watermark: WatermarkConfigRequest = Field(default_factory=WatermarkConfigRequest)
    compliance_enabled: bool = True
    auto_compliance_check: bool = True
    guideline_enforcement: bool = True
    violation_threshold: float = Field(default=0.3, ge=0.0, le=1.0)


class ColorGuidelineRequest(BaseModel):
    """Color guideline request."""
    name: str
    hex_code: str = Field(description="Hex color code (e.g., #FF6B35)")
    usage: str = Field(description="Usage type: primary, secondary, accent, neutral")
    description: str = ""


class BrandGuidelinesRequest(BaseModel):
    """Brand guidelines creation request."""
    brand_name: str
    colors: List[ColorGuidelineRequest]
    logo_path: Optional[str] = None


class AssetProtectionRequest(BaseModel):
    """Asset protection request."""
    asset_ids: List[str]
    project_id: Optional[str] = None
    watermark_config: Optional[WatermarkConfigRequest] = None


@router.get("/status")
async def get_protection_status():
    """Get brand protection system status."""
    agent = get_brand_protection_agent()
    guideline_manager = get_brand_guideline_manager()
    
    stats = agent.get_statistics()
    guidelines = guideline_manager.list_guidelines()
    
    return {
        "status": "active",
        "timestamp": datetime.utcnow().isoformat(),
        "agent_statistics": stats,
        "available_guidelines": len(guidelines),
        "version": "1.0"
    }


@router.post("/configure")
async def configure_protection(config: BrandProtectionConfigRequest):
    """Configure brand protection settings."""
    try:
        agent = get_brand_protection_agent()
        
        # Update watermark configuration
        watermark_dict = config.watermark.dict()
        agent.configure_watermark(**watermark_dict)
        
        # Update compliance configuration
        compliance_dict = {
            "compliance_enabled": config.compliance_enabled,
            "auto_compliance_check": config.auto_compliance_check,
            "guideline_enforcement": config.guideline_enforcement,
            "violation_threshold": config.violation_threshold
        }
        agent.configure_compliance(**compliance_dict)
        
        return {
            "success": True,
            "message": "Brand protection configuration updated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Configuration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Configuration failed: {str(e)}")


@router.post("/protect-asset/{asset_id}")
async def protect_asset(
    asset_id: str,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Apply brand protection to a single asset."""
    try:
        # Verify asset exists
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        agent = get_brand_protection_agent()
        result = await agent.protect_asset(asset_id, project_id)
        
        return {
            "success": True,
            "asset_id": asset_id,
            "protection_report": {
                "watermark_applied": result.watermark_applied,
                "compliance_score": result.compliance_score,
                "violations": result.violations,
                "brand_guidelines_met": result.brand_guidelines_met,
                "recommendations": result.recommendations,
                "processing_time_ms": result.processing_time_ms,
                "metadata": result.metadata
            },
            "timestamp": result.timestamp.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Asset protection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Protection failed: {str(e)}")


@router.post("/protect-assets")
async def protect_assets(
    request: AssetProtectionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Apply brand protection to multiple assets."""
    try:
        # Verify assets exist
        assets = db.query(Asset).filter(Asset.id.in_(request.asset_ids)).all()
        found_ids = {asset.id for asset in assets}
        missing_ids = set(request.asset_ids) - found_ids
        
        if missing_ids:
            raise HTTPException(
                status_code=400, 
                detail=f"Assets not found: {list(missing_ids)}"
            )
        
        agent = get_brand_protection_agent()
        
        # Apply custom watermark config if provided
        if request.watermark_config:
            watermark_dict = request.watermark_config.dict()
            agent.configure_watermark(**watermark_dict)
        
        # Process assets in background for large batches
        if len(request.asset_ids) > 5:
            background_tasks.add_task(
                _background_protect_assets,
                request.asset_ids,
                request.project_id
            )
            
            return {
                "success": True,
                "message": f"Started background protection for {len(request.asset_ids)} assets",
                "asset_count": len(request.asset_ids),
                "processing_mode": "background",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Process immediately for small batches
        results = await agent.batch_protect_assets(request.asset_ids, request.project_id)
        
        successful = len([r for r in results if r.watermark_applied or r.compliance_score > 0])
        
        return {
            "success": True,
            "asset_count": len(request.asset_ids),
            "successful_count": successful,
            "processing_mode": "immediate",
            "results": [
                {
                    "asset_id": result.asset_id,
                    "watermark_applied": result.watermark_applied,
                    "compliance_score": result.compliance_score,
                    "violations": result.violations,
                    "recommendations": result.recommendations,
                    "processing_time_ms": result.processing_time_ms
                }
                for result in results
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch protection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch protection failed: {str(e)}")


async def _background_protect_assets(asset_ids: List[str], project_id: Optional[str] = None):
    """Background task for protecting large batches of assets."""
    try:
        agent = get_brand_protection_agent()
        results = await agent.batch_protect_assets(asset_ids, project_id)
        
        successful = len([r for r in results if r.watermark_applied or r.compliance_score > 0])
        
        logger.info(f"Background protection completed: {successful}/{len(asset_ids)} successful")
        
        # Here you could store results in database or send notifications
        
    except Exception as e:
        logger.error(f"Background protection failed: {e}")


@router.get("/compliance/{asset_id}")
async def check_asset_compliance(
    asset_id: str,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Check compliance for a specific asset."""
    try:
        # Verify asset exists
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        if not asset.file_id:
            raise HTTPException(status_code=400, detail="Asset has no stored file")
        
        # Get stored file
        file_storage = get_file_storage()
        stored_file = file_storage.get_file_info(asset.file_id)
        if not stored_file:
            raise HTTPException(status_code=400, detail="Stored file not found")
        
        # Run compliance check
        from orchestrator.agents.compliance_checker import ComplianceChecker
        compliance_checker = ComplianceChecker()
        
        result = await compliance_checker.check_compliance(
            stored_file.stored_path,
            project_id=project_id
        )
        
        return {
            "asset_id": asset_id,
            "compliance_result": {
                "score": result.score,
                "violations": result.violations,
                "warnings": result.warnings,
                "recommendations": result.recommendations,
                "color_profile": {
                    "brightness": result.color_profile.brightness,
                    "contrast": result.color_profile.contrast,
                    "saturation": result.color_profile.saturation,
                    "temperature": result.color_profile.temperature,
                    "color_distribution": result.color_profile.color_distribution
                } if result.color_profile else None,
                "content_analysis": {
                    "text_detected": result.content_analysis.text_detected,
                    "safety_score": result.content_analysis.safety_score,
                    "quality_score": result.content_analysis.quality_score,
                    "inappropriate_content": result.content_analysis.inappropriate_content
                } if result.content_analysis else None,
                "processing_time_ms": result.processing_time_ms,
                "metadata": result.metadata
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compliance check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Compliance check failed: {str(e)}")


@router.post("/guidelines")
async def create_brand_guidelines(request: BrandGuidelinesRequest):
    """Create new brand guidelines."""
    try:
        guideline_manager = get_brand_guideline_manager()
        
        # Create guidelines
        guidelines = guideline_manager.create_guideline(request.brand_name)
        
        # Update with custom colors if provided
        if request.colors:
            custom_colors = []
            for color_req in request.colors:
                color = ColorGuideline.from_hex(
                    color_req.name,
                    color_req.hex_code,
                    color_req.usage,
                    color_req.description
                )
                custom_colors.append(color.__dict__)
            
            # Get the generated guideline ID
            guidelines_list = guideline_manager.list_guidelines()
            if guidelines_list:
                latest_guideline = guidelines_list[0]  # Most recent
                guideline_id = latest_guideline['id']
                
                success = guideline_manager.update_guidelines(
                    guideline_id, 
                    {"colors": custom_colors}
                )
                
                if not success:
                    logger.warning("Failed to update colors, using defaults")
        
        return {
            "success": True,
            "guideline_id": guideline_id if 'guideline_id' in locals() else "unknown",
            "brand_name": guidelines.brand_name,
            "version": guidelines.version,
            "color_count": len(guidelines.colors),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Guideline creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Guideline creation failed: {str(e)}")


@router.get("/guidelines")
async def list_brand_guidelines():
    """List all available brand guidelines."""
    try:
        guideline_manager = get_brand_guideline_manager()
        guidelines = guideline_manager.list_guidelines()
        
        return {
            "guidelines": guidelines,
            "count": len(guidelines),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Guidelines listing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Guidelines listing failed: {str(e)}")


@router.post("/guidelines/{guideline_id}/assign/{project_id}")
async def assign_guidelines_to_project(guideline_id: str, project_id: str):
    """Assign brand guidelines to a project."""
    try:
        guideline_manager = get_brand_guideline_manager()
        
        success = guideline_manager.assign_to_project(project_id, guideline_id)
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail="Failed to assign guidelines - check if guideline exists"
            )
        
        return {
            "success": True,
            "message": f"Guidelines {guideline_id} assigned to project {project_id}",
            "guideline_id": guideline_id,
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Guideline assignment failed: {e}")
        raise HTTPException(status_code=500, detail=f"Assignment failed: {str(e)}")


@router.get("/project/{project_id}/validate")
async def validate_project_branding(project_id: str, db: Session = Depends(get_db)):
    """Validate all assets in a project against brand guidelines."""
    try:
        # Verify project has assets
        assets = db.query(Asset).filter(Asset.project_id == project_id).all()
        if not assets:
            raise HTTPException(status_code=404, detail="No assets found in project")
        
        agent = get_brand_protection_agent()
        summary = await agent.validate_project_branding(project_id)
        
        return {
            "project_id": project_id,
            "validation_summary": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Project validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/statistics")
async def get_protection_statistics():
    """Get comprehensive brand protection statistics."""
    try:
        agent = get_brand_protection_agent()
        guideline_manager = get_brand_guideline_manager()
        file_storage = get_file_storage()
        
        agent_stats = agent.get_statistics()
        guidelines = guideline_manager.list_guidelines()
        storage_stats = file_storage.get_storage_stats()
        
        return {
            "agent_statistics": agent_stats,
            "guidelines": {
                "total_count": len(guidelines),
                "recent_guidelines": guidelines[:5]  # 5 most recent
            },
            "storage": {
                "total_size_mb": storage_stats.get('total_size_mb', 0),
                "image_count": storage_stats.get('images', {}).get('count', 0)
            },
            "system_health": {
                "services_active": True,
                "last_check": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Statistics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Statistics failed: {str(e)}")