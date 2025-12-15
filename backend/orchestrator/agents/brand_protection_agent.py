"""
Brand Protection Agent for FIBO Omni-Director Pro.
Manages image watermarking, content filtering, and brand compliance systems.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from PIL import Image
import uuid

from .watermarking_service import WatermarkingService
from .compliance_checker import ComplianceChecker
from .brand_guidelines import BrandGuidelineManager
from app.services.file_storage import get_file_storage, StoredFile
from app.models.database import SessionLocal, Asset

logger = logging.getLogger(__name__)


@dataclass
class ProtectionReport:
    """Brand protection analysis report."""
    asset_id: str
    timestamp: datetime
    watermark_applied: bool = False
    compliance_score: float = 0.0
    violations: List[str] = field(default_factory=list)
    brand_guidelines_met: bool = False
    recommendations: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WatermarkConfig:
    """Configuration for watermarking operations."""
    enabled: bool = True
    logo_path: Optional[str] = None
    position: str = "bottom-right"  # corner, center, custom
    opacity: float = 0.7
    size_percent: float = 10.0  # percentage of image size
    margin_percent: float = 5.0  # margin from edges
    blend_mode: str = "normal"  # normal, multiply, overlay
    quality: int = 90


@dataclass
class BrandProtectionConfig:
    """Configuration for brand protection operations."""
    watermark: WatermarkConfig = field(default_factory=WatermarkConfig)
    compliance_enabled: bool = True
    auto_compliance_check: bool = True
    guideline_enforcement: bool = True
    violation_threshold: float = 0.3  # Above this score = violation
    processing_timeout_seconds: int = 30


class BrandProtectionAgent:
    """Advanced brand protection agent with real implementation."""
    
    def __init__(self, config: Optional[BrandProtectionConfig] = None):
        """Initialize the brand protection agent.
        
        Args:
            config: Brand protection configuration.
        """
        self.config = config or BrandProtectionConfig()
        self.file_storage = get_file_storage()
        
        # Initialize services
        self.watermarking_service = WatermarkingService()
        self.compliance_checker = ComplianceChecker()
        self.guideline_manager = BrandGuidelineManager()
        
        # Performance tracking
        self.processed_assets = 0
        self.total_processing_time = 0.0
        self.violations_detected = 0
        self.watermarks_applied = 0
        
        logger.info("🛡️ Brand Protection Agent initialized")
    
    async def protect_asset(self, asset_id: str, project_id: Optional[str] = None) -> ProtectionReport:
        """Apply comprehensive brand protection to an asset.
        
        Args:
            asset_id: Asset ID to protect.
            project_id: Optional project ID for context.
            
        Returns:
            ProtectionReport with results.
        """
        start_time = datetime.utcnow()
        report = ProtectionReport(
            asset_id=asset_id,
            timestamp=start_time
        )
        
        try:
            # Get asset from database
            with SessionLocal() as db:
                asset = db.query(Asset).filter(Asset.id == asset_id).first()
                if not asset:
                    raise ValueError(f"Asset {asset_id} not found")
                
                # Get stored file info
                if not asset.file_id:
                    raise ValueError(f"Asset {asset_id} has no stored file")
                
                stored_file = self.file_storage.get_file_info(asset.file_id)
                if not stored_file:
                    raise ValueError(f"Stored file {asset.file_id} not found")
                
                logger.info(f"🔍 Starting brand protection for asset {asset_id}")
                
                # Step 1: Brand compliance check
                if self.config.compliance_enabled:
                    compliance_result = await self.compliance_checker.check_compliance(
                        stored_file.stored_path,
                        project_id=project_id
                    )
                    report.compliance_score = compliance_result.score
                    report.violations = compliance_result.violations
                    report.brand_guidelines_met = compliance_result.score > (1 - self.config.violation_threshold)
                    
                    if compliance_result.violations:
                        self.violations_detected += 1
                        logger.warning(f"⚠️ Compliance violations detected for {asset_id}: {compliance_result.violations}")
                    
                    # Add compliance recommendations
                    if compliance_result.recommendations:
                        report.recommendations.extend(compliance_result.recommendations)
                
                # Step 2: Apply watermark if configured
                if self.config.watermark.enabled:
                    watermark_result = await self.watermarking_service.apply_watermark(
                        input_path=stored_file.stored_path,
                        output_path=stored_file.stored_path,  # In-place watermarking
                        config=self.config.watermark
                    )
                    
                    if watermark_result.success:
                        report.watermark_applied = True
                        self.watermarks_applied += 1
                        logger.info(f"✅ Watermark applied to {asset_id}")
                        
                        # Update file info in database if needed
                        if watermark_result.file_size_changed:
                            asset.file_size = watermark_result.new_file_size
                            db.commit()
                    else:
                        logger.error(f"❌ Failed to apply watermark to {asset_id}: {watermark_result.error}")
                        report.recommendations.append("Watermark application failed - check file format compatibility")
                
                # Step 3: Brand guideline enforcement
                if self.config.guideline_enforcement:
                    guideline_result = await self.guideline_manager.validate_asset(
                        stored_file.stored_path,
                        project_id=project_id
                    )
                    
                    # Merge guideline results with compliance
                    if not guideline_result.compliant:
                        report.violations.extend(guideline_result.violations)
                        report.brand_guidelines_met = False
                        report.recommendations.extend(guideline_result.recommendations)
                
                # Calculate processing time
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds() * 1000
                report.processing_time_ms = processing_time
                
                # Update statistics
                self.processed_assets += 1
                self.total_processing_time += processing_time
                
                # Add metadata
                report.metadata = {
                    "file_size": stored_file.file_size,
                    "content_type": stored_file.content_type,
                    "original_filename": stored_file.original_filename,
                    "processing_version": "1.0",
                    "agent_config": {
                        "watermark_enabled": self.config.watermark.enabled,
                        "compliance_enabled": self.config.compliance_enabled,
                        "guideline_enforcement": self.config.guideline_enforcement
                    }
                }
                
                logger.info(f"🛡️ Brand protection completed for {asset_id} in {processing_time:.1f}ms")
                return report
                
        except Exception as e:
            logger.error(f"❌ Brand protection failed for {asset_id}: {e}")
            report.recommendations.append(f"Protection failed: {str(e)}")
            return report
    
    async def batch_protect_assets(self, asset_ids: List[str], project_id: Optional[str] = None) -> List[ProtectionReport]:
        """Apply brand protection to multiple assets in batch.
        
        Args:
            asset_ids: List of asset IDs to protect.
            project_id: Optional project ID for context.
            
        Returns:
            List of ProtectionReport results.
        """
        logger.info(f"🔄 Starting batch protection for {len(asset_ids)} assets")
        
        # Process assets in parallel with limited concurrency
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent operations
        
        async def protect_with_semaphore(asset_id: str) -> ProtectionReport:
            async with semaphore:
                return await self.protect_asset(asset_id, project_id)
        
        # Create tasks for all assets
        tasks = [protect_with_semaphore(asset_id) for asset_id in asset_ids]
        
        # Execute with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.processing_timeout_seconds * len(asset_ids)
            )
            
            # Process results and handle exceptions
            reports = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Create error report
                    error_report = ProtectionReport(
                        asset_id=asset_ids[i],
                        timestamp=datetime.utcnow()
                    )
                    error_report.recommendations.append(f"Processing failed: {str(result)}")
                    reports.append(error_report)
                    logger.error(f"❌ Failed to process asset {asset_ids[i]}: {result}")
                else:
                    reports.append(result)
            
            # Log batch summary
            successful = len([r for r in reports if r.watermark_applied or r.compliance_score > 0])
            logger.info(f"✅ Batch protection completed: {successful}/{len(asset_ids)} successful")
            
            return reports
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ Batch protection timed out after {self.config.processing_timeout_seconds * len(asset_ids)}s")
            # Return partial results
            return [
                ProtectionReport(
                    asset_id=asset_id,
                    timestamp=datetime.utcnow(),
                    recommendations=["Processing timed out"]
                )
                for asset_id in asset_ids
            ]
    
    def configure_watermark(self, **kwargs) -> None:
        """Update watermark configuration.
        
        Args:
            **kwargs: Watermark configuration parameters.
        """
        for key, value in kwargs.items():
            if hasattr(self.config.watermark, key):
                setattr(self.config.watermark, key, value)
                logger.info(f"🔧 Updated watermark config: {key} = {value}")
            else:
                logger.warning(f"⚠️ Unknown watermark config key: {key}")
    
    def configure_compliance(self, **kwargs) -> None:
        """Update compliance configuration.
        
        Args:
            **kwargs: Compliance configuration parameters.
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"🔧 Updated compliance config: {key} = {value}")
            else:
                logger.warning(f"⚠️ Unknown compliance config key: {key}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get agent performance statistics.
        
        Returns:
            Dictionary with performance stats.
        """
        avg_processing_time = (
            self.total_processing_time / self.processed_assets 
            if self.processed_assets > 0 else 0
        )
        
        return {
            "processed_assets": self.processed_assets,
            "watermarks_applied": self.watermarks_applied,
            "violations_detected": self.violations_detected,
            "average_processing_time_ms": round(avg_processing_time, 2),
            "total_processing_time_ms": round(self.total_processing_time, 2),
            "watermark_success_rate": (
                self.watermarks_applied / self.processed_assets 
                if self.processed_assets > 0 else 0
            ),
            "violation_rate": (
                self.violations_detected / self.processed_assets 
                if self.processed_assets > 0 else 0
            ),
            "config": {
                "watermark_enabled": self.config.watermark.enabled,
                "compliance_enabled": self.config.compliance_enabled,
                "guideline_enforcement": self.config.guideline_enforcement
            }
        }
    
    async def validate_project_branding(self, project_id: str) -> Dict[str, Any]:
        """Validate all assets in a project against brand guidelines.
        
        Args:
            project_id: Project ID to validate.
            
        Returns:
            Validation summary with recommendations.
        """
        logger.info(f"🔍 Starting project branding validation for {project_id}")
        
        # Get all assets for the project
        with SessionLocal() as db:
            assets = db.query(Asset).filter(Asset.project_id == project_id).all()
            
            if not assets:
                return {
                    "project_id": project_id,
                    "status": "no_assets",
                    "message": "No assets found in project"
                }
            
            # Batch protect all assets
            asset_ids = [asset.id for asset in assets]
            reports = await self.batch_protect_assets(asset_ids, project_id)
            
            # Analyze results
            total_assets = len(reports)
            compliant_assets = len([r for r in reports if r.brand_guidelines_met])
            watermarked_assets = len([r for r in reports if r.watermark_applied])
            violations = set()
            
            for report in reports:
                violations.update(report.violations)
            
            # Generate project summary
            compliance_score = compliant_assets / total_assets if total_assets > 0 else 0
            watermark_coverage = watermarked_assets / total_assets if total_assets > 0 else 0
            
            summary = {
                "project_id": project_id,
                "timestamp": datetime.utcnow().isoformat(),
                "total_assets": total_assets,
                "compliant_assets": compliant_assets,
                "watermarked_assets": watermarked_assets,
                "compliance_score": round(compliance_score, 2),
                "watermark_coverage": round(watermark_coverage, 2),
                "unique_violations": list(violations),
                "recommendations": [],
                "status": "completed"
            }
            
            # Add recommendations based on analysis
            if compliance_score < 0.8:
                summary["recommendations"].append("Consider reviewing brand guidelines - compliance below 80%")
            
            if watermark_coverage < 1.0 and self.config.watermark.enabled:
                summary["recommendations"].append("Some assets lack watermarks - check processing errors")
            
            if violations:
                summary["recommendations"].append(f"Address common violations: {', '.join(list(violations)[:3])}")
            
            logger.info(f"✅ Project validation completed: {compliance_score:.1%} compliance, {watermark_coverage:.1%} watermarked")
            return summary


# Global agent instance
_brand_protection_agent: Optional[BrandProtectionAgent] = None


def get_brand_protection_agent() -> BrandProtectionAgent:
    """Get global brand protection agent instance.
    
    Returns:
        BrandProtectionAgent instance.
    """
    global _brand_protection_agent
    if _brand_protection_agent is None:
        _brand_protection_agent = BrandProtectionAgent()
    return _brand_protection_agent