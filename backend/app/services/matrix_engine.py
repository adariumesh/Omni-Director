"""Matrix engine for generating 3x3 deterministic image grids."""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime

from app.services.bria_client import BriaClient, ImageResult
from app.services.schema_validator import CameraSettings, LightingSettings, FIBOAdvancedRequest

logger = logging.getLogger(__name__)


# Default parameter axes
DEFAULT_CAMERA_ANGLES = ["front view", "side view", "top-down view"]
DEFAULT_LIGHTING_STYLES = ["studio lighting", "neon lighting", "natural sunlight"]


@dataclass
class MatrixCell:
    """Represents a single cell in the 3x3 matrix."""

    position: str  # "row,col" format (e.g., "0,1")
    prompt: str
    seed: int
    angle: str
    lighting: str
    row: int = field(init=False)
    col: int = field(init=False)
    image_result: ImageResult | None = None

    def __post_init__(self) -> None:
        """Parse position into row and column."""
        parts = self.position.split(",")
        self.row = int(parts[0])
        self.col = int(parts[1])


@dataclass
class MatrixResult:
    """Result of a complete matrix generation."""

    seed: int
    base_prompt: str
    aspect_ratio: str
    cells: list[MatrixCell]
    created_at: datetime
    camera_angles: list[str]
    lighting_styles: list[str]

    @property
    def is_complete(self) -> bool:
        """Check if all 9 cells have images."""
        return all(cell.image_result is not None for cell in self.cells)

    @property
    def successful_count(self) -> int:
        """Count cells with successful generation."""
        return sum(1 for cell in self.cells if cell.image_result is not None)

    def get_cell(self, row: int, col: int) -> MatrixCell | None:
        """Get cell at specific position.

        Args:
            row: Row index (0-2).
            col: Column index (0-2).

        Returns:
            MatrixCell or None if not found.
        """
        for cell in self.cells:
            if cell.row == row and cell.col == col:
                return cell
        return None


