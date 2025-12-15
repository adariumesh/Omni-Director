"""SQLAlchemy database models for FIBO Omni-Director."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

from ..config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class Project(Base):
    """Project model representing a creative campaign."""

    __tablename__ = "projects"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: str = Column(String(255), nullable=False)
    brand_logo_path: str | None = Column(String(500), nullable=True)
    negative_prompt: str | None = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """Return string representation of Project."""
        return f"<Project(id={self.id}, name={self.name})>"


class Asset(Base):
    """Asset model representing a generated image."""

    __tablename__ = "assets"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: str = Column(String(36), ForeignKey("projects.id"), nullable=False)
    parent_id: str | None = Column(String(36), ForeignKey("assets.id"), nullable=True)
    prompt: str = Column(Text, nullable=False)
    seed: int = Column(Integer, nullable=False)
    aspect_ratio: str = Column(String(10), nullable=False, default="1:1")
    image_url: str | None = Column(String(500), nullable=True)
    image_path: str | None = Column(String(500), nullable=True)
    json_payload: str = Column(Text, nullable=False)
    matrix_position: str | None = Column(String(10), nullable=True)
    
    # File storage fields
    file_id: str | None = Column(String(100), nullable=True, index=True)
    thumbnail_path: str | None = Column(String(500), nullable=True)
    file_size: int | None = Column(Integer, nullable=True)
    content_type: str | None = Column(String(100), nullable=True)
    checksum: str | None = Column(String(64), nullable=True)
    
    # Generation metadata
    generation_mode: str | None = Column(String(20), nullable=True)  # generate, refine, inspire
    generation_time: float | None = Column(Integer, nullable=True)  # milliseconds
    api_provider: str | None = Column(String(50), nullable=True)  # bria, fal, replicate
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="assets")
    parent = relationship("Asset", remote_side=[id], backref="children")

    def __repr__(self) -> str:
        """Return string representation of Asset."""
        return f"<Asset(id={self.id}, seed={self.seed}, position={self.matrix_position})>"


# Database engine and session factory
engine = create_engine(settings.database_url, echo=settings.debug)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database by creating all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session.

    Yields:
        Database session that auto-closes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
