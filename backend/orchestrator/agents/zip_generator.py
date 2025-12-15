"""
FIBO ZIP Generator Service - ZIP creation and download management.

This service handles the creation of ZIP archives containing exported files,
manages temporary download URLs with expiration, and provides progress tracking
for large archive operations.

Author: FIBO Omni-Director Pro
Version: 2.0.0
"""

import logging
import asyncio
import zipfile
import json
import csv
import hashlib
import uuid
import io
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from app.services.file_storage import StoredFile

logger = logging.getLogger(__name__)


class CompressionMethod(Enum):
    """ZIP compression methods."""
    STORED = zipfile.ZIP_STORED      # No compression
    DEFLATED = zipfile.ZIP_DEFLATED  # Standard compression
    BZIP2 = zipfile.ZIP_BZIP2       # BZIP2 compression
    LZMA = zipfile.ZIP_LZMA         # LZMA compression


class ArchiveStructure(Enum):
    """Archive organization structures."""
    FLAT = "flat"                    # All files in root
    ORGANIZED = "organized"          # Organized by type/date
    BY_DATE = "by_date"             # Organized by creation date
    BY_TYPE = "by_type"             # Organized by file type
    CUSTOM = "custom"               # Custom structure


@dataclass
class ZipConfig:
    """Configuration for ZIP creation."""
    
    archive_name: str
    compression_method: CompressionMethod = CompressionMethod.DEFLATED
    compression_level: int = 6  # 0-9, higher = better compression, slower
    output_dir: Path = Path("./exports")
    
    # Archive structure
    structure: ArchiveStructure = ArchiveStructure.ORGANIZED
    create_manifest: bool = True
    include_metadata: bool = True
    include_thumbnails: bool = True
    
    # Metadata options
    include_readme: bool = True
    include_csv_index: bool = True
    include_json_manifest: bool = True
    
    # Size limits
    max_archive_size_mb: int = 1000  # Maximum archive size
    max_file_count: int = 1000       # Maximum files per archive
    
    # Custom structure (used when structure = CUSTOM)
    custom_structure: Optional[Dict[str, str]] = None


@dataclass
class ZipProgress:
    """Progress information for ZIP creation."""
    
    current_file: int = 0
    total_files: int = 0
    current_size: int = 0
    estimated_total_size: int = 0
    current_filename: str = ""
    stage: str = "preparing"  # preparing, adding_files, compressing, finalizing
    
    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.current_file / self.total_files) * 100.0


