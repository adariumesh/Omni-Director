"""Tests for Matrix Engine."""

import pytest
from unittest.mock import MagicMock

from backend.app.services.matrix_engine import (
    MatrixCell,
    MatrixEngine,
    MatrixResult,
    DEFAULT_CAMERA_ANGLES,
    DEFAULT_LIGHTING_STYLES,
)
from backend.app.services.bria_client import ImageResult


class TestMatrixCell:
    """Test MatrixCell dataclass."""

    def test_cell_parses_position(self) -> None:
        """Verify cell parses position into row/col."""
        cell = MatrixCell(
            position="1,2",
            prompt="test",
            seed=123,
            angle="front",
            lighting="studio",
        )
        
        assert cell.row == 1
        assert cell.col == 2

    def test_cell_stores_all_fields(self) -> None:
        """Verify cell stores all provided fields."""
        cell = MatrixCell(
            position="0,0",
            prompt="test prompt",
            seed=12345,
            angle="front view",
            lighting="studio lighting",
        )
        
        assert cell.position == "0,0"
        assert cell.prompt == "test prompt"
        assert cell.seed == 12345
        assert cell.angle == "front view"
        assert cell.lighting == "studio lighting"


class TestMatrixEngineInitialization:
    """Test MatrixEngine initialization."""

    def test_default_axes(self) -> None:
        """Verify default camera angles and lighting styles."""
        engine = MatrixEngine()
        
        assert engine.camera_angles == DEFAULT_CAMERA_ANGLES
        assert engine.lighting_styles == DEFAULT_LIGHTING_STYLES

    def test_custom_axes(self) -> None:
        """Verify custom axes are accepted."""
        custom_angles = ["low angle", "eye level", "high angle"]
        custom_lighting = ["warm", "cool", "neutral"]
        
        engine = MatrixEngine(
            camera_angles=custom_angles,
            lighting_styles=custom_lighting,
        )
        
        assert engine.camera_angles == custom_angles
        assert engine.lighting_styles == custom_lighting

    def test_invalid_axes_length_raises_error(self) -> None:
        """Verify non-3 length axes raise ValueError."""
        with pytest.raises(ValueError, match="exactly 3 values"):
            MatrixEngine(camera_angles=["a", "b"])

        with pytest.raises(ValueError, match="exactly 3 values"):
            MatrixEngine(lighting_styles=["a", "b", "c", "d"])


class TestMatrixEnginePromptBuilding:
    """Test prompt construction."""

    def test_build_prompt_includes_all_parts(self) -> None:
        """Verify prompt includes base, angle, lighting."""
        engine = MatrixEngine()
        
        prompt = engine.build_prompt(
            base_prompt="luxury watch",
            angle="front view",
            lighting="studio lighting",
        )
        
        assert "luxury watch" in prompt
        assert "front view" in prompt
        assert "studio lighting" in prompt
        assert "professional photography" in prompt


class TestMatrixEngineCellCreation:
    """Test matrix cell creation."""

    def test_creates_nine_cells(self) -> None:
        """Verify exactly 9 cells are created."""
        engine = MatrixEngine()
        
        cells = engine.create_matrix_cells("test prompt", seed=123)
        
        assert len(cells) == 9

    def test_all_cells_have_same_seed(self) -> None:
        """Verify all cells share the same seed."""
        engine = MatrixEngine()
        seed = 12345
        
        cells = engine.create_matrix_cells("test prompt", seed=seed)
        
        assert all(cell.seed == seed for cell in cells)

    def test_all_positions_unique(self) -> None:
        """Verify all cell positions are unique."""
        engine = MatrixEngine()
        
        cells = engine.create_matrix_cells("test prompt", seed=123)
        positions = [cell.position for cell in cells]
        
        assert len(set(positions)) == 9

    def test_positions_cover_full_grid(self) -> None:
        """Verify positions cover 0,0 to 2,2."""
        engine = MatrixEngine()
        
        cells = engine.create_matrix_cells("test prompt", seed=123)
        positions = set(cell.position for cell in cells)
        
        expected = {f"{r},{c}" for r in range(3) for c in range(3)}
        assert positions == expected

    def test_each_row_has_same_angle(self) -> None:
        """Verify each row uses the same camera angle."""
        engine = MatrixEngine()
        
        cells = engine.create_matrix_cells("test prompt", seed=123)
        
        for row in range(3):
            row_cells = [c for c in cells if c.row == row]
            angles = set(c.angle for c in row_cells)
            assert len(angles) == 1

    def test_each_column_has_same_lighting(self) -> None:
        """Verify each column uses the same lighting."""
        engine = MatrixEngine()
        
        cells = engine.create_matrix_cells("test prompt", seed=123)
        
        for col in range(3):
            col_cells = [c for c in cells if c.col == col]
            lightings = set(c.lighting for c in col_cells)
            assert len(lightings) == 1


