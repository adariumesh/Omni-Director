"""Schema validation for API requests and responses."""

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised when validation fails."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        """Initialize ValidationError.

        Args:
            message: Main error message.
            errors: Optional list of specific validation errors.
        """
        self.message = message
        self.errors = errors or []
        super().__init__(message)


# Valid values for constrained fields
VALID_ASPECT_RATIOS = [
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
]

MAX_PROMPT_LENGTH = 2000  # Increased for structured prompts
MAX_SEED_VALUE = 2147483647

# FIBO Professional Parameters
VALID_CAMERA_ANGLES = [
    "front_view", "three_quarter_view", "side_view", "back_view", 
    "top_down", "low_angle", "high_angle", "eye_level"
]

VALID_FOCAL_LENGTHS = [
    "14mm", "24mm", "35mm", "50mm", "85mm", "105mm", "135mm", "200mm"
]

VALID_DEPTH_OF_FIELD = [
    "shallow", "medium", "deep", "hyperfocal"
]

VALID_LIGHTING_SETUPS = [
    "studio_three_point", "rembrandt", "split_lighting", "butterfly",
    "loop_lighting", "rim_lighting", "natural_window", "golden_hour",
    "blue_hour", "dramatic_side", "soft_diffused", "hard_directional"
]

VALID_LIGHTING_TEMPERATURES = [
    "tungsten_3200k", "daylight_5600k", "cloudy_6500k", "shade_7500k",
    "warm_2700k", "cool_8000k"
]

VALID_COMPOSITION_RULES = [
    "rule_of_thirds", "golden_ratio", "symmetrical", "asymmetrical",
    "leading_lines", "frame_in_frame", "fill_frame", "negative_space"
]

VALID_COLOR_TEMPERATURES = [
    "very_warm", "warm", "neutral", "cool", "very_cool"
]

VALID_COLOR_SATURATIONS = [
    "desaturated", "natural", "vibrant", "oversaturated"
]

VALID_MOODS = [
    "professional", "dramatic", "elegant", "modern", "vintage", 
    "minimalist", "luxury", "industrial", "organic", "futuristic"
]

VALID_BACKGROUNDS = [
    "white_seamless", "black_seamless", "gradient_neutral", "textured_wall",
    "wooden_surface", "marble_surface", "fabric_backdrop", "outdoor_natural",
    "studio_cyc", "transparent"
]


# Advanced FIBO Schemas
class CameraSettings(BaseModel):
    """Professional camera settings for FIBO."""
    angle: str = Field(default="three_quarter_view")
    focal_length: str = Field(default="85mm") 
    depth_of_field: str = Field(default="shallow")
    distance: str = Field(default="medium_shot")
    
    @field_validator("angle")
    @classmethod
    def validate_angle(cls, v: str) -> str:
        if v not in VALID_CAMERA_ANGLES:
            raise ValueError(f"Invalid camera angle: {v}")
        return v
    
    @field_validator("focal_length") 
    @classmethod
    def validate_focal_length(cls, v: str) -> str:
        if v not in VALID_FOCAL_LENGTHS:
            raise ValueError(f"Invalid focal length: {v}")
        return v
    
    @field_validator("depth_of_field")
    @classmethod
    def validate_dof(cls, v: str) -> str:
        if v not in VALID_DEPTH_OF_FIELD:
            raise ValueError(f"Invalid depth of field: {v}")
        return v

class LightingSettings(BaseModel):
    """Professional lighting settings for FIBO."""
    setup: str = Field(default="studio_three_point")
    temperature: str = Field(default="daylight_5600k")
    intensity: str = Field(default="medium")
    direction: str = Field(default="front_left_45")
    
    @field_validator("setup")
    @classmethod 
    def validate_setup(cls, v: str) -> str:
        if v not in VALID_LIGHTING_SETUPS:
            raise ValueError(f"Invalid lighting setup: {v}")
        return v
    
    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: str) -> str:
        if v not in VALID_LIGHTING_TEMPERATURES:
            raise ValueError(f"Invalid lighting temperature: {v}")
        return v

class CompositionSettings(BaseModel):
    """Professional composition settings for FIBO."""
    rule: str = Field(default="rule_of_thirds")
    balance: str = Field(default="asymmetrical") 
    negative_space: str = Field(default="minimal")
    
    @field_validator("rule")
    @classmethod
    def validate_rule(cls, v: str) -> str:
        if v not in VALID_COMPOSITION_RULES:
            raise ValueError(f"Invalid composition rule: {v}")
        return v

class ColorPalette(BaseModel):
    """Color palette settings for FIBO."""
    primary_colors: list[str] = Field(default=["neutral"])
    accent_colors: list[str] = Field(default=[])
    temperature: str = Field(default="neutral")
    saturation: str = Field(default="natural")
    
    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: str) -> str:
        if v not in VALID_COLOR_TEMPERATURES:
            raise ValueError(f"Invalid color temperature: {v}")
        return v
    
    @field_validator("saturation")
    @classmethod
    def validate_saturation(cls, v: str) -> str:
        if v not in VALID_COLOR_SATURATIONS:
            raise ValueError(f"Invalid saturation: {v}")
        return v

class FIBOAdvancedRequest(BaseModel):
    """Advanced FIBO request with professional parameters."""
    subject: str = Field(..., min_length=1, max_length=500)
    camera: CameraSettings = Field(default_factory=CameraSettings)
    lighting: LightingSettings = Field(default_factory=LightingSettings)
    composition: CompositionSettings = Field(default_factory=CompositionSettings)
    color_palette: ColorPalette = Field(default_factory=ColorPalette)
    background: str = Field(default="white_seamless")
    style: str = Field(default="professional_photography")
    mood: str = Field(default="professional")
    aspect_ratio: str = Field(default="1:1")
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED_VALUE)
    
    @field_validator("background")
    @classmethod
    def validate_background(cls, v: str) -> str:
        if v not in VALID_BACKGROUNDS:
            raise ValueError(f"Invalid background: {v}")
        return v
    
    @field_validator("mood")
    @classmethod  
    def validate_mood(cls, v: str) -> str:
        if v not in VALID_MOODS:
            raise ValueError(f"Invalid mood: {v}")
        return v
    
    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, v: str) -> str:
        if v not in VALID_ASPECT_RATIOS:
            raise ValueError(f"Invalid aspect ratio: {v}")
        return v
    
    def to_structured_prompt(self) -> str:
        """Convert to structured FIBO prompt."""
        prompt_parts = [
            self.subject,
            f"camera angle: {self.camera.angle}",
            f"focal length: {self.camera.focal_length}", 
            f"depth of field: {self.camera.depth_of_field}",
            f"lighting: {self.lighting.setup}",
            f"lighting temperature: {self.lighting.temperature}",
            f"composition: {self.composition.rule}",
            f"background: {self.background}",
            f"style: {self.style}",
            f"mood: {self.mood}",
            "professional photography, high quality, sharp focus"
        ]
        
        if self.color_palette.primary_colors:
            colors = ", ".join(self.color_palette.primary_colors)
            prompt_parts.append(f"color palette: {colors}")
        
        return ", ".join(prompt_parts)

class BriaRequestSchema(BaseModel):
    """Validated schema for Bria API requests."""

    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    num_results: int = Field(default=1, ge=1, le=4)
    aspect_ratio: str = Field(default="1:1")
    sync: bool = Field(default=True)
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED_VALUE)
    prompt_enhancement: bool = Field(default=False)

    model_config = {"extra": "forbid"}

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, v: str) -> str:
        """Validate aspect ratio is in allowed list.

        Args:
            v: Aspect ratio string.

        Returns:
            Validated aspect ratio.

        Raises:
            ValueError: If aspect ratio is invalid.
        """
        if v not in VALID_ASPECT_RATIOS:
            raise ValueError(
                f"Invalid aspect ratio: {v}. Valid options: {VALID_ASPECT_RATIOS}"
            )
        return v

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate and clean prompt.

        Args:
            v: Raw prompt string.

        Returns:
            Cleaned prompt.

        Raises:
            ValueError: If prompt is invalid.
        """
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Prompt cannot be empty or whitespace only")
        return cleaned