class MatrixEngine:
    """Engine for generating 3x3 deterministic image matrices."""

    def __init__(
        self,
        bria_client: BriaClient | None = None,
        camera_angles: list[str] | None = None,
        lighting_styles: list[str] | None = None,
    ) -> None:
        """Initialize matrix engine.

        Args:
            bria_client: Optional BriaClient instance.
            camera_angles: Optional custom camera angles (3 values).
            lighting_styles: Optional custom lighting styles (3 values).
        """
        self.bria_client = bria_client or BriaClient()
        self.camera_angles = camera_angles or DEFAULT_CAMERA_ANGLES.copy()
        self.lighting_styles = lighting_styles or DEFAULT_LIGHTING_STYLES.copy()

        # Validate axes have exactly 3 values
        if len(self.camera_angles) != 3:
            raise ValueError("camera_angles must have exactly 3 values")
        if len(self.lighting_styles) != 3:
            raise ValueError("lighting_styles must have exactly 3 values")

    def build_prompt(
        self,
        base_prompt: str,
        angle: str,
        lighting: str,
    ) -> str:
        """Build full prompt for a matrix cell.

        Args:
            base_prompt: User's original prompt.
            angle: Camera angle descriptor.
            lighting: Lighting style descriptor.

        Returns:
            Complete prompt with parameters injected.
        """
        return f"{base_prompt}, {angle}, {lighting}, professional photography"

    def create_matrix_cells(
        self,
        base_prompt: str,
        seed: int,
    ) -> list[MatrixCell]:
        """Create all 9 matrix cells with prompts.

        Args:
            base_prompt: User's base prompt.
            seed: Locked seed for all cells.

        Returns:
            List of 9 MatrixCell objects.
        """
        cells = []

        for row, angle in enumerate(self.camera_angles):
            for col, lighting in enumerate(self.lighting_styles):
                prompt = self.build_prompt(base_prompt, angle, lighting)
                cell = MatrixCell(
                    position=f"{row},{col}",
                    prompt=prompt,
                    seed=seed,
                    angle=angle,
                    lighting=lighting,
                )
                cells.append(cell)

        return cells

    def generate_matrix(
        self,
        base_prompt: str,
        seed: int | None = None,
        aspect_ratio: str = "1:1",
    ) -> MatrixResult:
        """Generate complete 3x3 matrix of images.

        Args:
            base_prompt: User's base prompt.
            seed: Optional seed. If None, generates random seed.
            aspect_ratio: Image aspect ratio.

        Returns:
            MatrixResult with all 9 cells.

        Note:
            This makes 9 API calls (one per cell).
            Failed cells will have image_result=None.
        """
        # Generate seed if not provided
        if seed is None:
            seed = random.randint(0, 2147483647)
            logger.info(f"Generated random seed: {seed}")

        logger.info(f"Generating 3x3 matrix with seed {seed}")

        # Create cell definitions
        cells = self.create_matrix_cells(base_prompt, seed)

        # Generate each cell
        for cell in cells:
            logger.info(f"Generating cell {cell.position}: {cell.angle} + {cell.lighting}")

            try:
                result = self.bria_client.generate_with_locked_seed(
                    prompt=cell.prompt,
                    seed=seed,
                    aspect_ratio=aspect_ratio,
                )
                cell.image_result = result
                logger.info(f"Cell {cell.position} generated successfully")

            except Exception as e:
                logger.error(f"Failed to generate cell {cell.position}: {e}")
                cell.image_result = None

        # Build result
        matrix_result = MatrixResult(
            seed=seed,
            base_prompt=base_prompt,
            aspect_ratio=aspect_ratio,
            cells=cells,
            created_at=datetime.utcnow(),
            camera_angles=self.camera_angles.copy(),
            lighting_styles=self.lighting_styles.copy(),
        )

        logger.info(
            f"Matrix generation complete: {matrix_result.successful_count}/9 successful"
        )

        return matrix_result

    def generate_single_cell(
        self,
        base_prompt: str,
        seed: int,
        row: int,
        col: int,
        aspect_ratio: str = "1:1",
    ) -> MatrixCell:
        """Generate a single matrix cell.

        Args:
            base_prompt: User's base prompt.
            seed: Locked seed.
            row: Row index (0-2).
            col: Column index (0-2).
            aspect_ratio: Image aspect ratio.

        Returns:
            MatrixCell with image result.

        Raises:
            ValueError: If row/col out of range.
        """
        if row < 0 or row > 2:
            raise ValueError(f"Row must be 0-2, got {row}")
        if col < 0 or col > 2:
            raise ValueError(f"Column must be 0-2, got {col}")

        angle = self.camera_angles[row]
        lighting = self.lighting_styles[col]
        prompt = self.build_prompt(base_prompt, angle, lighting)

        cell = MatrixCell(
            position=f"{row},{col}",
            prompt=prompt,
            seed=seed,
            angle=angle,
            lighting=lighting,
        )

        try:
            result = self.bria_client.generate_with_locked_seed(
                prompt=prompt,
                seed=seed,
                aspect_ratio=aspect_ratio,
            )
            cell.image_result = result

        except Exception as e:
            logger.error(f"Failed to generate cell ({row},{col}): {e}")
            raise

        return cell

    def refine_from_cell(
        self,
        cell: MatrixCell,
        new_base_prompt: str,
        aspect_ratio: str = "1:1",
    ) -> MatrixResult:
        """Generate new matrix based on a selected cell.

        Uses the same seed but with a new base prompt.
        Keeps the same parameter axes.

        Args:
            cell: The selected cell to refine from.
            new_base_prompt: New base prompt for variations.
            aspect_ratio: Image aspect ratio.

        Returns:
            New MatrixResult with variations of the new prompt.
        """
        logger.info(f"Refining from cell {cell.position} with seed {cell.seed}")

        return self.generate_matrix(
            base_prompt=new_base_prompt,
            seed=cell.seed,
            aspect_ratio=aspect_ratio,
        )

    def generate_advanced_matrix(
        self,
        subject: str,
        seed: int | None = None,
        base_camera_settings: CameraSettings | None = None,
        base_lighting_settings: LightingSettings | None = None,
        aspect_ratio: str = "1:1"
    ) -> MatrixResult:
        """Generate matrix using advanced FIBO parameters.

        Creates 3x3 matrix with professional camera and lighting variations
        while maintaining the subject consistency through seed locking.

        Args:
            subject: Main subject (e.g., "luxury Swiss watch").
            seed: Optional seed for deterministic generation.
            base_camera_settings: Base camera settings to vary from.
            base_lighting_settings: Base lighting settings to vary from.
            aspect_ratio: Image aspect ratio.

        Returns:
            MatrixResult with advanced parameter variations.
        """
        if seed is None:
            seed = random.randint(0, 2147483647)

        logger.info(f"Generating advanced matrix: {subject} (seed: {seed})")

        # Define professional parameter variations
        camera_variations = [
            "front_view", "three_quarter_view", "side_view"
        ]
        
        lighting_variations = [
            "studio_three_point", "dramatic_side", "natural_window"
        ]

        cells = []
        
        # Create cells with advanced parameters
        for row, camera_angle in enumerate(camera_variations):
            for col, lighting_setup in enumerate(lighting_variations):
                
                # Create advanced request for this cell
                advanced_request = FIBOAdvancedRequest(
                    subject=subject,
                    camera=CameraSettings(
                        angle=camera_angle,
                        focal_length=base_camera_settings.focal_length if base_camera_settings else "85mm",
                        depth_of_field=base_camera_settings.depth_of_field if base_camera_settings else "shallow"
                    ),
                    lighting=LightingSettings(
                        setup=lighting_setup,
                        temperature=base_lighting_settings.temperature if base_lighting_settings else "daylight_5600k",
                        intensity="medium"
                    ),
                    aspect_ratio=aspect_ratio,
                    seed=seed
                )
                
                # Generate structured prompt
                structured_prompt = advanced_request.to_structured_prompt()
                
                cell = MatrixCell(
                    position=f"{row},{col}",
                    prompt=structured_prompt,
                    seed=seed,
                    angle=camera_angle,
                    lighting=lighting_setup,
                )
                
                cells.append(cell)

        # Generate images for each cell
        for cell in cells:
            logger.info(f"Generating advanced cell {cell.position}")
            
            try:
                # Create the advanced request again for generation
                advanced_request = FIBOAdvancedRequest(
                    subject=subject,
                    camera=CameraSettings(angle=cell.angle),
                    lighting=LightingSettings(setup=cell.lighting),
                    seed=seed,
                    aspect_ratio=aspect_ratio
                )
                
                # Generate using advanced method
                from app.services.bria_client import BriaClient
                bria_client = BriaClient()
                results = bria_client.generate_advanced(advanced_request)
                
                if results:
                    cell.image_result = results[0]
                    logger.info(f"Advanced cell {cell.position} generated successfully")
                else:
                    cell.image_result = None
                    logger.warning(f"No results for cell {cell.position}")
                
            except Exception as e:
                logger.error(f"Failed to generate advanced cell {cell.position}: {e}")
                cell.image_result = None

        # Create result
        matrix_result = MatrixResult(
            seed=seed,
            base_prompt=subject,
            aspect_ratio=aspect_ratio,
            cells=cells,
            created_at=datetime.utcnow(),
            camera_angles=camera_variations,
            lighting_styles=lighting_variations,
        )

        logger.info(f"Advanced matrix generation complete: {matrix_result.successful_count}/9 successful")
        return matrix_result

    def mutate_cell(
        self,
        cell: MatrixCell,
        mutations: dict[str, str],
        aspect_ratio: str = "1:1",
    ) -> MatrixCell:
        """Generate new cell with mutated parameters.

        Args:
            cell: Original cell to mutate.
            mutations: Dict of parameter mutations (e.g., {"lighting": "golden hour"}).
            aspect_ratio: Image aspect ratio.

        Returns:
            New MatrixCell with mutations applied.
        """
        # Apply mutations
        new_angle = mutations.get("angle", cell.angle)
        new_lighting = mutations.get("lighting", cell.lighting)

        # Get base prompt (strip parameters from original prompt)
        # This is a simplified approach - in production, store base_prompt separately
        base_prompt = cell.prompt.rsplit(",", 3)[0]

        new_prompt = self.build_prompt(base_prompt, new_angle, new_lighting)

        new_cell = MatrixCell(
            position=cell.position,
            prompt=new_prompt,
            seed=cell.seed,
            angle=new_angle,
            lighting=new_lighting,
        )

        try:
            result = self.bria_client.generate_with_locked_seed(
                prompt=new_prompt,
                seed=cell.seed,
                aspect_ratio=aspect_ratio,
            )
            new_cell.image_result = result

        except Exception as e:
            logger.error(f"Failed to mutate cell: {e}")
            raise

        return new_cell