class TestMatrixResult:
    """Test MatrixResult dataclass."""

    def test_is_complete_when_all_have_images(self) -> None:
        """Verify is_complete returns True when all cells have images."""
        cells = []
        for r in range(3):
            for c in range(3):
                cell = MatrixCell(
                    position=f"{r},{c}",
                    prompt="test",
                    seed=123,
                    angle="front",
                    lighting="studio",
                )
                cell.image_result = MagicMock(spec=ImageResult)
                cells.append(cell)

        result = MatrixResult(
            seed=123,
            base_prompt="test",
            aspect_ratio="1:1",
            cells=cells,
            created_at=MagicMock(),
            camera_angles=DEFAULT_CAMERA_ANGLES,
            lighting_styles=DEFAULT_LIGHTING_STYLES,
        )
        
        assert result.is_complete is True
        assert result.successful_count == 9

    def test_is_not_complete_when_some_missing(self) -> None:
        """Verify is_complete returns False when some cells failed."""
        cells = []
        for r in range(3):
            for c in range(3):
                cell = MatrixCell(
                    position=f"{r},{c}",
                    prompt="test",
                    seed=123,
                    angle="front",
                    lighting="studio",
                )
                # Only set image for some cells
                if r + c < 2:
                    cell.image_result = MagicMock(spec=ImageResult)
                cells.append(cell)

        result = MatrixResult(
            seed=123,
            base_prompt="test",
            aspect_ratio="1:1",
            cells=cells,
            created_at=MagicMock(),
            camera_angles=DEFAULT_CAMERA_ANGLES,
            lighting_styles=DEFAULT_LIGHTING_STYLES,
        )
        
        assert result.is_complete is False
        assert result.successful_count == 2

    def test_get_cell_by_position(self) -> None:
        """Verify get_cell returns correct cell."""
        cells = []
        for r in range(3):
            for c in range(3):
                cells.append(MatrixCell(
                    position=f"{r},{c}",
                    prompt=f"prompt_{r}_{c}",
                    seed=123,
                    angle="front",
                    lighting="studio",
                ))

        result = MatrixResult(
            seed=123,
            base_prompt="test",
            aspect_ratio="1:1",
            cells=cells,
            created_at=MagicMock(),
            camera_angles=DEFAULT_CAMERA_ANGLES,
            lighting_styles=DEFAULT_LIGHTING_STYLES,
        )
        
        cell = result.get_cell(1, 2)
        assert cell is not None
        assert cell.prompt == "prompt_1_2"

    def test_get_cell_returns_none_for_invalid_position(self) -> None:
        """Verify get_cell returns None for out-of-range position."""
        result = MatrixResult(
            seed=123,
            base_prompt="test",
            aspect_ratio="1:1",
            cells=[],
            created_at=MagicMock(),
            camera_angles=DEFAULT_CAMERA_ANGLES,
            lighting_styles=DEFAULT_LIGHTING_STYLES,
        )
        
        assert result.get_cell(5, 5) is None


class TestMatrixEngineGeneration:
    """Test matrix generation with mocked API."""

    def test_generate_single_cell_validates_bounds(self) -> None:
        """Verify generate_single_cell validates row/col bounds."""
        engine = MatrixEngine()
        
        with pytest.raises(ValueError, match="Row must be 0-2"):
            engine.generate_single_cell("test", 123, row=5, col=0)
        
        with pytest.raises(ValueError, match="Column must be 0-2"):
            engine.generate_single_cell("test", 123, row=0, col=5)
