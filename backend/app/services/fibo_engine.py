"""FIBO Generation Engine implementing Generate, Refine, and Inspire modes."""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from app.services.bria_client import BriaClient, ImageResult, BriaAPIError
from app.services.vlm_translator import VLMTranslator, VLMTranslatorError
from app.services.schema_validator import FIBOAdvancedRequest, ValidationError
from app.services.matrix_engine import MatrixEngine, MatrixResult

logger = logging.getLogger(__name__)


class GenerationMode(Enum):
    """FIBO generation modes."""
    GENERATE = "generate"  # Natural language → JSON → Image
    REFINE = "refine"      # Modify specific attributes only
    INSPIRE = "inspire"    # Generate variations from image


class FIBOEngineError(Exception):
    """Exception raised when FIBO engine operations fail."""
    
    def __init__(self, message: str, mode: Optional[GenerationMode] = None):
        self.message = message
        self.mode = mode
        super().__init__(message)


@dataclass
class GenerateRequest:
    """Request for Generate mode."""
    natural_prompt: str
    mode: GenerationMode = GenerationMode.GENERATE
    seed: Optional[int] = None
    aspect_ratio: str = "1:1"


@dataclass  
class RefineRequest:
    """Request for Refine mode."""
    base_json: Dict[str, Any]  # Previous generation JSON
    modification: str          # What to change (e.g., "make it gold")
    mode: GenerationMode = GenerationMode.REFINE
    seed: Optional[int] = None
    aspect_ratio: str = "1:1"


@dataclass
class InspireRequest:
    """Request for Inspire mode."""
    reference_json: Dict[str, Any]  # Reference style JSON
    subject_change: str             # New subject (e.g., "sports car")
    mode: GenerationMode = GenerationMode.INSPIRE
    seed: Optional[int] = None
    aspect_ratio: str = "1:1"


@dataclass
class FIBOGenerationResult:
    """Result from FIBO generation."""
    mode: GenerationMode
    images: List[ImageResult]
    request_json: Dict[str, Any]
    structured_prompt: str
    metadata: Dict[str, Any]
    created_at: datetime


