"""API routes for file storage and management."""

import logging
from typing import List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, Response, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.file_storage import get_file_storage, FileStorageManager, StoredFile, FileStorageError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/files",
    tags=["files"],
    responses={
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    }
)


# ==================== Response Models ====================


class FileInfoResponse(BaseModel):
    """Response for file information."""
    file_id: str
    original_filename: str
    file_size: int
    content_type: str
    created_at: str
    has_local_copy: bool
    has_thumbnail: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StorageStatsResponse(BaseModel):
    """Response for storage statistics."""
    total_size_mb: float
    total_files: int
    images: Dict[str, Any]
    thumbnails: Dict[str, Any]
    temp: Dict[str, Any]
    base_path: str


class DownloadRequest(BaseModel):
    """Request to download file from URL."""
    url: str = Field(..., description="URL to download from")
    filename: str = Field(None, description="Optional custom filename")


class DownloadResponse(BaseModel):
    """Response for file download."""
    success: bool
    file_id: str = Field(None)
    filename: str = Field(None)
    message: str
    file_info: FileInfoResponse = Field(None)


# ==================== Dependencies ====================


def get_storage_manager() -> FileStorageManager:
    """Get file storage manager instance."""
    return get_file_storage()


# ==================== Routes ====================


@router.get("/stats", response_model=StorageStatsResponse)
async def get_storage_stats(
    storage: FileStorageManager = Depends(get_storage_manager)
) -> StorageStatsResponse:
    """Get file storage statistics."""
    try:
        stats = storage.get_storage_stats()
        
        return StorageStatsResponse(
            total_size_mb=stats["total_size_mb"],
            total_files=stats["images"]["count"] + stats["thumbnails"]["count"] + stats["temp"]["count"],
            images=stats["images"],
            thumbnails=stats["thumbnails"],
            temp=stats["temp"],
            base_path=stats["base_path"]
        )
        
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage stats: {str(e)}"
        )


@router.get("/list", response_model=List[FileInfoResponse])
async def list_files(
    pattern: str = "*",
    storage: FileStorageManager = Depends(get_storage_manager)
) -> List[FileInfoResponse]:
    """List all stored files."""
    try:
        files = storage.list_files(pattern)
        
        return [
            FileInfoResponse(
                file_id=f.file_id,
                original_filename=f.original_filename,
                file_size=f.file_size,
                content_type=f.content_type,
                created_at=f.created_at.isoformat(),
                has_local_copy=f.stored_path.exists(),
                has_thumbnail=any(
                    storage.thumbnails_path.glob(f"thumb_{f.file_id}_*")
                ),
                metadata=f.metadata or {}
            )
            for f in files
        ]
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )


@router.get("/{file_id}", response_model=FileInfoResponse)
async def get_file_info(
    file_id: str,
    storage: FileStorageManager = Depends(get_storage_manager)
) -> FileInfoResponse:
    """Get information about a specific file."""
    try:
        stored_file = storage.get_file_info(file_id)
        
        if not stored_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}"
            )
        
        return FileInfoResponse(
            file_id=stored_file.file_id,
            original_filename=stored_file.original_filename,
            file_size=stored_file.file_size,
            content_type=stored_file.content_type,
            created_at=stored_file.created_at.isoformat(),
            has_local_copy=stored_file.stored_path.exists(),
            has_thumbnail=any(
                storage.thumbnails_path.glob(f"thumb_{file_id}_*")
            ),
            metadata=stored_file.metadata or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info for {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file info: {str(e)}"
        )


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    storage: FileStorageManager = Depends(get_storage_manager)
) -> FileResponse:
    """Download a stored file."""
    try:
        stored_file = storage.get_file_info(file_id)
        
        if not stored_file or not stored_file.stored_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}"
            )
        
        return FileResponse(
            path=stored_file.stored_path,
            filename=stored_file.original_filename,
            media_type=stored_file.content_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


@router.get("/{file_id}/thumbnail")
async def get_thumbnail(
    file_id: str,
    size: str = "256x256",
    storage: FileStorageManager = Depends(get_storage_manager)
) -> FileResponse:
    """Get thumbnail for a file."""
    try:
        # Parse size
        try:
            width, height = map(int, size.split("x"))
            thumbnail_size = (width, height)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid size format. Use 'WIDTHxHEIGHT' (e.g., '256x256')"
            )
        
        # Get file info
        stored_file = storage.get_file_info(file_id)
        
        if not stored_file or not stored_file.stored_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}"
            )
        
        # Create or get thumbnail
        thumbnail_path = storage.create_thumbnail(stored_file, thumbnail_size)
        
        if not thumbnail_path or not thumbnail_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create thumbnail"
            )
        
        return FileResponse(
            path=thumbnail_path,
            media_type="image/jpeg",
            filename=f"thumb_{stored_file.original_filename}.jpg"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thumbnail for {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get thumbnail: {str(e)}"
        )


@router.post("/download", response_model=DownloadResponse)
async def download_from_url(
    request: DownloadRequest,
    storage: FileStorageManager = Depends(get_storage_manager)
) -> DownloadResponse:
    """Download a file from a URL and store it."""
    try:
        stored_file = storage.download_image_from_url(
            url=request.url,
            filename=request.filename
        )
        
        # Create thumbnail
        thumbnail_path = storage.create_thumbnail(stored_file)
        
        return DownloadResponse(
            success=True,
            file_id=stored_file.file_id,
            filename=stored_file.original_filename,
            message=f"File downloaded and stored successfully",
            file_info=FileInfoResponse(
                file_id=stored_file.file_id,
                original_filename=stored_file.original_filename,
                file_size=stored_file.file_size,
                content_type=stored_file.content_type,
                created_at=stored_file.created_at.isoformat(),
                has_local_copy=True,
                has_thumbnail=thumbnail_path is not None,
                metadata=stored_file.metadata or {}
            )
        )
        
    except FileStorageError as e:
        logger.warning(f"File storage error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Error downloading from URL {request.url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {str(e)}"
        )


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    include_thumbnails: bool = True,
    storage: FileStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """Delete a stored file."""
    try:
        deleted = storage.delete_file(file_id, include_thumbnails)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}"
            )
        
        return {
            "success": True,
            "message": f"File {file_id} deleted successfully",
            "thumbnails_deleted": include_thumbnails
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_temp_files(
    max_age_hours: int = 24,
    storage: FileStorageManager = Depends(get_storage_manager)
) -> Dict[str, Any]:
    """Clean up temporary files older than specified age."""
    try:
        deleted_count = storage.cleanup_temp_files(max_age_hours)
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} temporary files"
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )