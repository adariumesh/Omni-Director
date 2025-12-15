"""File storage and management system for FIBO Omni-Director Pro."""

import logging
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse
import httpx
from PIL import Image
import io

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class StoredFile:
    """Information about a stored file."""
    file_id: str
    original_filename: str
    stored_path: Path
    file_size: int
    content_type: str
    checksum: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ImageInfo:
    """Information about an image file."""
    width: int
    height: int
    format: str
    mode: str
    has_transparency: bool
    file_size: int


class FileStorageError(Exception):
    """Exception raised when file storage operations fail."""
    
    def __init__(self, message: str, operation: str = "storage"):
        self.message = message
        self.operation = operation
        super().__init__(message)


class FileStorageManager:
    """Manages file storage, downloads, and organization."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize file storage manager.
        
        Args:
            base_path: Base directory for file storage.
        """
        self.base_path = base_path or settings.data_dir / "files"
        self.images_path = self.base_path / "images"
        self.thumbnails_path = self.base_path / "thumbnails"
        self.temp_path = self.base_path / "temp"
        
        # Create directories
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.images_path.mkdir(parents=True, exist_ok=True)
        self.thumbnails_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Configure HTTP client for downloads
        self.http_client = httpx.Client(
            timeout=30.0,
            headers={"User-Agent": "FIBO-Omni-Director/2.0"}
        )
        
        logger.info(f"File storage initialized at {self.base_path}")
    
    def download_image_from_url(self, url: str, filename: Optional[str] = None) -> StoredFile:
        """Download an image from a URL and store it locally.
        
        Args:
            url: URL to download from.
            filename: Optional custom filename.
            
        Returns:
            StoredFile with download information.
            
        Raises:
            FileStorageError: If download or storage fails.
        """
        logger.info(f"Downloading image from: {url}")
        
        try:
            # Download the file
            response = self.http_client.get(url)
            response.raise_for_status()
            
            # Get content info
            content = response.content
            content_type = response.headers.get("content-type", "application/octet-stream")
            
            # Generate filename if not provided
            if not filename:
                parsed_url = urlparse(url)
                url_filename = Path(parsed_url.path).name
                if url_filename and "." in url_filename:
                    filename = url_filename
                else:
                    extension = mimetypes.guess_extension(content_type) or ".jpg"
                    filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
            
            # Validate it's an image
            try:
                with Image.open(io.BytesIO(content)) as img:
                    img.verify()  # Verify it's a valid image
            except Exception as e:
                raise FileStorageError(f"Invalid image file: {e}", "validation")
            
            # Generate file ID and paths
            file_id = self._generate_file_id(content, url)
            stored_path = self.images_path / f"{file_id}_{filename}"
            
            # Write file
            stored_path.write_bytes(content)
            
            # Calculate checksum
            checksum = hashlib.sha256(content).hexdigest()
            
            # Get image info
            with Image.open(io.BytesIO(content)) as img:
                image_info = ImageInfo(
                    width=img.width,
                    height=img.height,
                    format=img.format or "UNKNOWN",
                    mode=img.mode,
                    has_transparency=img.mode in ("RGBA", "LA") or "transparency" in img.info,
                    file_size=len(content)
                )
            
            stored_file = StoredFile(
                file_id=file_id,
                original_filename=filename,
                stored_path=stored_path,
                file_size=len(content),
                content_type=content_type,
                checksum=checksum,
                created_at=datetime.utcnow(),
                metadata={
                    "source_url": url,
                    "image_info": image_info.__dict__,
                    "download_headers": dict(response.headers)
                }
            )
            
            logger.info(f"✅ Downloaded and stored: {filename} ({len(content)} bytes)")
            return stored_file
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error downloading {url}: {e}")
            raise FileStorageError(f"Download failed: {e}", "download")
            
        except Exception as e:
            logger.error(f"Error storing file from {url}: {e}")
            raise FileStorageError(f"Storage failed: {e}", "storage")
    
    def create_thumbnail(self, stored_file: StoredFile, size: tuple = (256, 256)) -> Optional[Path]:
        """Create a thumbnail for an image file.
        
        Args:
            stored_file: StoredFile to create thumbnail for.
            size: Thumbnail size as (width, height).
            
        Returns:
            Path to created thumbnail or None if failed.
        """
        try:
            if not stored_file.stored_path.exists():
                logger.warning(f"Source file not found: {stored_file.stored_path}")
                return None
            
            # Generate thumbnail path
            thumbnail_name = f"thumb_{stored_file.file_id}_{size[0]}x{size[1]}.jpg"
            thumbnail_path = self.thumbnails_path / thumbnail_name
            
            # Skip if thumbnail already exists
            if thumbnail_path.exists():
                return thumbnail_path
            
            # Create thumbnail
            with Image.open(stored_file.stored_path) as img:
                # Convert to RGB if necessary (for JPEG output)
                if img.mode in ("RGBA", "LA", "P"):
                    # Create white background for transparent images
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                    img = background
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, "JPEG", quality=85, optimize=True)
            
            logger.debug(f"Created thumbnail: {thumbnail_path}")
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Failed to create thumbnail for {stored_file.file_id}: {e}")
            return None
    
    def get_file_info(self, file_id: str) -> Optional[StoredFile]:
        """Get information about a stored file.
        
        Args:
            file_id: File ID to look up.
            
        Returns:
            StoredFile if found, None otherwise.
        """
        # Search for file with this ID
        for file_path in self.images_path.glob(f"{file_id}_*"):
            if file_path.is_file():
                try:
                    stat = file_path.stat()
                    return StoredFile(
                        file_id=file_id,
                        original_filename=file_path.name[len(file_id) + 1:],  # Remove ID prefix
                        stored_path=file_path,
                        file_size=stat.st_size,
                        content_type=mimetypes.guess_type(file_path)[0] or "application/octet-stream",
                        checksum="",  # Would need to recalculate
                        created_at=datetime.fromtimestamp(stat.st_ctime),
                        metadata={}
                    )
                except Exception as e:
                    logger.warning(f"Error reading file info for {file_path}: {e}")
                    continue
        
        return None
    
    def list_files(self, pattern: str = "*") -> List[StoredFile]:
        """List all stored files matching pattern.
        
        Args:
            pattern: Glob pattern to match files.
            
        Returns:
            List of StoredFile objects.
        """
        files = []
        
        for file_path in self.images_path.glob(pattern):
            if file_path.is_file():
                try:
                    # Extract file ID from filename
                    filename = file_path.name
                    if "_" in filename:
                        file_id = filename.split("_", 1)[0]
                        original_filename = filename.split("_", 1)[1]
                    else:
                        file_id = filename
                        original_filename = filename
                    
                    stat = file_path.stat()
                    files.append(StoredFile(
                        file_id=file_id,
                        original_filename=original_filename,
                        stored_path=file_path,
                        file_size=stat.st_size,
                        content_type=mimetypes.guess_type(file_path)[0] or "application/octet-stream",
                        checksum="",
                        created_at=datetime.fromtimestamp(stat.st_ctime),
                        metadata={}
                    ))
                except Exception as e:
                    logger.warning(f"Error reading file {file_path}: {e}")
        
        return sorted(files, key=lambda f: f.created_at, reverse=True)
    
    def delete_file(self, file_id: str, include_thumbnails: bool = True) -> bool:
        """Delete a stored file and its thumbnails.
        
        Args:
            file_id: File ID to delete.
            include_thumbnails: Whether to delete thumbnails too.
            
        Returns:
            True if file was deleted, False if not found.
        """
        deleted = False
        
        # Delete main file
        for file_path in self.images_path.glob(f"{file_id}_*"):
            try:
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")
                deleted = True
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {e}")
        
        # Delete thumbnails
        if include_thumbnails:
            for thumb_path in self.thumbnails_path.glob(f"thumb_{file_id}_*"):
                try:
                    thumb_path.unlink()
                    logger.debug(f"Deleted thumbnail: {thumb_path}")
                except Exception as e:
                    logger.warning(f"Error deleting thumbnail {thumb_path}: {e}")
        
        return deleted
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours for temp files.
            
        Returns:
            Number of files deleted.
        """
        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        for temp_file in self.temp_path.glob("*"):
            try:
                if temp_file.stat().st_mtime < cutoff_time:
                    temp_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Error cleaning temp file {temp_file}: {e}")
        
        logger.info(f"Cleaned up {deleted_count} temporary files")
        return deleted_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage usage statistics.
        
        Returns:
            Dictionary with storage stats.
        """
        try:
            images_size = sum(f.stat().st_size for f in self.images_path.rglob("*") if f.is_file())
            images_count = len([f for f in self.images_path.glob("*") if f.is_file()])
            
            thumbnails_size = sum(f.stat().st_size for f in self.thumbnails_path.rglob("*") if f.is_file())
            thumbnails_count = len([f for f in self.thumbnails_path.glob("*") if f.is_file()])
            
            temp_size = sum(f.stat().st_size for f in self.temp_path.rglob("*") if f.is_file())
            temp_count = len([f for f in self.temp_path.glob("*") if f.is_file()])
            
            total_size = images_size + thumbnails_size + temp_size
            
            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "images": {
                    "count": images_count,
                    "size_bytes": images_size,
                    "size_mb": round(images_size / 1024 / 1024, 2)
                },
                "thumbnails": {
                    "count": thumbnails_count,
                    "size_bytes": thumbnails_size,
                    "size_mb": round(thumbnails_size / 1024 / 1024, 2)
                },
                "temp": {
                    "count": temp_count,
                    "size_bytes": temp_size,
                    "size_mb": round(temp_size / 1024 / 1024, 2)
                },
                "base_path": str(self.base_path)
            }
            
        except Exception as e:
            logger.error(f"Error calculating storage stats: {e}")
            return {"error": str(e)}
    
    def _generate_file_id(self, content: bytes, source_url: str) -> str:
        """Generate a unique file ID based on content and source.
        
        Args:
            content: File content bytes.
            source_url: Source URL.
            
        Returns:
            Unique file ID string.
        """
        # Use content hash + URL hash for uniqueness
        content_hash = hashlib.sha256(content).hexdigest()[:16]
        url_hash = hashlib.md5(source_url.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%y%m%d%H%M")
        
        return f"{timestamp}_{content_hash}_{url_hash}"
    
    def __del__(self):
        """Clean up HTTP client on destruction."""
        try:
            self.http_client.close()
        except:
            pass


# Global instance
_storage_manager: Optional[FileStorageManager] = None


def get_file_storage() -> FileStorageManager:
    """Get global file storage manager instance.
    
    Returns:
        FileStorageManager instance.
    """
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = FileStorageManager()
    return _storage_manager