"""
FIBO Omni-Director Pro - Orchestrator Agents Package

This package contains specialized agent implementations for the FIBO platform:

- Brand Protection Agent: Content compliance and brand safety
- Brand Guidelines Agent: Brand consistency enforcement  
- Compliance Checker: Automated compliance validation
- Watermarking Service: Asset protection and attribution
- Export Engine Agent: Advanced file export and portfolio creation

The Export Engine Agent provides comprehensive export capabilities including:
- Real file export with format conversion
- ZIP archive generation with download management
- Professional HTML portfolio creation
- Batch processing with progress tracking
- Automatic cleanup and file management

Author: FIBO Omni-Director Pro
Version: 2.0.0
"""

from .brand_protection_agent import BrandProtectionAgent
from .brand_guidelines import BrandGuidelineManager
from .compliance_checker import ComplianceChecker
from .watermarking_service import WatermarkingService
from .export_engine_agent import (
    ExportEngineAgent, 
    ExportAgentConfig, 
    ExportOperation,
    ExportStatus,
    ExportType,
    get_export_agent
)
from .file_export_service import (
    FileExportService,
    ExportFormat,
    ExportRequest,
    ExportResult,
    WatermarkConfig,
    ResizeConfig
)
from .zip_generator import (
    ZipGenerator,
    ZipConfig,
    ZipResult,
    CompressionMethod,
    ArchiveStructure
)
from .portfolio_generator import (
    PortfolioGenerator,
    PortfolioConfig,
    PortfolioResult,
    PortfolioTheme,
    LayoutStyle,
    BrandingConfig
)

__all__ = [
    # Core agents
    "BrandProtectionAgent",
    "BrandGuidelineManager", 
    "ComplianceChecker",
    "WatermarkingService",
    
    # Export Engine components
    "ExportEngineAgent",
    "ExportAgentConfig",
    "ExportOperation", 
    "ExportStatus",
    "ExportType",
    "get_export_agent",
    
    # File Export Service
    "FileExportService",
    "ExportFormat",
    "ExportRequest",
    "ExportResult", 
    "WatermarkConfig",
    "ResizeConfig",
    
    # ZIP Generator
    "ZipGenerator",
    "ZipConfig",
    "ZipResult",
    "CompressionMethod",
    "ArchiveStructure",
    
    # Portfolio Generator
    "PortfolioGenerator",
    "PortfolioConfig", 
    "PortfolioResult",
    "PortfolioTheme",
    "LayoutStyle",
    "BrandingConfig",
]

# Version information
__version__ = "2.0.0"
__author__ = "FIBO Omni-Director Pro"