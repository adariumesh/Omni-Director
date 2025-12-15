"""API routes for image generation."""

import logging
from typing import Annotated, Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.repositories.asset_repository import AssetRepository
from app.services.bria_client import BriaAPIError, BriaClient
from app.services.matrix_engine import MatrixEngine
from app.services.fibo_engine import FIBOEngine, GenerateRequest, RefineRequest, InspireRequest, GenerationMode
from app.services.schema_validator import (
    VALID_ASPECT_RATIOS,
    SchemaValidator,
    ValidationError,
    FIBOAdvancedRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1", 
    tags=["generation"],
    responses={
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    }
)


# ==================== Request/Response Models ====================


class GenerateRequest(BaseModel):
    """Request for single image generation."""

    prompt: str = Field(..., min_length=1, max_length=1000)
    seed: int | None = Field(default=None, ge=0, le=2147483647)
    aspect_ratio: str = Field(default="1:1")
    project_id: str | None = Field(default=None)

    model_config = {"extra": "forbid"}


class GenerateResponse(BaseModel):
    """Response for single image generation."""

    success: bool
    image_url: str
    seed: int
    prompt: str
    aspect_ratio: str
    asset_id: str | None = None


class MatrixRequest(BaseModel):
    """Request for 3x3 matrix generation."""

    base_prompt: str = Field(..., min_length=1, max_length=1000)
    seed: int | None = Field(default=None, ge=0, le=2147483647)
    aspect_ratio: str = Field(default="1:1")
    project_id: str | None = Field(default=None)
    camera_angles: list[str] | None = Field(default=None)
    lighting_styles: list[str] | None = Field(default=None)

    model_config = {"extra": "forbid"}


class MatrixCellResponse(BaseModel):
    """Response for a single matrix cell."""

    position: str
    row: int
    col: int
    prompt: str
    angle: str
    lighting: str
    image_url: str | None
    success: bool
    asset_id: str | None = None


class MatrixResponse(BaseModel):
    """Response for matrix generation."""

    success: bool
    seed: int
    base_prompt: str
    aspect_ratio: str
    cells: list[MatrixCellResponse]
    successful_count: int
    total_count: int = 9


class MutateRequest(BaseModel):
    """Request for cell mutation."""

    asset_id: str = Field(...)
    mutations: dict[str, str] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    api_configured: bool
    database_connected: bool


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""
    
    overall_status: str
    ready_for_production: bool
    services: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]
    features_available: Dict[str, bool]


# ==================== Dependencies ====================


def get_bria_client() -> BriaClient:
    """Get Bria client instance."""
    return BriaClient()


def get_validator() -> SchemaValidator:
    """Get schema validator instance."""
    return SchemaValidator()


def get_repository(db: Session = Depends(get_db)) -> AssetRepository:
    """Get asset repository instance."""
    return AssetRepository(db)