class MatrixRequestSchema(BaseModel):
    """Validated schema for matrix generation requests."""

    base_prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    seed: int | None = Field(default=None, ge=0, le=MAX_SEED_VALUE)
    aspect_ratio: str = Field(default="1:1")
    camera_angles: list[str] | None = Field(default=None, min_length=3, max_length=3)
    lighting_styles: list[str] | None = Field(default=None, min_length=3, max_length=3)

    model_config = {"extra": "forbid"}

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, v: str) -> str:
        """Validate aspect ratio."""
        if v not in VALID_ASPECT_RATIOS:
            raise ValueError(
                f"Invalid aspect ratio: {v}. Valid options: {VALID_ASPECT_RATIOS}"
            )
        return v

    @field_validator("base_prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate and clean prompt."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Base prompt cannot be empty")
        return cleaned


class MutationRequestSchema(BaseModel):
    """Validated schema for cell mutation requests."""

    cell_position: str = Field(..., pattern=r"^[0-2],[0-2]$")
    seed: int = Field(..., ge=0, le=MAX_SEED_VALUE)
    base_prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    mutations: dict[str, str] = Field(default_factory=dict)
    aspect_ratio: str = Field(default="1:1")

    model_config = {"extra": "forbid"}

    @field_validator("mutations")
    @classmethod
    def validate_mutations(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate mutation keys are valid.

        Args:
            v: Mutations dictionary.

        Returns:
            Validated mutations.

        Raises:
            ValueError: If invalid mutation keys.
        """
        valid_keys = {"angle", "lighting"}
        invalid_keys = set(v.keys()) - valid_keys
        if invalid_keys:
            raise ValueError(f"Invalid mutation keys: {invalid_keys}")
        return v


class SchemaValidator:
    """Validator for all API schemas."""

    def __init__(self, schemas_dir: Path | None = None) -> None:
        """Initialize schema validator.

        Args:
            schemas_dir: Optional path to JSON schema files.
        """
        self.schemas_dir = schemas_dir or Path(__file__).parent.parent.parent.parent / "schemas"

    def validate_bria_request(self, data: dict) -> BriaRequestSchema:
        """Validate Bria API request data.

        Args:
            data: Request data dictionary.

        Returns:
            Validated BriaRequestSchema.

        Raises:
            ValidationError: If validation fails.
        """
        try:
            return BriaRequestSchema(**data)
        except Exception as e:
            logger.error(f"Bria request validation failed: {e}")
            raise ValidationError(f"Invalid request: {e}") from e

    def validate_matrix_request(self, data: dict) -> MatrixRequestSchema:
        """Validate matrix generation request.

        Args:
            data: Request data dictionary.

        Returns:
            Validated MatrixRequestSchema.

        Raises:
            ValidationError: If validation fails.
        """
        try:
            return MatrixRequestSchema(**data)
        except Exception as e:
            logger.error(f"Matrix request validation failed: {e}")
            raise ValidationError(f"Invalid matrix request: {e}") from e

    def validate_mutation_request(self, data: dict) -> MutationRequestSchema:
        """Validate mutation request.

        Args:
            data: Request data dictionary.

        Returns:
            Validated MutationRequestSchema.

        Raises:
            ValidationError: If validation fails.
        """
        try:
            return MutationRequestSchema(**data)
        except Exception as e:
            logger.error(f"Mutation request validation failed: {e}")
            raise ValidationError(f"Invalid mutation request: {e}") from e

    def validate_fibo_advanced_request(self, data: dict) -> FIBOAdvancedRequest:
        """Validate advanced FIBO request.

        Args:
            data: Request data dictionary.

        Returns:
            Validated FIBOAdvancedRequest.

        Raises:
            ValidationError: If validation fails.
        """
        try:
            return FIBOAdvancedRequest(**data)
        except Exception as e:
            logger.error(f"Advanced FIBO request validation failed: {e}")
            raise ValidationError(f"Invalid FIBO request: {e}") from e

    def to_bria_payload(self, schema: BriaRequestSchema) -> dict:
        """Convert validated schema to Bria API payload.

        Args:
            schema: Validated BriaRequestSchema.

        Returns:
            Dict ready for API submission.
        """
        payload = {
            "prompt": schema.prompt,
            "num_results": schema.num_results,
            "aspect_ratio": schema.aspect_ratio,
            "sync": schema.sync,
        }

        if schema.seed is not None:
            payload["seed"] = schema.seed

        if schema.prompt_enhancement:
            payload["prompt_enhancement"] = True

        return payload

    def load_json_schema(self, schema_name: str) -> dict:
        """Load JSON schema from file.

        Args:
            schema_name: Name of schema file (without extension).

        Returns:
            Parsed JSON schema.

        Raises:
            ValidationError: If schema file not found.
        """
        schema_path = self.schemas_dir / f"{schema_name}.schema.json"

        if not schema_path.exists():
            raise ValidationError(f"Schema file not found: {schema_path}")

        with open(schema_path) as f:
            return json.load(f)
