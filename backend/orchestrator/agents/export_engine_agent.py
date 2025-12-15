"""
FIBO Export Engine Agent - Advanced file export orchestration system.

This agent provides comprehensive export capabilities including:
- Real file export from FileStorageManager
- ZIP generation with temporary download URLs
- HTML portfolio creation with professional templates
- Batch export operations with progress tracking
- Automatic cleanup and file management

Author: FIBO Omni-Director Pro
Version: 2.0.0
"""

import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum

from app.services.file_storage import FileStorageManager, StoredFile, get_file_storage
from .file_export_service import FileExportService, ExportFormat, ExportRequest, ExportResult
from .zip_generator import ZipGenerator, ZipConfig, ZipResult
from .portfolio_generator import PortfolioGenerator, PortfolioConfig, PortfolioResult

logger = logging.getLogger(__name__)


class ExportStatus(Enum):
    """Export operation status."""
    PENDING = "pending"
    PREPARING = "preparing"
    EXPORTING = "exporting"
    PACKAGING = "packaging"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportType(Enum):
    """Types of export operations."""
    SINGLE_FILE = "single_file"
    BATCH_IMAGES = "batch_images"
    ZIP_ARCHIVE = "zip_archive"
    HTML_PORTFOLIO = "html_portfolio"
    CUSTOM_PACKAGE = "custom_package"


@dataclass
class ExportOperation:
    """Represents an ongoing export operation."""
    
    operation_id: str
    export_type: ExportType
    status: ExportStatus = ExportStatus.PENDING
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # File information
    file_ids: List[str] = field(default_factory=list)
    total_files: int = 0
    processed_files: int = 0
    
    # Results
    output_path: Optional[str] = None
    download_url: Optional[str] = None
    expiry_time: Optional[datetime] = None
    
    # Error handling
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Metadata
    config: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportAgentConfig:
    """Configuration for the export agent."""
    
    # Storage paths
    export_base_dir: str = "./exports"
    temp_dir: str = "./temp_exports"
    
    # Limits
    max_batch_size: int = 50
    max_concurrent_exports: int = 3
    cleanup_interval_hours: int = 1
    temp_file_expiry_hours: int = 24
    
    # Default formats
    default_image_format: ExportFormat = ExportFormat.PNG
    default_image_quality: int = 95
    
    # Portfolio settings
    enable_portfolios: bool = True
    default_portfolio_template: str = "professional"
    
    # ZIP settings
    compression_level: int = 6
    enable_progress_tracking: bool = True


