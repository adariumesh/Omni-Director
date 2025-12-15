"""API routes for asset management and database operations."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db, Asset, Project
from app.repositories.asset_repository import AssetRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/assets",
    tags=["assets"],
    responses={
        404: {"description": "Asset not found"},
        500: {"description": "Internal server error"},
    }
)


# ==================== Response Models ====================


class AssetResponse(BaseModel):
    """Response model for asset information."""
    id: str
    project_id: str
    parent_id: Optional[str]
    prompt: str
    seed: int
    aspect_ratio: str
    image_url: Optional[str]
    image_path: Optional[str]
    file_id: Optional[str]
    thumbnail_path: Optional[str]
    file_size: Optional[int]
    content_type: Optional[str]
    generation_mode: Optional[str]
    api_provider: Optional[str]
    matrix_position: Optional[str]
    created_at: str
    has_local_file: bool = False
    has_thumbnail: bool = False


class ProjectResponse(BaseModel):
    """Response model for project information."""
    id: str
    name: str
    brand_logo_path: Optional[str]
    negative_prompt: Optional[str]
    created_at: str
    updated_at: str
    asset_count: int = 0


class AssetLineageResponse(BaseModel):
    """Response for asset lineage/family tree."""
    root_asset: AssetResponse
    lineage_chain: List[AssetResponse]
    children: List[AssetResponse]
    total_descendants: int


class StorageStatsResponse(BaseModel):
    """Response for database storage statistics."""
    total_assets: int
    assets_with_files: int
    total_file_size_mb: float
    provider_distribution: Dict[str, int]
    mode_distribution: Dict[str, int]
    file_coverage_percent: float


class CreateProjectRequest(BaseModel):
    """Request to create a new project."""
    name: str = Field(..., min_length=1, max_length=255)
    brand_logo_path: Optional[str] = Field(None, max_length=500)
    negative_prompt: Optional[str] = Field(None, max_length=1000)


class UpdateProjectRequest(BaseModel):
    """Request to update a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    brand_logo_path: Optional[str] = Field(None, max_length=500)
    negative_prompt: Optional[str] = Field(None, max_length=1000)


# ==================== Dependencies ====================


def get_repository(db: Session = Depends(get_db)) -> AssetRepository:
    """Get asset repository instance."""
    return AssetRepository(db)


# ==================== Helper Functions ====================


def _asset_to_response(asset: Asset) -> AssetResponse:
    """Convert Asset model to response."""
    return AssetResponse(
        id=asset.id,
        project_id=asset.project_id,
        parent_id=asset.parent_id,
        prompt=asset.prompt,
        seed=asset.seed,
        aspect_ratio=asset.aspect_ratio,
        image_url=asset.image_url,
        image_path=asset.image_path,
        file_id=asset.file_id,
        thumbnail_path=asset.thumbnail_path,
        file_size=asset.file_size,
        content_type=asset.content_type,
        generation_mode=asset.generation_mode,
        api_provider=asset.api_provider,
        matrix_position=asset.matrix_position,
        created_at=asset.created_at.isoformat(),
        has_local_file=bool(asset.file_id),
        has_thumbnail=bool(asset.thumbnail_path)
    )