# ==================== Routes ====================


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: Session = Depends(get_db),
) -> HealthResponse:
    """Check API health status with comprehensive environment validation."""
    from app.services.environment_validator import EnvironmentValidator
    
    validator = EnvironmentValidator()
    env_status = validator.validate_environment()
    
    # Map to simple response format for compatibility
    api_configured = any(
        check.name in ["BRIA_API", "OpenAI_API"] and check.status.value == "available" 
        for check in env_status.services
    )
    
    database_connected = any(
        check.name == "Database" and check.status.value == "available"
        for check in env_status.services
    )
    
    # Determine overall status
    if env_status.overall_status.value == "available":
        status = "healthy"
    elif env_status.overall_status.value == "degraded":
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        api_configured=api_configured,
        database_connected=database_connected,
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Get detailed environment status and service availability."""
    from app.services.environment_validator import EnvironmentValidator
    
    validator = EnvironmentValidator()
    env_status = validator.validate_environment()
    
    # Check feature availability
    features = {}
    for feature in ["image_generation", "vlm_translation", "export", "brand_protection"]:
        ready, _ = validator.is_ready_for_feature(feature)
        features[feature] = ready
    
    # Format service information
    services = []
    for check in env_status.services:
        services.append({
            "name": check.name,
            "status": check.status.value,
            "message": check.message,
            "critical": check.critical,
            "details": check.details or {}
        })
    
    return DetailedHealthResponse(
        overall_status=env_status.overall_status.value,
        ready_for_production=env_status.ready_for_production,
        services=services,
        warnings=env_status.warnings,
        errors=env_status.errors,
        features_available=features
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate_image(
    request: GenerateRequest,
    client: Annotated[BriaClient, Depends(get_bria_client)],
    validator: Annotated[SchemaValidator, Depends(get_validator)],
    repository: Annotated[AssetRepository, Depends(get_repository)],
) -> GenerateResponse:
    """Generate a single image.

    Args:
        request: Generation request parameters.
        client: Bria API client.
        validator: Schema validator.
        repository: Asset repository.

    Returns:
        GenerateResponse with image URL and metadata.

    Raises:
        HTTPException: If generation fails.
    """
    # Validate request
    try:
        validated = validator.validate_bria_request(request.model_dump())
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Generate image
    try:
        result = client.generate_with_locked_seed(
            prompt=validated.prompt,
            seed=validated.seed or 0,
            aspect_ratio=validated.aspect_ratio,
        )
    except BriaAPIError as e:
        logger.error(f"Bria API error: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )

    # Save to database if project provided
    asset_id = None
    if request.project_id:
        try:
            asset = repository.create_asset(
                project_id=request.project_id,
                prompt=result.prompt,
                seed=result.seed,
                aspect_ratio=result.aspect_ratio,
                image_url=result.url,
                image_path=result.local_path,
                file_id=result.file_id,
                thumbnail_path=result.thumbnail_path,
                generation_mode="simple",
                api_provider="bria",
                json_payload=request.model_dump(),
            )
            asset_id = asset.id
        except Exception as e:
            logger.error(f"Failed to save asset: {e}")

    return GenerateResponse(
        success=True,
        image_url=result.url,
        seed=result.seed,
        prompt=result.prompt,
        aspect_ratio=result.aspect_ratio,
        asset_id=asset_id,
    )


@router.post("/matrix", response_model=MatrixResponse)
async def generate_matrix(
    request: MatrixRequest,
    client: Annotated[BriaClient, Depends(get_bria_client)],
    repository: Annotated[AssetRepository, Depends(get_repository)],
) -> MatrixResponse:
    """Generate a 3x3 deterministic matrix.

    Args:
        request: Matrix request parameters.
        client: Bria API client.
        repository: Asset repository.

    Returns:
        MatrixResponse with all 9 cells.

    Raises:
        HTTPException: If generation fails.
    """
    # Build matrix engine with custom axes if provided
    engine = MatrixEngine(
        bria_client=client,
        camera_angles=request.camera_angles,
        lighting_styles=request.lighting_styles,
    )

    # Generate matrix
    try:
        result = engine.generate_matrix(
            base_prompt=request.base_prompt,
            seed=request.seed,
            aspect_ratio=request.aspect_ratio,
        )
    except Exception as e:
        logger.error(f"Matrix generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # Build cell responses and save to database
    cells: list[MatrixCellResponse] = []

    for cell in result.cells:
        asset_id = None

        # Save to database if project provided and image generated
        if request.project_id and cell.image_result:
            try:
                asset = repository.create_asset(
                    project_id=request.project_id,
                    prompt=cell.prompt,
                    seed=result.seed,
                    aspect_ratio=result.aspect_ratio,
                    image_url=cell.image_result.url,
                    matrix_position=cell.position,
                    json_payload={
                        "base_prompt": request.base_prompt,
                        "angle": cell.angle,
                        "lighting": cell.lighting,
                        "seed": result.seed,
                    },
                )
                asset_id = asset.id
            except Exception as e:
                logger.error(f"Failed to save cell asset: {e}")

        cells.append(
            MatrixCellResponse(
                position=cell.position,
                row=cell.row,
                col=cell.col,
                prompt=cell.prompt,
                angle=cell.angle,
                lighting=cell.lighting,
                image_url=cell.image_result.url if cell.image_result else None,
                success=cell.image_result is not None,
                asset_id=asset_id,
            )
        )

    return MatrixResponse(
        success=result.successful_count > 0,
        seed=result.seed,
        base_prompt=result.base_prompt,
        aspect_ratio=result.aspect_ratio,
        cells=cells,
        successful_count=result.successful_count,
    )


@router.post("/mutate", response_model=GenerateResponse)
async def mutate_cell(
    request: MutateRequest,
    client: Annotated[BriaClient, Depends(get_bria_client)],
    repository: Annotated[AssetRepository, Depends(get_repository)],
) -> GenerateResponse:
    """Mutate a cell with new parameters.

    Args:
        request: Mutation request.
        client: Bria API client.
        repository: Asset repository.

    Returns:
        GenerateResponse with mutated image.

    Raises:
        HTTPException: If asset not found or mutation fails.
    """
    # Get original asset
    asset = repository.get_asset(request.asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset not found: {request.asset_id}",
        )

    # Get original JSON payload
    payload = repository.get_json_payload(request.asset_id)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset has no JSON payload",
        )

    # Build mutated prompt
    base_prompt = payload.get("base_prompt", asset.prompt.rsplit(",", 3)[0])
    angle = request.mutations.get("angle", payload.get("angle", "front view"))
    lighting = request.mutations.get("lighting", payload.get("lighting", "studio lighting"))

    mutated_prompt = f"{base_prompt}, {angle}, {lighting}, professional photography"

    # Generate with mutations
    try:
        result = client.generate_with_locked_seed(
            prompt=mutated_prompt,
            seed=asset.seed,
            aspect_ratio=asset.aspect_ratio,
        )
    except BriaAPIError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )

    # Save mutated asset with parent reference
    new_asset = repository.create_asset(
        project_id=asset.project_id,
        parent_id=asset.id,
        prompt=result.prompt,
        seed=result.seed,
        aspect_ratio=result.aspect_ratio,
        image_url=result.url,
        json_payload={
            "base_prompt": base_prompt,
            "angle": angle,
            "lighting": lighting,
            "seed": asset.seed,
            "mutations": request.mutations,
        },
    )

    return GenerateResponse(
        success=True,
        image_url=result.url,
        seed=result.seed,
        prompt=result.prompt,
        aspect_ratio=result.aspect_ratio,
        asset_id=new_asset.id,
    )


@router.get("/aspect-ratios")
async def get_aspect_ratios() -> dict[str, list[str]]:
    """Get list of valid aspect ratios."""
    return {"aspect_ratios": VALID_ASPECT_RATIOS}


# ==================== ADVANCED FIBO ENDPOINTS ====================

class FIBOGenerateRequest(BaseModel):
    """Request for FIBO Generate mode."""
    natural_prompt: str = Field(..., min_length=1, max_length=500, description="Natural language description")
    seed: int | None = Field(None, description="Optional seed for deterministic generation")
    aspect_ratio: str = Field("1:1", description="Image aspect ratio")
    project_id: str | None = Field(None, description="Optional project ID")


class FIBORefineRequest(BaseModel):
    """Request for FIBO Refine mode."""
    asset_id: str = Field(..., description="ID of asset to refine")
    modification: str = Field(..., min_length=1, max_length=200, description="What to change")
    project_id: str | None = Field(None, description="Optional project ID")


class FIBOInspireRequest(BaseModel):
    """Request for FIBO Inspire mode."""
    reference_asset_id: str = Field(..., description="Reference asset for style")
    subject_change: str = Field(..., min_length=1, max_length=200, description="New subject")
    seed: int | None = Field(None, description="Optional seed")
    aspect_ratio: str = Field("1:1", description="Image aspect ratio") 
    project_id: str | None = Field(None, description="Optional project ID")


class FIBOAdvancedResponse(BaseModel):
    """Response for advanced FIBO generation."""
    success: bool
    mode: str
    images: list[dict]
    request_json: dict
    structured_prompt: str
    metadata: dict
    asset_ids: list[str] = Field(default_factory=list)


def get_fibo_engine() -> FIBOEngine:
    """Get FIBO engine instance."""
    try:
        return FIBOEngine()
    except Exception as e:
        # For demo/testing purposes, create a mock engine
        logger.warning(f"Cannot create real FIBO engine: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"FIBO engine unavailable: {str(e)}. Please configure API keys."
        )


@router.post("/fibo/generate", response_model=FIBOAdvancedResponse)
async def fibo_generate_mode(
    request: FIBOGenerateRequest,
    fibo_engine: Annotated[FIBOEngine, Depends(get_fibo_engine)],
    repository: Annotated[AssetRepository, Depends(get_repository)],
) -> FIBOAdvancedResponse:
    """FIBO Generate Mode: Natural language → Advanced JSON → Image.
    
    Expands natural language prompts into professional photography parameters
    using VLM translation and structured generation.
    """
    try:
        # Create generation request
        gen_request = GenerateRequest(
            natural_prompt=request.natural_prompt,
            seed=request.seed,
            aspect_ratio=request.aspect_ratio
        )
        
        # Generate using FIBO engine
        result = fibo_engine.generate_mode(gen_request)
        
        # Save to database if project provided
        asset_ids = []
        if request.project_id:
            for image in result.images:
                try:
                    asset = repository.create_asset(
                        project_id=request.project_id,
                        prompt=result.structured_prompt,
                        seed=image.seed,
                        aspect_ratio=image.aspect_ratio,
                        image_url=image.url,
                        image_path=image.local_path,
                        file_id=image.file_id,
                        thumbnail_path=image.thumbnail_path,
                        generation_mode="generate",
                        api_provider="bria",
                        json_payload=result.request_json,
                    )
                    asset_ids.append(asset.id)
                except Exception as e:
                    logger.error(f"Failed to save FIBO asset: {e}")
        
        # Format response
        return FIBOAdvancedResponse(
            success=True,
            mode=result.mode.value,
            images=[{
                "url": img.url,
                "seed": img.seed,
                "created_at": img.created_at.isoformat()
            } for img in result.images],
            request_json=result.request_json,
            structured_prompt=result.structured_prompt,
            metadata=result.metadata,
            asset_ids=asset_ids
        )
        
    except Exception as e:
        logger.error(f"FIBO Generate mode failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )


@router.post("/fibo/refine", response_model=FIBOAdvancedResponse)
async def fibo_refine_mode(
    request: FIBORefineRequest,
    fibo_engine: Annotated[FIBOEngine, Depends(get_fibo_engine)],
    repository: Annotated[AssetRepository, Depends(get_repository)],
) -> FIBOAdvancedResponse:
    """FIBO Refine Mode: Modify specific attributes without breaking scene.
    
    Uses disentangled control to change only requested attributes while
    maintaining consistency in other parameters.
    """
    try:
        # Get base asset
        base_asset = repository.get_asset(request.asset_id)
        if not base_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base asset not found"
            )
        
        # Parse base JSON payload
        if not base_asset.json_payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Base asset has no JSON parameters"
            )
        
        import json
        base_json = json.loads(base_asset.json_payload)
        
        # Create refinement request
        refine_request = RefineRequest(
            base_json=base_json,
            modification=request.modification,
            seed=base_asset.seed
        )
        
        # Refine using FIBO engine
        result = fibo_engine.refine_mode(refine_request)
        
        # Save refined asset
        asset_ids = []
        if request.project_id:
            for image in result.images:
                try:
                    asset = repository.create_asset(
                        project_id=request.project_id,
                        parent_id=base_asset.id,  # Link to parent
                        prompt=result.structured_prompt,
                        seed=image.seed,
                        aspect_ratio=image.aspect_ratio,
                        image_url=image.url,
                        json_payload=result.request_json,
                    )
                    asset_ids.append(asset.id)
                except Exception as e:
                    logger.error(f"Failed to save refined asset: {e}")
        
        return FIBOAdvancedResponse(
            success=True,
            mode=result.mode.value,
            images=[{
                "url": img.url,
                "seed": img.seed,
                "created_at": img.created_at.isoformat()
            } for img in result.images],
            request_json=result.request_json,
            structured_prompt=result.structured_prompt,
            metadata=result.metadata,
            asset_ids=asset_ids
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FIBO Refine mode failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refinement failed: {str(e)}"
        )


@router.post("/fibo/inspire", response_model=list[FIBOAdvancedResponse])
async def fibo_inspire_mode(
    request: FIBOInspireRequest,
    fibo_engine: Annotated[FIBOEngine, Depends(get_fibo_engine)],
    repository: Annotated[AssetRepository, Depends(get_repository)],
) -> list[FIBOAdvancedResponse]:
    """FIBO Inspire Mode: Generate variations maintaining style consistency.
    
    Takes a reference asset's style and applies it to a new subject,
    creating multiple variations with consistent aesthetic.
    """
    try:
        # Get reference asset
        reference_asset = repository.get_asset(request.reference_asset_id)
        if not reference_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference asset not found"
            )
        
        # Parse reference JSON
        if not reference_asset.json_payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference asset has no style parameters"
            )
        
        import json
        reference_json = json.loads(reference_asset.json_payload)
        
        # Create inspiration request
        inspire_request = InspireRequest(
            reference_json=reference_json,
            subject_change=request.subject_change,
            seed=request.seed,
            aspect_ratio=request.aspect_ratio
        )
        
        # Generate inspired variations
        results = fibo_engine.inspire_mode(inspire_request)
        
        # Format responses
        responses = []
        for result in results:
            asset_ids = []
            if request.project_id:
                for image in result.images:
                    try:
                        asset = repository.create_asset(
                            project_id=request.project_id,
                            prompt=result.structured_prompt,
                            seed=image.seed,
                            aspect_ratio=image.aspect_ratio,
                            image_url=image.url,
                            json_payload=result.request_json,
                        )
                        asset_ids.append(asset.id)
                    except Exception as e:
                        logger.error(f"Failed to save inspired asset: {e}")
            
            responses.append(FIBOAdvancedResponse(
                success=True,
                mode=result.mode.value,
                images=[{
                    "url": img.url,
                    "seed": img.seed,
                    "created_at": img.created_at.isoformat()
                } for img in result.images],
                request_json=result.request_json,
                structured_prompt=result.structured_prompt,
                metadata=result.metadata,
                asset_ids=asset_ids
            ))
        
        return responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FIBO Inspire mode failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inspiration failed: {str(e)}"
        )


@router.get("/fibo/modes")
async def get_fibo_modes() -> dict[str, Any]:
    """Get available FIBO generation modes."""
    return {
        "modes": [mode.value for mode in GenerationMode],
        "descriptions": {
            "generate": "Natural language → Advanced JSON → Image",
            "refine": "Modify specific attributes without breaking scene", 
            "inspire": "Generate variations maintaining style consistency"
        },
        "status": "Available for configuration"
    }


@router.get("/fibo/status")
async def get_fibo_engine_status() -> dict[str, Any]:
    """Get FIBO engine status and capabilities.
    
    Returns detailed information about engine availability,
    API configuration, and feature readiness.
    """
    try:
        from app.services.fibo_engine import FIBOEngine
        
        # Try to initialize engine to check status
        engine = FIBOEngine()
        status = engine.get_engine_status()
        
        return {
            "success": True,
            "engine_status": status,
            "message": "Engine ready" if status["ready"] else f"Missing: {', '.join(status['missing_requirements'])}"
        }
        
    except Exception as e:
        logger.error(f"FIBO engine status check failed: {e}")
        return {
            "success": False,
            "engine_status": {
                "engine_name": "FIBO Engine",
                "ready": False,
                "error": str(e)
            },
            "message": f"Engine unavailable: {str(e)}"
        }


@router.post("/bria/research")
async def research_bria_api() -> dict[str, Any]:
    """Research and document BRIA API capabilities.
    
    Tests available endpoints, parameters, and limits to generate
    proper integration documentation. Requires valid BRIA API key.
    
    Returns:
        Research documentation or requirements if API key missing.
    """
    from app.services.bria_api_research import research_and_document_bria_api
    
    try:
        documentation = research_and_document_bria_api()
        
        # Check if documentation is just the "API key required" message
        if "API Key Required" in documentation:
            return {
                "success": False,
                "message": "BRIA API key required for research",
                "documentation": documentation,
                "next_steps": [
                    "Set BRIA_API_KEY environment variable",
                    "Restart backend server", 
                    "Call this endpoint again"
                ]
            }
        
        return {
            "success": True,
            "message": "BRIA API research completed",
            "documentation": documentation,
            "research_file": "./research/bria_api_capabilities.json"
        }
        
    except Exception as e:
        logger.error(f"BRIA API research failed: {e}")
        return {
            "success": False,
            "message": f"Research failed: {str(e)}",
            "documentation": "",
            "error": str(e)
        }


@router.post("/fibo/advanced", response_model=FIBOAdvancedResponse)
async def fibo_advanced_generation(
    request: FIBOAdvancedRequest,
    client: Annotated[BriaClient, Depends(get_bria_client)],
    repository: Annotated[AssetRepository, Depends(get_repository)],
) -> FIBOAdvancedResponse:
    """Direct advanced FIBO generation with full parameter control.
    
    Accepts complete FIBOAdvancedRequest JSON with all professional parameters
    for maximum control over generation.
    """
    try:
        # Generate using advanced parameters
        results = client.generate_advanced(request)
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No images generated"
            )
        
        # Format response
        return FIBOAdvancedResponse(
            success=True,
            mode="advanced_direct",
            images=[{
                "url": img.url,
                "seed": img.seed,
                "created_at": img.created_at.isoformat()
            } for img in results],
            request_json=request.dict(),
            structured_prompt=request.to_structured_prompt(),
            metadata={
                "generation_type": "advanced_direct",
                "parameter_count": len(request.dict())
            },
        )
        
    except BriaAPIError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Advanced FIBO generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Advanced generation failed: {str(e)}"
        )