class ExportEngineAgent:
    """
    Advanced export engine agent for FIBO Omni-Director Pro.
    
    Provides orchestration for all export operations including file exports,
    ZIP generation, portfolio creation, and download management.
    """
    
    def __init__(self, config: Optional[ExportAgentConfig] = None):
        """Initialize the export engine agent.
        
        Args:
            config: Configuration settings for the agent.
        """
        self.config = config or ExportAgentConfig()
        self.storage_manager = get_file_storage()
        
        # Initialize sub-services
        self.file_export_service = FileExportService()
        self.zip_generator = ZipGenerator()
        self.portfolio_generator = PortfolioGenerator()
        
        # Operation tracking
        self.operations: Dict[str, ExportOperation] = {}
        self.active_operations = 0
        
        # Setup directories
        self._setup_directories()
        
        # Background tasks
        self._cleanup_task = None
        self._start_background_tasks()
        
        logger.info("Export Engine Agent initialized")
    
    def _setup_directories(self) -> None:
        """Setup required directories."""
        for path in [self.config.export_base_dir, self.config.temp_dir]:
            Path(path).mkdir(parents=True, exist_ok=True)
    
    def _start_background_tasks(self) -> None:
        """Start background cleanup tasks."""
        if self.config.cleanup_interval_hours > 0:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def export_single_file(
        self,
        file_id: str,
        export_format: ExportFormat = ExportFormat.PNG,
        quality: int = 95,
        custom_filename: Optional[str] = None,
        apply_watermark: bool = False
    ) -> ExportOperation:
        """
        Export a single file with specified format and settings.
        
        Args:
            file_id: ID of the file to export.
            export_format: Desired export format.
            quality: Image quality (1-100).
            custom_filename: Custom filename (optional).
            apply_watermark: Whether to apply watermark.
            
        Returns:
            ExportOperation with operation details.
        """
        operation_id = str(uuid.uuid4())
        
        # Check if file exists
        stored_file = self.storage_manager.get_file_info(file_id)
        if not stored_file:
            return ExportOperation(
                operation_id=operation_id,
                export_type=ExportType.SINGLE_FILE,
                status=ExportStatus.FAILED,
                file_ids=[file_id],
                errors=[f"File not found: {file_id}"]
            )
        
        # Create operation
        operation = ExportOperation(
            operation_id=operation_id,
            export_type=ExportType.SINGLE_FILE,
            status=ExportStatus.PREPARING,
            file_ids=[file_id],
            total_files=1,
            config={
                "format": export_format.value,
                "quality": quality,
                "custom_filename": custom_filename,
                "apply_watermark": apply_watermark
            }
        )
        
        self.operations[operation_id] = operation
        
        try:
            # Perform export
            operation.status = ExportStatus.EXPORTING
            operation.progress = 0.1
            
            export_request = ExportRequest(
                source_path=stored_file.stored_path,
                output_format=export_format,
                quality=quality,
                apply_watermark=apply_watermark,
                custom_filename=custom_filename or stored_file.original_filename
            )
            
            operation.progress = 0.5
            
            export_result = await self.file_export_service.export_file(export_request)
            
            if export_result.success:
                operation.status = ExportStatus.COMPLETED
                operation.progress = 1.0
                operation.output_path = str(export_result.output_path)
                operation.processed_files = 1
                
                # Create temporary download URL
                download_url, expiry = self._create_download_url(export_result.output_path)
                operation.download_url = download_url
                operation.expiry_time = expiry
                
                logger.info(f"Single file export completed: {file_id}")
            else:
                operation.status = ExportStatus.FAILED
                operation.errors.extend(export_result.errors)
                
        except Exception as e:
            operation.status = ExportStatus.FAILED
            operation.errors.append(f"Export failed: {str(e)}")
            logger.error(f"Single file export error: {e}")
        
        operation.updated_at = datetime.utcnow()
        return operation
    
    async def export_batch_images(
        self,
        file_ids: List[str],
        export_format: ExportFormat = ExportFormat.PNG,
        quality: int = 95,
        apply_watermark: bool = False,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> ExportOperation:
        """
        Export multiple images in batch with progress tracking.
        
        Args:
            file_ids: List of file IDs to export.
            export_format: Desired export format.
            quality: Image quality (1-100).
            apply_watermark: Whether to apply watermark.
            progress_callback: Optional progress callback function.
            
        Returns:
            ExportOperation with batch export details.
        """
        operation_id = str(uuid.uuid4())
        
        # Validate batch size
        if len(file_ids) > self.config.max_batch_size:
            return ExportOperation(
                operation_id=operation_id,
                export_type=ExportType.BATCH_IMAGES,
                status=ExportStatus.FAILED,
                file_ids=file_ids,
                errors=[f"Batch size exceeds limit: {len(file_ids)} > {self.config.max_batch_size}"]
            )
        
        # Check concurrent operations
        if self.active_operations >= self.config.max_concurrent_exports:
            return ExportOperation(
                operation_id=operation_id,
                export_type=ExportType.BATCH_IMAGES,
                status=ExportStatus.FAILED,
                file_ids=file_ids,
                errors=["Too many concurrent operations"]
            )
        
        # Create operation
        operation = ExportOperation(
            operation_id=operation_id,
            export_type=ExportType.BATCH_IMAGES,
            status=ExportStatus.PREPARING,
            file_ids=file_ids,
            total_files=len(file_ids),
            config={
                "format": export_format.value,
                "quality": quality,
                "apply_watermark": apply_watermark
            }
        )
        
        self.operations[operation_id] = operation
        self.active_operations += 1
        
        try:
            operation.status = ExportStatus.EXPORTING
            
            # Create batch export directory
            batch_dir = Path(self.config.export_base_dir) / f"batch_{operation_id}"
            batch_dir.mkdir(parents=True, exist_ok=True)
            
            exported_files = []
            failed_files = []
            
            for i, file_id in enumerate(file_ids):
                try:
                    # Update progress
                    progress = (i / len(file_ids)) * 0.8  # Reserve 20% for packaging
                    operation.progress = progress
                    if progress_callback:
                        progress_callback(progress)
                    
                    # Get file info
                    stored_file = self.storage_manager.get_file_info(file_id)
                    if not stored_file:
                        failed_files.append(f"File not found: {file_id}")
                        continue
                    
                    # Export file
                    export_request = ExportRequest(
                        source_path=stored_file.stored_path,
                        output_format=export_format,
                        quality=quality,
                        apply_watermark=apply_watermark,
                        custom_filename=f"{i+1:03d}_{stored_file.original_filename}"
                    )
                    
                    export_result = await self.file_export_service.export_file(
                        export_request, 
                        output_dir=batch_dir
                    )
                    
                    if export_result.success:
                        exported_files.append(export_result.output_path)
                        operation.processed_files += 1
                    else:
                        failed_files.extend(export_result.errors)
                        
                except Exception as e:
                    failed_files.append(f"Error processing {file_id}: {str(e)}")
            
            # Update operation
            if failed_files:
                operation.warnings.extend(failed_files)
            
            if exported_files:
                operation.status = ExportStatus.COMPLETED
                operation.progress = 1.0
                operation.output_path = str(batch_dir)
                
                logger.info(f"Batch export completed: {len(exported_files)}/{len(file_ids)} files")
            else:
                operation.status = ExportStatus.FAILED
                operation.errors.append("No files were exported successfully")
                
        except Exception as e:
            operation.status = ExportStatus.FAILED
            operation.errors.append(f"Batch export failed: {str(e)}")
            logger.error(f"Batch export error: {e}")
        
        finally:
            self.active_operations -= 1
            operation.updated_at = datetime.utcnow()
        
        return operation
    
    async def create_zip_archive(
        self,
        file_ids: List[str],
        archive_name: Optional[str] = None,
        include_metadata: bool = True,
        compression_level: Optional[int] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> ExportOperation:
        """
        Create a ZIP archive containing specified files.
        
        Args:
            file_ids: List of file IDs to include.
            archive_name: Custom archive name.
            include_metadata: Whether to include metadata files.
            compression_level: ZIP compression level (0-9).
            progress_callback: Optional progress callback function.
            
        Returns:
            ExportOperation with ZIP creation details.
        """
        operation_id = str(uuid.uuid4())
        
        # Create operation
        operation = ExportOperation(
            operation_id=operation_id,
            export_type=ExportType.ZIP_ARCHIVE,
            status=ExportStatus.PREPARING,
            file_ids=file_ids,
            total_files=len(file_ids),
            config={
                "archive_name": archive_name,
                "include_metadata": include_metadata,
                "compression_level": compression_level or self.config.compression_level
            }
        )
        
        self.operations[operation_id] = operation
        
        try:
            operation.status = ExportStatus.PACKAGING
            operation.progress = 0.1
            
            # Get stored files
            stored_files = []
            for file_id in file_ids:
                stored_file = self.storage_manager.get_file_info(file_id)
                if stored_file:
                    stored_files.append(stored_file)
                else:
                    operation.warnings.append(f"File not found: {file_id}")
            
            if not stored_files:
                operation.status = ExportStatus.FAILED
                operation.errors.append("No valid files found")
                return operation
            
            operation.progress = 0.3
            
            # Create ZIP configuration
            zip_config = ZipConfig(
                archive_name=archive_name or f"fibo_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                compression_level=compression_level or self.config.compression_level,
                include_metadata=include_metadata,
                output_dir=Path(self.config.export_base_dir)
            )
            
            # Create ZIP
            zip_result = await self.zip_generator.create_archive(
                stored_files, 
                zip_config,
                progress_callback=lambda p: self._update_operation_progress(operation_id, 0.3 + p * 0.6)
            )
            
            if zip_result.success:
                operation.status = ExportStatus.COMPLETED
                operation.progress = 1.0
                operation.output_path = str(zip_result.archive_path)
                operation.processed_files = len(stored_files)
                
                # Create download URL with expiry
                download_url, expiry = self._create_download_url(zip_result.archive_path)
                operation.download_url = download_url
                operation.expiry_time = expiry
                
                operation.metadata = {
                    "archive_size": zip_result.archive_size,
                    "compression_ratio": zip_result.compression_ratio,
                    "file_count": len(stored_files)
                }
                
                logger.info(f"ZIP archive created: {zip_result.archive_path}")
            else:
                operation.status = ExportStatus.FAILED
                operation.errors.extend(zip_result.errors)
                
        except Exception as e:
            operation.status = ExportStatus.FAILED
            operation.errors.append(f"ZIP creation failed: {str(e)}")
            logger.error(f"ZIP creation error: {e}")
        
        operation.updated_at = datetime.utcnow()
        return operation
    
    async def create_html_portfolio(
        self,
        file_ids: List[str],
        portfolio_name: Optional[str] = None,
        template: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> ExportOperation:
        """
        Create an HTML portfolio with specified files.
        
        Args:
            file_ids: List of file IDs to include.
            portfolio_name: Custom portfolio name.
            template: Portfolio template to use.
            custom_config: Custom configuration options.
            progress_callback: Optional progress callback function.
            
        Returns:
            ExportOperation with portfolio creation details.
        """
        operation_id = str(uuid.uuid4())
        
        # Create operation
        operation = ExportOperation(
            operation_id=operation_id,
            export_type=ExportType.HTML_PORTFOLIO,
            status=ExportStatus.PREPARING,
            file_ids=file_ids,
            total_files=len(file_ids),
            config={
                "portfolio_name": portfolio_name,
                "template": template or self.config.default_portfolio_template,
                "custom_config": custom_config or {}
            }
        )
        
        self.operations[operation_id] = operation
        
        try:
            operation.status = ExportStatus.EXPORTING
            operation.progress = 0.1
            
            # Get stored files with metadata
            stored_files = []
            for file_id in file_ids:
                stored_file = self.storage_manager.get_file_info(file_id)
                if stored_file:
                    stored_files.append(stored_file)
                else:
                    operation.warnings.append(f"File not found: {file_id}")
            
            if not stored_files:
                operation.status = ExportStatus.FAILED
                operation.errors.append("No valid files found")
                return operation
            
            operation.progress = 0.3
            
            # Create portfolio configuration
            portfolio_config = PortfolioConfig(
                name=portfolio_name or f"FIBO Portfolio {datetime.now().strftime('%Y-%m-%d')}",
                template=template or self.config.default_portfolio_template,
                output_dir=Path(self.config.export_base_dir),
                **custom_config
            )
            
            # Generate portfolio
            portfolio_result = await self.portfolio_generator.create_portfolio(
                stored_files,
                portfolio_config,
                progress_callback=lambda p: self._update_operation_progress(operation_id, 0.3 + p * 0.6)
            )
            
            if portfolio_result.success:
                operation.status = ExportStatus.COMPLETED
                operation.progress = 1.0
                operation.output_path = str(portfolio_result.portfolio_path)
                operation.processed_files = len(stored_files)
                
                # Create download URL for portfolio ZIP
                if portfolio_result.archive_path:
                    download_url, expiry = self._create_download_url(portfolio_result.archive_path)
                    operation.download_url = download_url
                    operation.expiry_time = expiry
                
                operation.metadata = {
                    "portfolio_url": portfolio_result.portfolio_url,
                    "template_used": portfolio_config.template,
                    "asset_count": len(stored_files)
                }
                
                logger.info(f"HTML portfolio created: {portfolio_result.portfolio_path}")
            else:
                operation.status = ExportStatus.FAILED
                operation.errors.extend(portfolio_result.errors)
                
        except Exception as e:
            operation.status = ExportStatus.FAILED
            operation.errors.append(f"Portfolio creation failed: {str(e)}")
            logger.error(f"Portfolio creation error: {e}")
        
        operation.updated_at = datetime.utcnow()
        return operation
    
    def get_operation_status(self, operation_id: str) -> Optional[ExportOperation]:
        """Get the status of an export operation.
        
        Args:
            operation_id: ID of the operation.
            
        Returns:
            ExportOperation if found, None otherwise.
        """
        return self.operations.get(operation_id)
    
    def list_operations(
        self, 
        status_filter: Optional[ExportStatus] = None,
        limit: int = 50
    ) -> List[ExportOperation]:
        """List export operations with optional filtering.
        
        Args:
            status_filter: Filter by operation status.
            limit: Maximum number of operations to return.
            
        Returns:
            List of ExportOperation objects.
        """
        operations = list(self.operations.values())
        
        if status_filter:
            operations = [op for op in operations if op.status == status_filter]
        
        # Sort by creation time (newest first)
        operations.sort(key=lambda op: op.created_at, reverse=True)
        
        return operations[:limit]
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel an ongoing export operation.
        
        Args:
            operation_id: ID of the operation to cancel.
            
        Returns:
            True if cancelled successfully, False otherwise.
        """
        operation = self.operations.get(operation_id)
        if not operation:
            return False
        
        if operation.status in [ExportStatus.COMPLETED, ExportStatus.FAILED, ExportStatus.CANCELLED]:
            return False
        
        operation.status = ExportStatus.CANCELLED
        operation.updated_at = datetime.utcnow()
        
        logger.info(f"Operation cancelled: {operation_id}")
        return True
    
    def cleanup_expired_files(self) -> int:
        """Clean up expired temporary files and operations.
        
        Returns:
            Number of files cleaned up.
        """
        cleaned_count = 0
        current_time = datetime.utcnow()
        
        # Clean up expired operations
        expired_ops = []
        for op_id, operation in self.operations.items():
            if (operation.expiry_time and 
                current_time > operation.expiry_time and 
                operation.status == ExportStatus.COMPLETED):
                
                # Clean up files
                if operation.output_path:
                    try:
                        output_path = Path(operation.output_path)
                        if output_path.exists():
                            if output_path.is_dir():
                                import shutil
                                shutil.rmtree(output_path)
                            else:
                                output_path.unlink()
                            cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {operation.output_path}: {e}")
                
                expired_ops.append(op_id)
        
        # Remove expired operations
        for op_id in expired_ops:
            del self.operations[op_id]
        
        # Clean up temp directory
        temp_path = Path(self.config.temp_dir)
        if temp_path.exists():
            cutoff_time = current_time - timedelta(hours=self.config.temp_file_expiry_hours)
            
            for file_path in temp_path.glob("*"):
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        if file_path.is_dir():
                            import shutil
                            shutil.rmtree(file_path)
                        else:
                            file_path.unlink()
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired files")
        
        return cleaned_count
    
    def get_export_statistics(self) -> Dict[str, Any]:
        """Get export statistics and metrics.
        
        Returns:
            Dictionary containing export statistics.
        """
        operations = list(self.operations.values())
        
        stats = {
            "total_operations": len(operations),
            "active_operations": self.active_operations,
            "status_breakdown": {},
            "type_breakdown": {},
            "success_rate": 0.0,
            "total_files_exported": 0,
            "average_batch_size": 0.0,
            "recent_operations": len([op for op in operations 
                                    if op.created_at > datetime.utcnow() - timedelta(hours=24)])
        }
        
        if operations:
            # Status breakdown
            for status in ExportStatus:
                count = len([op for op in operations if op.status == status])
                stats["status_breakdown"][status.value] = count
            
            # Type breakdown
            for export_type in ExportType:
                count = len([op for op in operations if op.export_type == export_type])
                stats["type_breakdown"][export_type.value] = count
            
            # Success rate
            completed_ops = [op for op in operations if op.status in [ExportStatus.COMPLETED, ExportStatus.FAILED]]
            if completed_ops:
                successful_ops = [op for op in completed_ops if op.status == ExportStatus.COMPLETED]
                stats["success_rate"] = len(successful_ops) / len(completed_ops)
            
            # Total files exported
            stats["total_files_exported"] = sum(op.processed_files for op in operations)
            
            # Average batch size
            batch_ops = [op for op in operations if op.export_type == ExportType.BATCH_IMAGES]
            if batch_ops:
                stats["average_batch_size"] = sum(op.total_files for op in batch_ops) / len(batch_ops)
        
        return stats
    
    def _create_download_url(self, file_path: Path) -> tuple[str, datetime]:
        """Create a temporary download URL for a file.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            Tuple of (download_url, expiry_time).
        """
        # Generate unique download token
        download_token = str(uuid.uuid4())
        expiry_time = datetime.utcnow() + timedelta(hours=self.config.temp_file_expiry_hours)
        
        # In a real implementation, this would be stored in a database
        # and served by a download endpoint
        download_url = f"/api/downloads/{download_token}"
        
        return download_url, expiry_time
    
    def _update_operation_progress(self, operation_id: str, progress: float) -> None:
        """Update the progress of an operation.
        
        Args:
            operation_id: ID of the operation.
            progress: Progress value (0.0 to 1.0).
        """
        operation = self.operations.get(operation_id)
        if operation:
            operation.progress = min(max(progress, 0.0), 1.0)
            operation.updated_at = datetime.utcnow()
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                self.cleanup_expired_files()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


# Global agent instance
_export_agent: Optional[ExportEngineAgent] = None


def get_export_agent(config: Optional[ExportAgentConfig] = None) -> ExportEngineAgent:
    """Get global export agent instance.
    
    Args:
        config: Optional configuration for the agent.
        
    Returns:
        ExportEngineAgent instance.
    """
    global _export_agent
    if _export_agent is None:
        _export_agent = ExportEngineAgent(config)
    return _export_agent