class FIBOEngine:
    """Advanced FIBO generation engine with three modes."""

    def __init__(self, bria_client: Optional[BriaClient] = None, 
                 vlm_translator: Optional[VLMTranslator] = None):
        """Initialize FIBO engine.
        
        Args:
            bria_client: Bria API client instance.
            vlm_translator: VLM translator instance.
        """
        # Initialize clients with proper error handling
        try:
            self.bria_client = bria_client or BriaClient()
            logger.info("✅ BRIA client initialized")
        except Exception as e:
            logger.warning(f"⚠️ BRIA client initialization failed: {e}")
            self.bria_client = None
            
        try:
            self.vlm_translator = vlm_translator or VLMTranslator()
            logger.info("✅ VLM translator initialized")
        except VLMTranslatorError as e:
            logger.warning(f"⚠️ VLM translator initialization failed: {e}")
            self.vlm_translator = None
            
        self.matrix_engine = MatrixEngine(bria_client=self.bria_client)
        
        # Check what features are available
        self.features_available = {
            "image_generation": self.bria_client is not None,
            "vlm_translation": self.vlm_translator is not None,
            "matrix_generation": self.bria_client is not None,
        }
        
        logger.info(f"FIBO Engine features: {self.features_available}")

    # ==================== GENERATE MODE ====================

    def generate_mode(self, request: GenerateRequest) -> FIBOGenerationResult:
        """Generate mode: Natural language → JSON → Image.
        
        This is FIBO's primary mode for expanding short prompts into 
        detailed professional parameters.

        Args:
            request: GenerateRequest with natural language prompt.

        Returns:
            FIBOGenerationResult with generated images.

        Raises:
            FIBOEngineError: If generation fails.
        """
        logger.info(f"Generate mode: {request.natural_prompt}")
        
        # Check feature availability
        if not self.features_available["vlm_translation"]:
            raise FIBOEngineError(
                "VLM translation not available. Please configure OPENAI_API_KEY.",
                GenerationMode.GENERATE
            )
        
        if not self.features_available["image_generation"]:
            raise FIBOEngineError(
                "Image generation not available. Please configure BRIA_API_KEY.",
                GenerationMode.GENERATE
            )
        
        try:
            # Step 1: Translate natural language to advanced JSON
            advanced_request = self.vlm_translator.translate_to_advanced_request(
                request.natural_prompt
            )
            
            # Set aspect ratio and seed from request
            advanced_request.aspect_ratio = request.aspect_ratio
            if request.seed:
                advanced_request.seed = request.seed
            
            # Step 2: Generate image using advanced parameters
            images = self.bria_client.generate_advanced(advanced_request)
            
            # Step 3: Create result
            return FIBOGenerationResult(
                mode=GenerationMode.GENERATE,
                images=images,
                request_json=advanced_request.dict(),
                structured_prompt=advanced_request.to_structured_prompt(),
                metadata={
                    "original_prompt": request.natural_prompt,
                    "translation_method": "vlm_gpt4",
                    "parameter_count": len(advanced_request.dict())
                },
                created_at=datetime.utcnow()
            )

        except VLMTranslatorError as e:
            logger.error(f"VLM translation failed: {e}")
            raise FIBOEngineError(
                f"Failed to translate prompt: {e.message}", 
                GenerationMode.GENERATE
            )
            
        except BriaAPIError as e:
            logger.error(f"Bria generation failed: {e}")
            raise FIBOEngineError(
                f"Failed to generate image: {e.message}",
                GenerationMode.GENERATE
            )

    def generate_matrix_mode(self, natural_prompt: str, seed: Optional[int] = None) -> MatrixResult:
        """Generate 3x3 matrix using Generate mode.
        
        Args:
            natural_prompt: Natural language description.
            seed: Optional seed for deterministic generation.

        Returns:
            MatrixResult with 9 cells using advanced parameters.

        Raises:
            FIBOEngineError: If matrix generation fails.
        """
        logger.info(f"Matrix Generate mode: {natural_prompt}")
        
        try:
            # Translate to advanced request
            base_request = self.vlm_translator.translate_to_advanced_request(natural_prompt)
            if seed:
                base_request.seed = seed
            
            # Use subject for matrix generation
            return self.matrix_engine.generate_advanced_matrix(
                base_request.subject, 
                seed or base_request.seed,
                base_camera_settings=base_request.camera,
                base_lighting_settings=base_request.lighting
            )
            
        except Exception as e:
            logger.error(f"Matrix generation failed: {e}")
            raise FIBOEngineError(f"Matrix generation failed: {e}")

    # ==================== REFINE MODE ====================

    def refine_mode(self, request: RefineRequest) -> FIBOGenerationResult:
        """Refine mode: Modify specific attributes without breaking scene.
        
        This is FIBO's disentangled control - change one thing while
        keeping everything else identical.

        Args:
            request: RefineRequest with base JSON and modification.

        Returns:
            FIBOGenerationResult with refined image.

        Raises:
            FIBOEngineError: If refinement fails.
        """
        logger.info(f"Refine mode: {request.modification}")
        
        try:
            # Step 1: Parse base JSON into FIBOAdvancedRequest
            base_request = FIBOAdvancedRequest(**request.base_json)
            
            # Step 2: Create modification prompt for VLM
            current_description = f"""
            Current settings:
            Subject: {base_request.subject}
            Camera: {base_request.camera.angle}, {base_request.camera.focal_length}
            Lighting: {base_request.lighting.setup}, {base_request.lighting.temperature}
            Mood: {base_request.mood}
            Background: {base_request.background}
            """
            
            modification_prompt = f"""
            {current_description}
            
            Modification request: {request.modification}
            
            Keep all other parameters identical, only change what's specifically requested.
            """
            
            # Step 3: Get refined parameters
            refined_request = self.vlm_translator.translate_to_advanced_request(
                modification_prompt
            )
            
            # Step 4: Apply selective modifications
            refined_request = self._apply_selective_refinement(
                base_request, refined_request, request.modification
            )
            
            # Step 5: Keep seed and aspect ratio from original
            refined_request.seed = request.seed or base_request.seed
            refined_request.aspect_ratio = request.aspect_ratio
            
            # Step 6: Generate refined image
            images = self.bria_client.generate_advanced(refined_request)
            
            return FIBOGenerationResult(
                mode=GenerationMode.REFINE,
                images=images,
                request_json=refined_request.dict(),
                structured_prompt=refined_request.to_structured_prompt(),
                metadata={
                    "original_json": request.base_json,
                    "modification": request.modification,
                    "refinement_type": "disentangled_selective"
                },
                created_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            raise FIBOEngineError(f"Refinement failed: {e}", GenerationMode.REFINE)

    def _apply_selective_refinement(
        self, 
        base: FIBOAdvancedRequest, 
        refined: FIBOAdvancedRequest, 
        modification: str
    ) -> FIBOAdvancedRequest:
        """Apply selective refinement based on modification type.
        
        Args:
            base: Original request.
            refined: VLM-suggested refinement.
            modification: What was requested to change.

        Returns:
            Selectively refined request.
        """
        # Determine what should change based on modification keywords
        modification_lower = modification.lower()
        
        # Start with base and selectively apply changes
        result = FIBOAdvancedRequest(**base.dict())
        
        # Lighting modifications
        if any(word in modification_lower for word in ['lighting', 'light', 'dramatic', 'soft', 'bright']):
            result.lighting = refined.lighting
            logger.debug("Applied lighting refinement")
        
        # Color modifications  
        if any(word in modification_lower for word in ['color', 'gold', 'silver', 'red', 'blue', 'warm', 'cool']):
            result.color_palette = refined.color_palette
            logger.debug("Applied color refinement")
        
        # Camera modifications
        if any(word in modification_lower for word in ['angle', 'camera', 'view', 'perspective', 'close', 'wide']):
            result.camera = refined.camera
            logger.debug("Applied camera refinement")
        
        # Background modifications
        if any(word in modification_lower for word in ['background', 'backdrop', 'surface']):
            result.background = refined.background
            logger.debug("Applied background refinement")
        
        # Mood modifications
        if any(word in modification_lower for word in ['mood', 'style', 'elegant', 'modern', 'vintage']):
            result.mood = refined.mood
            result.style = refined.style
            logger.debug("Applied mood/style refinement")
        
        return result

    # ==================== INSPIRE MODE ====================

    def inspire_mode(self, request: InspireRequest) -> List[FIBOGenerationResult]:
        """Inspire mode: Generate variations maintaining style consistency.
        
        Takes a reference style and applies it to a new subject.

        Args:
            request: InspireRequest with reference JSON and new subject.

        Returns:
            List of FIBOGenerationResult with style variations.

        Raises:
            FIBOEngineError: If inspiration fails.
        """
        logger.info(f"Inspire mode: {request.subject_change}")
        
        try:
            # Parse reference JSON
            reference_request = FIBOAdvancedRequest(**request.reference_json)
            
            # Create inspiration prompt preserving style
            inspiration_prompt = f"""
            Create a {request.subject_change} using these exact style parameters:
            Camera angle: {reference_request.camera.angle}
            Focal length: {reference_request.camera.focal_length}
            Lighting: {reference_request.lighting.setup}
            Lighting temperature: {reference_request.lighting.temperature}
            Background: {reference_request.background}
            Mood: {reference_request.mood}
            Style: {reference_request.style}
            Color palette: {', '.join(reference_request.color_palette.primary_colors)}
            """
            
            # Generate base inspired version
            base_inspired = self.vlm_translator.translate_to_advanced_request(inspiration_prompt)
            base_inspired.seed = request.seed
            base_inspired.aspect_ratio = request.aspect_ratio
            
            # Generate multiple variations
            variations = []
            
            # Variation 1: Direct style transfer
            images1 = self.bria_client.generate_advanced(base_inspired)
            variations.append(FIBOGenerationResult(
                mode=GenerationMode.INSPIRE,
                images=images1,
                request_json=base_inspired.dict(),
                structured_prompt=base_inspired.to_structured_prompt(),
                metadata={
                    "reference_json": request.reference_json,
                    "subject_change": request.subject_change,
                    "variation_type": "direct_style_transfer"
                },
                created_at=datetime.utcnow()
            ))
            
            # Variation 2: Style with lighting adaptation
            adapted_lighting = FIBOAdvancedRequest(**base_inspired.dict())
            adapted_lighting.lighting.intensity = "high" if reference_request.lighting.intensity == "medium" else "medium"
            
            images2 = self.bria_client.generate_advanced(adapted_lighting)
            variations.append(FIBOGenerationResult(
                mode=GenerationMode.INSPIRE,
                images=images2,
                request_json=adapted_lighting.dict(),
                structured_prompt=adapted_lighting.to_structured_prompt(),
                metadata={
                    "reference_json": request.reference_json,
                    "subject_change": request.subject_change,
                    "variation_type": "adapted_lighting"
                },
                created_at=datetime.utcnow()
            ))
            
            return variations

        except Exception as e:
            logger.error(f"Inspiration failed: {e}")
            raise FIBOEngineError(f"Inspiration failed: {e}", GenerationMode.INSPIRE)

    # ==================== UTILITY METHODS ====================

    def get_supported_modes(self) -> List[str]:
        """Get list of supported generation modes."""
        return [mode.value for mode in GenerationMode]

    def validate_mode_request(self, mode: GenerationMode, data: Dict[str, Any]) -> bool:
        """Validate request data for specific mode.
        
        Args:
            mode: Generation mode.
            data: Request data.

        Returns:
            True if valid.

        Raises:
            FIBOEngineError: If validation fails.
        """
        if mode == GenerationMode.GENERATE:
            if "natural_prompt" not in data:
                raise FIBOEngineError("Generate mode requires 'natural_prompt'")
                
        elif mode == GenerationMode.REFINE:
            if "base_json" not in data or "modification" not in data:
                raise FIBOEngineError("Refine mode requires 'base_json' and 'modification'")
                
        elif mode == GenerationMode.INSPIRE:
            if "reference_json" not in data or "subject_change" not in data:
                raise FIBOEngineError("Inspire mode requires 'reference_json' and 'subject_change'")
        
        return True

    def get_engine_status(self) -> Dict[str, Any]:
        """Get engine status and capabilities.
        
        Returns:
            Dictionary with engine status information.
        """
        return {
            "engine_name": "FIBO Advanced Generation Engine",
            "version": "2.0",
            "features_available": self.features_available,
            "supported_modes": self.get_supported_modes(),
            "api_status": {
                "bria": "configured" if self.bria_client else "missing_api_key",
                "openai": "configured" if self.vlm_translator else "missing_api_key"
            },
            "ready": all(self.features_available.values()),
            "missing_requirements": [
                feature for feature, available in self.features_available.items() 
                if not available
            ]
        }