@dataclass
class ZipResult:
    """Result of ZIP creation operation."""
    
    success: bool
    archive_path: Optional[Path] = None
    archive_size: int = 0
    file_count: int = 0
    compression_ratio: float = 0.0
    creation_time: float = 0.0
    
    # Download management
    download_token: Optional[str] = None
    download_url: Optional[str] = None
    expiry_time: Optional[datetime] = None
    
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ZipGenerator:
    """
    Service for creating ZIP archives with advanced features.
    
    Features:
    - Multiple compression methods and levels
    - Organized archive structures
    - Progress tracking for large archives
    - Metadata and manifest generation
    - Temporary download URLs with expiration
    - Size and file count limits
    - Automatic cleanup
    """
    
    def __init__(self):
        """Initialize the ZIP generator service."""
        self.active_operations: Dict[str, ZipProgress] = {}
        self.download_tokens: Dict[str, Dict[str, Any]] = {}
        
        logger.info("ZIP Generator Service initialized")
    
    async def create_archive(
        self,
        files: List[StoredFile],
        config: ZipConfig,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> ZipResult:
        """
        Create a ZIP archive containing the specified files.
        
        Args:
            files: List of StoredFile objects to include.
            config: ZIP creation configuration.
            progress_callback: Optional progress callback function.
            
        Returns:
            ZipResult with creation details.
        """
        operation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Initialize progress tracking
        progress = ZipProgress(
            total_files=len(files),
            stage="preparing"
        )
        self.active_operations[operation_id] = progress
        
        try:
            # Validate inputs
            validation_result = self._validate_inputs(files, config)
            if not validation_result["valid"]:
                return ZipResult(
                    success=False,
                    errors=validation_result["errors"]
                )
            
            # Prepare output directory and file path
            config.output_dir.mkdir(parents=True, exist_ok=True)
            archive_name = config.archive_name
            if not archive_name.endswith('.zip'):
                archive_name += '.zip'
            
            archive_path = config.output_dir / archive_name
            
            # Estimate total size
            estimated_size = sum(f.file_size for f in files if f.stored_path.exists())
            progress.estimated_total_size = estimated_size
            
            if progress_callback:
                progress_callback(0.05)
            
            # Create archive structure plan
            structure_plan = self._create_structure_plan(files, config)
            progress.stage = "adding_files"
            
            if progress_callback:
                progress_callback(0.1)
            
            # Create ZIP archive
            total_uncompressed = 0
            compression_method = config.compression_method.value
            
            with zipfile.ZipFile(
                archive_path, 
                'w', 
                compression=compression_method,
                compresslevel=config.compression_level
            ) as zipf:
                
                # Add files according to structure plan
                for i, file_entry in enumerate(structure_plan):
                    stored_file = file_entry["file"]
                    archive_path_in_zip = file_entry["archive_path"]
                    
                    progress.current_file = i + 1
                    progress.current_filename = stored_file.original_filename
                    
                    try:
                        if stored_file.stored_path.exists():
                            # Add file to archive
                            zipf.write(stored_file.stored_path, archive_path_in_zip)
                            total_uncompressed += stored_file.file_size
                            progress.current_size += stored_file.file_size
                            
                            logger.debug(f"Added to archive: {archive_path_in_zip}")
                        else:
                            logger.warning(f"File not found: {stored_file.stored_path}")
                            
                    except Exception as e:
                        logger.error(f"Error adding file {stored_file.file_id}: {e}")
                        continue
                    
                    # Update progress
                    if progress_callback:
                        file_progress = 0.1 + (i / len(files)) * 0.7
                        progress_callback(file_progress)
                
                progress.stage = "adding_metadata"
                
                # Add metadata files if requested
                if config.include_metadata:
                    await self._add_metadata_files(zipf, files, config)
                
                if progress_callback:
                    progress_callback(0.85)
                
                progress.stage = "finalizing"
            
            # Calculate final statistics
            creation_time = (datetime.utcnow() - start_time).total_seconds()
            archive_size = archive_path.stat().st_size
            compression_ratio = archive_size / total_uncompressed if total_uncompressed > 0 else 1.0
            
            # Generate download token and URL
            download_token = self._generate_download_token()
            download_url = f"/api/downloads/zip/{download_token}"
            expiry_time = datetime.utcnow() + timedelta(hours=24)
            
            # Store download token info
            self.download_tokens[download_token] = {
                "archive_path": archive_path,
                "expiry_time": expiry_time,
                "archive_name": archive_name,
                "file_count": len(files),
                "created_at": datetime.utcnow()
            }
            
            if progress_callback:
                progress_callback(1.0)
            
            result = ZipResult(
                success=True,
                archive_path=archive_path,
                archive_size=archive_size,
                file_count=len(files),
                compression_ratio=compression_ratio,
                creation_time=creation_time,
                download_token=download_token,
                download_url=download_url,
                expiry_time=expiry_time,
                metadata={
                    "compression_method": config.compression_method.name,
                    "compression_level": config.compression_level,
                    "structure": config.structure.value,
                    "total_uncompressed_size": total_uncompressed
                }
            )
            
            logger.info(
                f"ZIP archive created: {archive_path} "
                f"({len(files)} files, {archive_size:,} bytes, "
                f"{compression_ratio:.2%} compression)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"ZIP creation failed: {e}")
            return ZipResult(
                success=False,
                errors=[f"ZIP creation failed: {str(e)}"],
                creation_time=(datetime.utcnow() - start_time).total_seconds()
            )
        
        finally:
            # Clean up progress tracking
            if operation_id in self.active_operations:
                del self.active_operations[operation_id]
    
    async def create_multi_volume_archive(
        self,
        files: List[StoredFile],
        config: ZipConfig,
        volume_size_mb: int = 100,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> List[ZipResult]:
        """
        Create multiple ZIP volumes if files exceed size limit.
        
        Args:
            files: List of StoredFile objects to include.
            config: ZIP creation configuration.
            volume_size_mb: Maximum size per volume in MB.
            progress_callback: Optional progress callback function.
            
        Returns:
            List of ZipResult objects for each volume.
        """
        volume_size_bytes = volume_size_mb * 1024 * 1024
        
        # Group files by estimated volume
        volumes = []
        current_volume = []
        current_size = 0
        
        for file in files:
            file_size = file.file_size
            
            if current_size + file_size > volume_size_bytes and current_volume:
                volumes.append(current_volume)
                current_volume = [file]
                current_size = file_size
            else:
                current_volume.append(file)
                current_size += file_size
        
        if current_volume:
            volumes.append(current_volume)
        
        # Create each volume
        results = []
        for i, volume_files in enumerate(volumes):
            volume_config = ZipConfig(
                archive_name=f"{config.archive_name}_vol{i+1:02d}",
                compression_method=config.compression_method,
                compression_level=config.compression_level,
                output_dir=config.output_dir,
                structure=config.structure,
                include_metadata=config.include_metadata and i == 0,  # Only first volume gets metadata
                include_readme=config.include_readme and i == 0
            )
            
            volume_progress = lambda p: progress_callback(
                (i + p) / len(volumes)
            ) if progress_callback else None
            
            result = await self.create_archive(volume_files, volume_config, volume_progress)
            results.append(result)
        
        logger.info(f"Multi-volume archive created: {len(volumes)} volumes")
        return results
    
    def get_download_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get download information for a token.
        
        Args:
            token: Download token.
            
        Returns:
            Download info dict or None if not found/expired.
        """
        if token not in self.download_tokens:
            return None
        
        info = self.download_tokens[token]
        
        # Check expiry
        if datetime.utcnow() > info["expiry_time"]:
            del self.download_tokens[token]
            return None
        
        return info
    
    def cleanup_expired_downloads(self) -> int:
        """Clean up expired download tokens and files.
        
        Returns:
            Number of items cleaned up.
        """
        current_time = datetime.utcnow()
        expired_tokens = []
        
        for token, info in self.download_tokens.items():
            if current_time > info["expiry_time"]:
                expired_tokens.append(token)
                
                # Clean up file if it exists
                try:
                    archive_path = Path(info["archive_path"])
                    if archive_path.exists():
                        archive_path.unlink()
                        logger.debug(f"Cleaned up expired archive: {archive_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup archive: {e}")
        
        # Remove expired tokens
        for token in expired_tokens:
            del self.download_tokens[token]
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired download tokens")
        
        return len(expired_tokens)
    
    def get_active_operations(self) -> Dict[str, ZipProgress]:
        """Get currently active ZIP operations.
        
        Returns:
            Dictionary of operation ID -> ZipProgress.
        """
        return self.active_operations.copy()
    
    def _validate_inputs(self, files: List[StoredFile], config: ZipConfig) -> Dict[str, Any]:
        """Validate inputs for ZIP creation.
        
        Args:
            files: List of files to archive.
            config: ZIP configuration.
            
        Returns:
            Validation result dictionary.
        """
        errors = []
        
        # Check file count
        if len(files) == 0:
            errors.append("No files provided for archiving")
        elif len(files) > config.max_file_count:
            errors.append(f"Too many files: {len(files)} > {config.max_file_count}")
        
        # Check estimated size
        total_size = sum(f.file_size for f in files if f.stored_path.exists())
        max_size_bytes = config.max_archive_size_mb * 1024 * 1024
        
        if total_size > max_size_bytes:
            errors.append(f"Archive too large: {total_size:,} bytes > {max_size_bytes:,} bytes")
        
        # Check file existence
        missing_files = [f for f in files if not f.stored_path.exists()]
        if missing_files:
            errors.append(f"{len(missing_files)} files not found on disk")
        
        # Check output directory
        if not config.output_dir.parent.exists():
            errors.append(f"Output directory parent does not exist: {config.output_dir.parent}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": []
        }
    
    def _create_structure_plan(self, files: List[StoredFile], config: ZipConfig) -> List[Dict[str, Any]]:
        """Create a plan for organizing files in the archive.
        
        Args:
            files: List of files to organize.
            config: ZIP configuration.
            
        Returns:
            List of file placement plans.
        """
        plan = []
        
        for i, file in enumerate(files):
            if config.structure == ArchiveStructure.FLAT:
                archive_path = file.original_filename
                
            elif config.structure == ArchiveStructure.ORGANIZED:
                # Group by type and add index
                file_ext = Path(file.original_filename).suffix.lower()
                if file_ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                    folder = "images"
                elif file_ext in ['.json']:
                    folder = "metadata"
                else:
                    folder = "files"
                
                archive_path = f"{folder}/{i+1:03d}_{file.original_filename}"
                
            elif config.structure == ArchiveStructure.BY_DATE:
                date_folder = file.created_at.strftime("%Y-%m-%d")
                archive_path = f"{date_folder}/{file.original_filename}"
                
            elif config.structure == ArchiveStructure.BY_TYPE:
                file_ext = Path(file.original_filename).suffix.lower()
                type_folder = file_ext[1:] if file_ext else "unknown"
                archive_path = f"{type_folder}/{file.original_filename}"
                
            elif config.structure == ArchiveStructure.CUSTOM and config.custom_structure:
                # Use custom structure mapping
                archive_path = config.custom_structure.get(
                    file.file_id, 
                    f"uncategorized/{file.original_filename}"
                )
                
            else:
                # Default to organized structure
                archive_path = f"files/{i+1:03d}_{file.original_filename}"
            
            # Ensure unique names
            base_path = archive_path
            counter = 1
            while any(entry["archive_path"] == archive_path for entry in plan):
                name_parts = Path(base_path).name.rsplit('.', 1)
                if len(name_parts) == 2:
                    new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                else:
                    new_name = f"{base_path}_{counter}"
                
                archive_path = str(Path(base_path).parent / new_name)
                counter += 1
            
            plan.append({
                "file": file,
                "archive_path": archive_path,
                "folder": str(Path(archive_path).parent) if "/" in archive_path else ""
            })
        
        return plan
    
    async def _add_metadata_files(self, zipf: zipfile.ZipFile, files: List[StoredFile], config: ZipConfig) -> None:
        """Add metadata files to the archive.
        
        Args:
            zipf: Open ZipFile object.
            files: List of files being archived.
            config: ZIP configuration.
        """
        try:
            # Create README
            if config.include_readme:
                readme_content = self._generate_readme(files, config)
                zipf.writestr("README.md", readme_content)
            
            # Create manifest JSON
            if config.include_json_manifest:
                manifest = self._generate_manifest(files, config)
                zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
            
            # Create CSV index
            if config.include_csv_index:
                csv_content = self._generate_csv_index(files)
                zipf.writestr("file_index.csv", csv_content)
            
        except Exception as e:
            logger.warning(f"Failed to add metadata files: {e}")
    
    def _generate_readme(self, files: List[StoredFile], config: ZipConfig) -> str:
        """Generate README content for the archive.
        
        Args:
            files: List of files in archive.
            config: ZIP configuration.
            
        Returns:
            README content string.
        """
        total_size = sum(f.file_size for f in files)
        creation_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        readme = f"""# FIBO Export Archive: {config.archive_name}

## Archive Information

- **Created:** {creation_date} UTC
- **Files:** {len(files)}
- **Total Size:** {total_size:,} bytes ({total_size / 1024 / 1024:.1f} MB)
- **Structure:** {config.structure.value}
- **Compression:** {config.compression_method.name}

## Contents

This archive contains {len(files)} files exported from FIBO Omni-Director Pro.

### File Organization

"""
        
        if config.structure == ArchiveStructure.ORGANIZED:
            readme += """- `images/` - Image files (PNG, JPEG, WebP, etc.)
- `metadata/` - Metadata and configuration files
- `files/` - Other file types
"""
        elif config.structure == ArchiveStructure.BY_DATE:
            readme += "- Files are organized by creation date in YYYY-MM-DD folders\n"
        elif config.structure == ArchiveStructure.BY_TYPE:
            readme += "- Files are organized by file type/extension\n"
        else:
            readme += "- Files are stored in flat structure\n"
        
        readme += """
### Metadata Files

- `manifest.json` - Complete archive manifest with file details
- `file_index.csv` - Tabular index of all files
- `README.md` - This documentation file

## Usage

1. Extract the archive to your desired location
2. Review the manifest.json for detailed file information
3. Use file_index.csv for bulk operations or analysis

## Generated By

FIBO Omni-Director Pro - Advanced File Export System
https://fibo.ai

---
*This archive was generated automatically. Do not modify the metadata files.*
"""
        
        return readme
    
    def _generate_manifest(self, files: List[StoredFile], config: ZipConfig) -> Dict[str, Any]:
        """Generate manifest data for the archive.
        
        Args:
            files: List of files in archive.
            config: ZIP configuration.
            
        Returns:
            Manifest dictionary.
        """
        return {
            "archive_info": {
                "name": config.archive_name,
                "created_at": datetime.utcnow().isoformat(),
                "generator": "FIBO Omni-Director Pro",
                "version": "2.0.0",
                "file_count": len(files),
                "structure": config.structure.value,
                "compression": {
                    "method": config.compression_method.name,
                    "level": config.compression_level
                }
            },
            "files": [
                {
                    "file_id": file.file_id,
                    "original_filename": file.original_filename,
                    "file_size": file.file_size,
                    "content_type": file.content_type,
                    "checksum": file.checksum,
                    "created_at": file.created_at.isoformat() if file.created_at else None,
                    "metadata": file.metadata
                }
                for file in files
            ],
            "statistics": {
                "total_size": sum(f.file_size for f in files),
                "file_types": self._get_file_type_stats(files),
                "size_distribution": self._get_size_distribution(files)
            }
        }
    
    def _generate_csv_index(self, files: List[StoredFile]) -> str:
        """Generate CSV index of files.
        
        Args:
            files: List of files in archive.
            
        Returns:
            CSV content string.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "file_id", "original_filename", "file_size", "content_type", 
            "checksum", "created_at", "has_metadata"
        ])
        
        # Data rows
        for file in files:
            writer.writerow([
                file.file_id,
                file.original_filename,
                file.file_size,
                file.content_type,
                file.checksum,
                file.created_at.isoformat() if file.created_at else "",
                bool(file.metadata)
            ])
        
        return output.getvalue()
    
    def _get_file_type_stats(self, files: List[StoredFile]) -> Dict[str, int]:
        """Get file type statistics.
        
        Args:
            files: List of files to analyze.
            
        Returns:
            Dictionary of file type counts.
        """
        type_counts = {}
        for file in files:
            ext = Path(file.original_filename).suffix.lower()
            if not ext:
                ext = "no_extension"
            type_counts[ext] = type_counts.get(ext, 0) + 1
        return type_counts
    
    def _get_size_distribution(self, files: List[StoredFile]) -> Dict[str, int]:
        """Get file size distribution.
        
        Args:
            files: List of files to analyze.
            
        Returns:
            Dictionary of size distribution.
        """
        size_ranges = {
            "< 1MB": 0,
            "1-10MB": 0,
            "10-100MB": 0,
            "> 100MB": 0
        }
        
        for file in files:
            size_mb = file.file_size / (1024 * 1024)
            if size_mb < 1:
                size_ranges["< 1MB"] += 1
            elif size_mb < 10:
                size_ranges["1-10MB"] += 1
            elif size_mb < 100:
                size_ranges["10-100MB"] += 1
            else:
                size_ranges["> 100MB"] += 1
        
        return size_ranges
    
    def _generate_download_token(self) -> str:
        """Generate a unique download token.
        
        Returns:
            Unique download token string.
        """
        return str(uuid.uuid4()).replace('-', '')[:16]