"""Streamlit session state manager for FIBO Omni-Director."""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import streamlit as st


@dataclass
class MatrixCell:
    """Represents a cell in the 3x3 matrix."""

    position: str
    row: int
    col: int
    prompt: str
    angle: str
    lighting: str
    image_url: Optional[str] = None
    asset_id: Optional[str] = None
    success: bool = False


@dataclass
class MatrixState:
    """State of the current matrix."""

    seed: int
    base_prompt: str
    aspect_ratio: str
    cells: list[MatrixCell] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    camera_angles: list[str] = field(default_factory=list)
    lighting_styles: list[str] = field(default_factory=list)

    def get_cell(self, row: int, col: int) -> Optional[MatrixCell]:
        """Get cell at position."""
        for cell in self.cells:
            if cell.row == row and cell.col == col:
                return cell
        return None


@dataclass
class ProjectState:
    """Current project state."""

    id: Optional[str] = None
    name: str = "Untitled Project"
    brand_logo_path: Optional[str] = None
    negative_prompt: Optional[str] = None


class SessionManager:
    """Manages Streamlit session state for the application."""

    # Session state keys
    KEY_PROJECT = "project"
    KEY_MATRIX = "matrix"
    KEY_SELECTED_CELL = "selected_cell"
    KEY_HISTORY = "history"
    KEY_ASPECT_RATIO = "aspect_ratio"
    KEY_CAMERA_ANGLES = "camera_angles"
    KEY_LIGHTING_STYLES = "lighting_styles"
    KEY_LAST_FIBO_RESULT = "last_fibo_result"
    KEY_FIBO_HISTORY = "fibo_history"

    # Default values
    DEFAULT_CAMERA_ANGLES = ["front view", "side view", "top-down view"]
    DEFAULT_LIGHTING_STYLES = ["studio lighting", "neon lighting", "natural sunlight"]

    def __init__(self) -> None:
        """Initialize session state with defaults."""
        self._init_defaults()

    def _init_defaults(self) -> None:
        """Initialize default session state values."""
        if self.KEY_PROJECT not in st.session_state:
            st.session_state[self.KEY_PROJECT] = ProjectState()

        if self.KEY_MATRIX not in st.session_state:
            st.session_state[self.KEY_MATRIX] = None

        if self.KEY_SELECTED_CELL not in st.session_state:
            st.session_state[self.KEY_SELECTED_CELL] = None

        if self.KEY_HISTORY not in st.session_state:
            st.session_state[self.KEY_HISTORY] = []

        if self.KEY_ASPECT_RATIO not in st.session_state:
            st.session_state[self.KEY_ASPECT_RATIO] = "1:1"

        if self.KEY_CAMERA_ANGLES not in st.session_state:
            st.session_state[self.KEY_CAMERA_ANGLES] = self.DEFAULT_CAMERA_ANGLES.copy()

        if self.KEY_LIGHTING_STYLES not in st.session_state:
            st.session_state[self.KEY_LIGHTING_STYLES] = self.DEFAULT_LIGHTING_STYLES.copy()

        if self.KEY_LAST_FIBO_RESULT not in st.session_state:
            st.session_state[self.KEY_LAST_FIBO_RESULT] = None

        if self.KEY_FIBO_HISTORY not in st.session_state:
            st.session_state[self.KEY_FIBO_HISTORY] = []

    # ==================== Project State ====================

    @property
    def project(self) -> ProjectState:
        """Get current project state."""
        return st.session_state[self.KEY_PROJECT]

    @project.setter
    def project(self, value: ProjectState) -> None:
        """Set current project state."""
        st.session_state[self.KEY_PROJECT] = value

    def update_project(
        self,
        project_id: str | None = None,
        name: str | None = None,
        brand_logo_path: str | None = None,
        negative_prompt: str | None = None,
    ) -> None:
        """Update project state fields."""
        project = self.project

        if project_id is not None:
            project.id = project_id
        if name is not None:
            project.name = name
        if brand_logo_path is not None:
            project.brand_logo_path = brand_logo_path
        if negative_prompt is not None:
            project.negative_prompt = negative_prompt

        st.session_state[self.KEY_PROJECT] = project

    # ==================== Matrix State ====================

    @property
    def matrix(self) -> MatrixState | None:
        """Get current matrix state."""
        return st.session_state[self.KEY_MATRIX]

    @matrix.setter
    def matrix(self, value: MatrixState | None) -> None:
        """Set current matrix state."""
        st.session_state[self.KEY_MATRIX] = value

    def set_matrix_from_response(self, response: dict) -> None:
        """Set matrix state from API response.

        Args:
            response: Matrix response from backend API.
        """
        cells = []
        for cell_data in response.get("cells", []):
            cells.append(
                MatrixCell(
                    position=cell_data["position"],
                    row=cell_data["row"],
                    col=cell_data["col"],
                    prompt=cell_data["prompt"],
                    angle=cell_data["angle"],
                    lighting=cell_data["lighting"],
                    image_url=cell_data.get("image_url"),
                    asset_id=cell_data.get("asset_id"),
                    success=cell_data.get("success", False),
                )
            )

        matrix = MatrixState(
            seed=response["seed"],
            base_prompt=response["base_prompt"],
            aspect_ratio=response["aspect_ratio"],
            cells=cells,
            camera_angles=self.camera_angles,
            lighting_styles=self.lighting_styles,
        )

        self.matrix = matrix
        self._add_to_history(matrix)

    def clear_matrix(self) -> None:
        """Clear current matrix."""
        st.session_state[self.KEY_MATRIX] = None
        st.session_state[self.KEY_SELECTED_CELL] = None

    # ==================== Cell Selection ====================

    @property
    def selected_cell(self) -> MatrixCell | None:
        """Get currently selected cell."""
        return st.session_state[self.KEY_SELECTED_CELL]

    @selected_cell.setter
    def selected_cell(self, value: MatrixCell | None) -> None:
        """Set currently selected cell."""
        st.session_state[self.KEY_SELECTED_CELL] = value

    def select_cell(self, row: int, col: int) -> MatrixCell | None:
        """Select a cell by position.

        Args:
            row: Row index (0-2).
            col: Column index (0-2).

        Returns:
            Selected cell or None if not found.
        """
        if self.matrix is None:
            return None

        cell = self.matrix.get_cell(row, col)
        if cell:
            self.selected_cell = cell

        return cell

    def deselect_cell(self) -> None:
        """Clear cell selection."""
        st.session_state[self.KEY_SELECTED_CELL] = None

    # ==================== History ====================

    @property
    def history(self) -> list[MatrixState]:
        """Get matrix history."""
        return st.session_state[self.KEY_HISTORY]

    def _add_to_history(self, matrix: MatrixState) -> None:
        """Add matrix to history."""
        history = self.history
        history.append(matrix)

        # Limit history size
        if len(history) > 10:
            history = history[-10:]

        st.session_state[self.KEY_HISTORY] = history

    def clear_history(self) -> None:
        """Clear matrix history."""
        st.session_state[self.KEY_HISTORY] = []

    def restore_from_history(self, index: int) -> bool:
        """Restore matrix from history.

        Args:
            index: History index.

        Returns:
            True if restored, False if index invalid.
        """
        if 0 <= index < len(self.history):
            self.matrix = self.history[index]
            return True
        return False

    # ==================== FIBO Results ====================

    @property
    def last_fibo_result(self) -> dict | None:
        """Get last FIBO generation result."""
        return st.session_state[self.KEY_LAST_FIBO_RESULT]

    @last_fibo_result.setter
    def last_fibo_result(self, value: dict | None) -> None:
        """Set last FIBO generation result."""
        st.session_state[self.KEY_LAST_FIBO_RESULT] = value
        
        # Add to history if not None
        if value is not None:
            self._add_to_fibo_history(value)

    @property
    def fibo_history(self) -> list[dict]:
        """Get FIBO generation history."""
        return st.session_state[self.KEY_FIBO_HISTORY]

    def _add_to_fibo_history(self, result: dict) -> None:
        """Add FIBO result to history."""
        history = self.fibo_history
        history.append({
            **result,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Limit history size
        if len(history) > 20:
            history = history[-20:]

        st.session_state[self.KEY_FIBO_HISTORY] = history

    def clear_fibo_history(self) -> None:
        """Clear FIBO generation history."""
        st.session_state[self.KEY_FIBO_HISTORY] = []

    # ==================== Configuration ====================

    @property
    def aspect_ratio(self) -> str:
        """Get current aspect ratio."""
        return st.session_state[self.KEY_ASPECT_RATIO]

    @aspect_ratio.setter
    def aspect_ratio(self, value: str) -> None:
        """Set current aspect ratio."""
        st.session_state[self.KEY_ASPECT_RATIO] = value

    @property
    def camera_angles(self) -> list[str]:
        """Get current camera angles."""
        return st.session_state[self.KEY_CAMERA_ANGLES]

    @camera_angles.setter
    def camera_angles(self, value: list[str]) -> None:
        """Set camera angles."""
        st.session_state[self.KEY_CAMERA_ANGLES] = value

    @property
    def lighting_styles(self) -> list[str]:
        """Get current lighting styles."""
        return st.session_state[self.KEY_LIGHTING_STYLES]

    @lighting_styles.setter
    def lighting_styles(self, value: list[str]) -> None:
        """Set lighting styles."""
        st.session_state[self.KEY_LIGHTING_STYLES] = value

    # ==================== Utility ====================

    def reset_all(self) -> None:
        """Reset all session state to defaults."""
        st.session_state[self.KEY_PROJECT] = ProjectState()
        st.session_state[self.KEY_MATRIX] = None
        st.session_state[self.KEY_SELECTED_CELL] = None
        st.session_state[self.KEY_HISTORY] = []
        st.session_state[self.KEY_ASPECT_RATIO] = "1:1"
        st.session_state[self.KEY_CAMERA_ANGLES] = self.DEFAULT_CAMERA_ANGLES.copy()
        st.session_state[self.KEY_LIGHTING_STYLES] = self.DEFAULT_LIGHTING_STYLES.copy()

    def get_state_summary(self) -> dict[str, Any]:
        """Get summary of current state for debugging."""
        return {
            "project_id": self.project.id,
            "project_name": self.project.name,
            "has_matrix": self.matrix is not None,
            "matrix_seed": self.matrix.seed if self.matrix else None,
            "selected_cell": self.selected_cell.position if self.selected_cell else None,
            "history_length": len(self.history),
            "aspect_ratio": self.aspect_ratio,
        }