def _project_to_response(project: Project, asset_count: int = 0) -> ProjectResponse:
    """Convert Project model to response."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        brand_logo_path=project.brand_logo_path,
        negative_prompt=project.negative_prompt,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        asset_count=asset_count
    )


# ==================== Project Routes ====================


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    repository: AssetRepository = Depends(get_repository)
) -> ProjectResponse:
    """Create a new project."""
    try:
        project = repository.create_project(
            name=request.name,
            brand_logo_path=request.brand_logo_path,
            negative_prompt=request.negative_prompt
        )
        
        return _project_to_response(project)
        
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    repository: AssetRepository = Depends(get_repository)
) -> List[ProjectResponse]:
    """Get all projects with asset counts."""
    try:
        projects = repository.get_all_projects()
        
        responses = []
        for project in projects:
            asset_count = len(repository.get_assets_by_project(project.id))
            responses.append(_project_to_response(project, asset_count))
        
        return responses
        
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    repository: AssetRepository = Depends(get_repository)
) -> ProjectResponse:
    """Get project by ID."""
    try:
        project = repository.get_project(project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )
        
        asset_count = len(repository.get_assets_by_project(project.id))
        return _project_to_response(project, asset_count)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    repository: AssetRepository = Depends(get_repository)
) -> ProjectResponse:
    """Update a project."""
    try:
        project = repository.update_project(
            project_id=project_id,
            name=request.name,
            brand_logo_path=request.brand_logo_path,
            negative_prompt=request.negative_prompt
        )
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )
        
        asset_count = len(repository.get_assets_by_project(project.id))
        return _project_to_response(project, asset_count)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    repository: AssetRepository = Depends(get_repository)
) -> Dict[str, Any]:
    """Delete a project and all its assets."""
    try:
        deleted = repository.delete_project(project_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )
        
        return {
            "success": True,
            "message": f"Project {project_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


# ==================== Asset Routes ====================


@router.get("/projects/{project_id}/assets", response_model=List[AssetResponse])
async def get_project_assets(
    project_id: str,
    repository: AssetRepository = Depends(get_repository)
) -> List[AssetResponse]:
    """Get all assets for a project."""
    try:
        assets = repository.get_assets_by_project(project_id)
        return [_asset_to_response(asset) for asset in assets]
        
    except Exception as e:
        logger.error(f"Failed to get assets for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project assets: {str(e)}"
        )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    repository: AssetRepository = Depends(get_repository)
) -> AssetResponse:
    """Get asset by ID."""
    try:
        asset = repository.get_asset(asset_id)
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset not found: {asset_id}"
            )
        
        return _asset_to_response(asset)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get asset {asset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get asset: {str(e)}"
        )


@router.get("/{asset_id}/lineage", response_model=AssetLineageResponse)
async def get_asset_lineage(
    asset_id: str,
    repository: AssetRepository = Depends(get_repository)
) -> AssetLineageResponse:
    """Get asset lineage (family tree)."""
    try:
        asset = repository.get_asset(asset_id)
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset not found: {asset_id}"
            )
        
        # Get full lineage (ancestors)
        lineage = repository.get_asset_lineage(asset_id)
        
        # Get direct children
        children = repository.get_asset_children(asset_id)
        
        # Count all descendants recursively
        total_descendants = len(children)
        for child in children:
            total_descendants += len(repository.get_asset_children(child.id))
        
        return AssetLineageResponse(
            root_asset=_asset_to_response(lineage[0] if lineage else asset),
            lineage_chain=[_asset_to_response(a) for a in lineage],
            children=[_asset_to_response(child) for child in children],
            total_descendants=total_descendants
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lineage for asset {asset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get asset lineage: {str(e)}"
        )


@router.get("/{asset_id}/json")
async def get_asset_json(
    asset_id: str,
    repository: AssetRepository = Depends(get_repository)
) -> Dict[str, Any]:
    """Get asset JSON payload."""
    try:
        json_payload = repository.get_json_payload(asset_id)
        
        if json_payload is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset not found or has no JSON payload: {asset_id}"
            )
        
        return json_payload
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get JSON for asset {asset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get asset JSON: {str(e)}"
        )


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    repository: AssetRepository = Depends(get_repository)
) -> Dict[str, Any]:
    """Delete an asset."""
    try:
        deleted = repository.delete_asset(asset_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset not found: {asset_id}"
            )
        
        return {
            "success": True,
            "message": f"Asset {asset_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete asset {asset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete asset: {str(e)}"
        )


# ==================== Search and Filter Routes ====================


@router.get("/search/by-seed/{seed}", response_model=List[AssetResponse])
async def search_assets_by_seed(
    seed: int,
    repository: AssetRepository = Depends(get_repository)
) -> List[AssetResponse]:
    """Search assets by generation seed."""
    try:
        assets = repository.get_assets_by_seed(seed)
        return [_asset_to_response(asset) for asset in assets]
        
    except Exception as e:
        logger.error(f"Failed to search assets by seed {seed}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search assets: {str(e)}"
        )


@router.get("/search/by-provider/{provider}", response_model=List[AssetResponse])
async def search_assets_by_provider(
    provider: str,
    repository: AssetRepository = Depends(get_repository)
) -> List[AssetResponse]:
    """Search assets by API provider."""
    try:
        assets = repository.get_assets_by_provider(provider)
        return [_asset_to_response(asset) for asset in assets]
        
    except Exception as e:
        logger.error(f"Failed to search assets by provider {provider}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search assets: {str(e)}"
        )


@router.get("/search/by-mode/{mode}", response_model=List[AssetResponse])
async def search_assets_by_mode(
    mode: str,
    repository: AssetRepository = Depends(get_repository)
) -> List[AssetResponse]:
    """Search assets by generation mode."""
    try:
        assets = repository.get_assets_by_mode(mode)
        return [_asset_to_response(asset) for asset in assets]
        
    except Exception as e:
        logger.error(f"Failed to search assets by mode {mode}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search assets: {str(e)}"
        )


@router.get("/search/by-file/{file_id}", response_model=AssetResponse)
async def search_asset_by_file_id(
    file_id: str,
    repository: AssetRepository = Depends(get_repository)
) -> AssetResponse:
    """Search asset by file storage ID."""
    try:
        asset = repository.get_asset_by_file_id(file_id)
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset not found for file ID: {file_id}"
            )
        
        return _asset_to_response(asset)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search asset by file ID {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search asset: {str(e)}"
        )


# ==================== Statistics Routes ====================


@router.get("/stats/storage", response_model=StorageStatsResponse)
async def get_storage_statistics(
    repository: AssetRepository = Depends(get_repository)
) -> StorageStatsResponse:
    """Get database storage statistics."""
    try:
        stats = repository.get_storage_statistics()
        
        return StorageStatsResponse(
            total_assets=stats["total_assets"],
            assets_with_files=stats["assets_with_files"],
            total_file_size_mb=stats["total_file_size_mb"],
            provider_distribution=stats["provider_distribution"],
            mode_distribution=stats["mode_distribution"],
            file_coverage_percent=stats["file_coverage_percent"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get storage statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage statistics: {str(e)}"
        )