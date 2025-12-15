"""Repository for Asset and Project database operations."""

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.database import Asset, Project


class AssetRepository:
    """Repository for Asset CRUD operations."""

    def __init__(self, db: Session) -> None:
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    # ==================== Project Operations ====================

    def create_project(
        self,
        name: str,
        brand_logo_path: str | None = None,
        negative_prompt: str | None = None,
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name.
            brand_logo_path: Optional path to brand logo.
            negative_prompt: Optional negative prompt for brand safety.

        Returns:
            Created Project instance.
        """
        project = Project(
            name=name,
            brand_logo_path=brand_logo_path,
            negative_prompt=negative_prompt,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_project(self, project_id: str) -> Project | None:
        """Get project by ID.

        Args:
            project_id: UUID of the project.

        Returns:
            Project instance or None if not found.
        """
        return self.db.query(Project).filter(Project.id == project_id).first()

    def get_all_projects(self) -> list[Project]:
        """Get all projects ordered by creation date.

        Returns:
            List of all projects.
        """
        return self.db.query(Project).order_by(Project.created_at.desc()).all()

    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        brand_logo_path: str | None = None,
        negative_prompt: str | None = None,
    ) -> Project | None:
        """Update project fields.

        Args:
            project_id: UUID of the project.
            name: Optional new name.
            brand_logo_path: Optional new logo path.
            negative_prompt: Optional new negative prompt.

        Returns:
            Updated Project or None if not found.
        """
        project = self.get_project(project_id)
        if not project:
            return None

        if name is not None:
            project.name = name
        if brand_logo_path is not None:
            project.brand_logo_path = brand_logo_path
        if negative_prompt is not None:
            project.negative_prompt = negative_prompt

        project.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete_project(self, project_id: str) -> bool:
        """Delete project and all associated assets.

        Args:
            project_id: UUID of the project.

        Returns:
            True if deleted, False if not found.
        """
        project = self.get_project(project_id)
        if not project:
            return False

        self.db.delete(project)
        self.db.commit()
        return True

    # ==================== Asset Operations ====================

    def create_asset(
        self,
        project_id: str,
        prompt: str,
        seed: int,
        json_payload: dict,
        aspect_ratio: str = "1:1",
        parent_id: str | None = None,
        image_url: str | None = None,
        image_path: str | None = None,
        matrix_position: str | None = None,
        file_id: str | None = None,
        thumbnail_path: str | None = None,
        file_size: int | None = None,
        content_type: str | None = None,
        checksum: str | None = None,
        generation_mode: str | None = None,
        generation_time: float | None = None,
        api_provider: str | None = None,
    ) -> Asset:
        """Create a new asset.

        Args:
            project_id: UUID of parent project.
            prompt: Generation prompt.
            seed: Random seed used.
            json_payload: Full JSON request payload.
            aspect_ratio: Image aspect ratio.
            parent_id: Optional parent asset ID for refinements.
            image_url: Optional Bria CDN URL.
            image_path: Optional local file path.
            matrix_position: Optional matrix position (e.g., "0,1").
            file_id: Optional file storage ID.
            thumbnail_path: Optional thumbnail path.
            file_size: Optional file size in bytes.
            content_type: Optional content type.
            checksum: Optional file checksum.
            generation_mode: Optional generation mode (generate/refine/inspire).
            generation_time: Optional generation time in milliseconds.
            api_provider: Optional API provider used.

        Returns:
            Created Asset instance.
        """
        asset = Asset(
            project_id=project_id,
            parent_id=parent_id,
            prompt=prompt,
            seed=seed,
            aspect_ratio=aspect_ratio,
            image_url=image_url,
            image_path=image_path,
            json_payload=json.dumps(json_payload),
            matrix_position=matrix_position,
            file_id=file_id,
            thumbnail_path=thumbnail_path,
            file_size=file_size,
            content_type=content_type,
            checksum=checksum,
            generation_mode=generation_mode,
            generation_time=generation_time,
            api_provider=api_provider,
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get asset by ID.

        Args:
            asset_id: UUID of the asset.

        Returns:
            Asset instance or None if not found.
        """
        return self.db.query(Asset).filter(Asset.id == asset_id).first()

    def get_assets_by_project(self, project_id: str) -> list[Asset]:
        """Get all assets for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of assets ordered by creation date.
        """
        return (
            self.db.query(Asset)
            .filter(Asset.project_id == project_id)
            .order_by(Asset.created_at.desc())
            .all()
        )

    def get_assets_by_seed(self, seed: int) -> list[Asset]:
        """Get all assets with a specific seed.

        Args:
            seed: The generation seed.

        Returns:
            List of assets with that seed.
        """
        return self.db.query(Asset).filter(Asset.seed == seed).all()

    def get_matrix_assets(self, project_id: str, seed: int) -> list[Asset]:
        """Get all 9 assets from a matrix generation.

        Args:
            project_id: UUID of the project.
            seed: The locked seed used for the matrix.

        Returns:
            List of 9 assets (or fewer if incomplete).
        """
        return (
            self.db.query(Asset)
            .filter(
                Asset.project_id == project_id,
                Asset.seed == seed,
                Asset.matrix_position.isnot(None),
            )
            .order_by(Asset.matrix_position)
            .all()
        )

    def get_asset_children(self, asset_id: str) -> list[Asset]:
        """Get all child assets (refinements) of an asset.

        Args:
            asset_id: UUID of the parent asset.

        Returns:
            List of child assets.
        """
        return (
            self.db.query(Asset)
            .filter(Asset.parent_id == asset_id)
            .order_by(Asset.created_at.desc())
            .all()
        )

    def get_asset_lineage(self, asset_id: str) -> list[Asset]:
        """Get full lineage of an asset (all ancestors).

        Args:
            asset_id: UUID of the asset.

        Returns:
            List of assets from root to current.
        """
        lineage = []
        current = self.get_asset(asset_id)

        while current:
            lineage.insert(0, current)
            if current.parent_id:
                current = self.get_asset(current.parent_id)
            else:
                break

        return lineage

    def update_asset_image(
        self,
        asset_id: str,
        image_url: str | None = None,
        image_path: str | None = None,
    ) -> Asset | None:
        """Update asset image paths.

        Args:
            asset_id: UUID of the asset.
            image_url: Optional new URL.
            image_path: Optional new local path.

        Returns:
            Updated Asset or None if not found.
        """
        asset = self.get_asset(asset_id)
        if not asset:
            return None

        if image_url is not None:
            asset.image_url = image_url
        if image_path is not None:
            asset.image_path = image_path

        self.db.commit()
        self.db.refresh(asset)
        return asset

    def delete_asset(self, asset_id: str) -> bool:
        """Delete an asset.

        Args:
            asset_id: UUID of the asset.

        Returns:
            True if deleted, False if not found.
        """
        asset = self.get_asset(asset_id)
        if not asset:
            return False

        self.db.delete(asset)
        self.db.commit()
        return True

    def get_json_payload(self, asset_id: str) -> dict | None:
        """Get parsed JSON payload for an asset.

        Args:
            asset_id: UUID of the asset.

        Returns:
            Parsed JSON dict or None if not found.
        """
        asset = self.get_asset(asset_id)
        if not asset:
            return None

        try:
            return json.loads(asset.json_payload)
        except json.JSONDecodeError:
            return None

    # ==================== File Storage Integration ====================

    def get_asset_by_file_id(self, file_id: str) -> Asset | None:
        """Get asset by file storage ID.

        Args:
            file_id: File storage ID.

        Returns:
            Asset instance or None if not found.
        """
        return self.db.query(Asset).filter(Asset.file_id == file_id).first()

    def get_assets_by_provider(self, api_provider: str) -> list[Asset]:
        """Get all assets generated by a specific API provider.

        Args:
            api_provider: API provider name (e.g., "bria", "fal", "replicate").

        Returns:
            List of assets from that provider.
        """
        return (
            self.db.query(Asset)
            .filter(Asset.api_provider == api_provider)
            .order_by(Asset.created_at.desc())
            .all()
        )

    def get_assets_by_mode(self, generation_mode: str) -> list[Asset]:
        """Get all assets by generation mode.

        Args:
            generation_mode: Generation mode (generate/refine/inspire).

        Returns:
            List of assets using that mode.
        """
        return (
            self.db.query(Asset)
            .filter(Asset.generation_mode == generation_mode)
            .order_by(Asset.created_at.desc())
            .all()
        )

    def update_asset_file_info(
        self,
        asset_id: str,
        file_id: str | None = None,
        thumbnail_path: str | None = None,
        file_size: int | None = None,
        content_type: str | None = None,
        checksum: str | None = None,
    ) -> Asset | None:
        """Update asset file storage information.

        Args:
            asset_id: UUID of the asset.
            file_id: Optional file storage ID.
            thumbnail_path: Optional thumbnail path.
            file_size: Optional file size.
            content_type: Optional content type.
            checksum: Optional file checksum.

        Returns:
            Updated Asset or None if not found.
        """
        asset = self.get_asset(asset_id)
        if not asset:
            return None

        if file_id is not None:
            asset.file_id = file_id
        if thumbnail_path is not None:
            asset.thumbnail_path = thumbnail_path
        if file_size is not None:
            asset.file_size = file_size
        if content_type is not None:
            asset.content_type = content_type
        if checksum is not None:
            asset.checksum = checksum

        self.db.commit()
        self.db.refresh(asset)
        return asset

    def get_storage_statistics(self) -> dict:
        """Get storage statistics for all assets.

        Returns:
            Dictionary with storage statistics.
        """
        from sqlalchemy import func
        
        total_assets = self.db.query(Asset).count()
        
        assets_with_files = self.db.query(Asset).filter(
            Asset.file_id.isnot(None)
        ).count()
        
        total_file_size = self.db.query(func.sum(Asset.file_size)).filter(
            Asset.file_size.isnot(None)
        ).scalar() or 0
        
        provider_stats = self.db.query(
            Asset.api_provider,
            func.count(Asset.id).label('count')
        ).filter(
            Asset.api_provider.isnot(None)
        ).group_by(Asset.api_provider).all()
        
        mode_stats = self.db.query(
            Asset.generation_mode,
            func.count(Asset.id).label('count')
        ).filter(
            Asset.generation_mode.isnot(None)
        ).group_by(Asset.generation_mode).all()
        
        return {
            "total_assets": total_assets,
            "assets_with_files": assets_with_files,
            "total_file_size_mb": round(total_file_size / 1024 / 1024, 2),
            "provider_distribution": {stat[0]: stat[1] for stat in provider_stats},
            "mode_distribution": {stat[0]: stat[1] for stat in mode_stats},
            "file_coverage_percent": round((assets_with_files / total_assets * 100) if total_assets > 0 else 0, 1)
        }
