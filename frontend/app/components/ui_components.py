"""Reusable UI components for FIBO Omni-Director."""

import streamlit as st

from app.config import config
from app.state.session_manager import MatrixCell, MatrixState, SessionManager


def render_header() -> None:
    """Render application header."""
    st.title(f"{config.page_icon} {config.page_title}")
    st.caption("Deterministic Visual Production Studio")


def render_sidebar(session: SessionManager) -> dict:
    """Render sidebar with controls.

    Args:
        session: Session manager instance.

    Returns:
        Dict of sidebar inputs.
    """
    with st.sidebar:
        st.header("⚙️ Settings")

        # Project settings
        st.subheader("📁 Project")
        project_name = st.text_input(
            "Project Name",
            value=session.project.name,
            key="sidebar_project_name",
        )

        # Aspect ratio
        st.subheader("📐 Aspect Ratio")
        aspect_ratios = ["1:1", "9:16", "16:9", "4:3", "3:4"]
        aspect_ratio = st.selectbox(
            "Select ratio",
            options=aspect_ratios,
            index=aspect_ratios.index(session.aspect_ratio),
            key="sidebar_aspect_ratio",
        )

        # Brand settings
        st.subheader("🛡️ Brand Guard")
        brand_logo = st.file_uploader(
            "Upload Logo",
            type=["png", "jpg", "jpeg"],
            key="sidebar_logo",
        )
        negative_prompt = st.text_area(
            "Negative Prompt (Safety)",
            value=session.project.negative_prompt or "",
            placeholder="e.g., no blurry text, no competitor colors",
            key="sidebar_negative",
        )

        # Matrix axes
        st.subheader("🎯 Matrix Axes")

        st.caption("Camera Angles (rows)")
        col1, col2, col3 = st.columns(3)
        with col1:
            angle1 = st.text_input("Row 1", value=session.camera_angles[0], key="angle1")
        with col2:
            angle2 = st.text_input("Row 2", value=session.camera_angles[1], key="angle2")
        with col3:
            angle3 = st.text_input("Row 3", value=session.camera_angles[2], key="angle3")

        st.caption("Lighting Styles (columns)")
        col1, col2, col3 = st.columns(3)
        with col1:
            light1 = st.text_input("Col 1", value=session.lighting_styles[0], key="light1")
        with col2:
            light2 = st.text_input("Col 2", value=session.lighting_styles[1], key="light2")
        with col3:
            light3 = st.text_input("Col 3", value=session.lighting_styles[2], key="light3")

        # Reset button
        st.divider()
        if st.button("🔄 Reset All", use_container_width=True):
            session.reset_all()
            st.rerun()

        return {
            "project_name": project_name,
            "aspect_ratio": aspect_ratio,
            "brand_logo": brand_logo,
            "negative_prompt": negative_prompt,
            "camera_angles": [angle1, angle2, angle3],
            "lighting_styles": [light1, light2, light3],
        }


from typing import Optional, Callable

def render_matrix_grid(
    matrix: MatrixState,
    session: SessionManager,
    on_cell_click: Optional[Callable] = None,
) -> Optional[MatrixCell]:
    """Render 3x3 matrix grid.

    Args:
        matrix: Matrix state to render.
        session: Session manager.
        on_cell_click: Optional callback for cell clicks.

    Returns:
        Clicked cell or None.
    """
    clicked_cell = None

    # Header with seed info
    st.markdown(f"**Seed:** `{matrix.seed}` | **Prompt:** {matrix.base_prompt}")
    st.divider()

    # Column headers (lighting styles)
    header_cols = st.columns([1, 3, 3, 3])
    with header_cols[0]:
        st.write("")  # Empty corner
    for i, lighting in enumerate(matrix.lighting_styles):
        with header_cols[i + 1]:
            st.caption(f"💡 {lighting}")

    # Grid rows
    for row, angle in enumerate(matrix.camera_angles):
        cols = st.columns([1, 3, 3, 3])

        # Row header
        with cols[0]:
            st.caption(f"📷 {angle}")

        # Cells
        for col in range(3):
            cell = matrix.get_cell(row, col)
            if not cell:
                continue

            with cols[col + 1]:
                # Cell container
                is_selected = (
                    session.selected_cell is not None
                    and session.selected_cell.position == cell.position
                )

                if cell.image_url:
                    st.image(
                        cell.image_url,
                        use_container_width=True,
                        caption=f"[{row},{col}]",
                    )

                    # Selection button
                    button_label = "✓ Selected" if is_selected else "Select"
                    if st.button(
                        button_label,
                        key=f"select_{row}_{col}",
                        use_container_width=True,
                        type="primary" if is_selected else "secondary",
                    ):
                        session.select_cell(row, col)
                        clicked_cell = cell
                        if on_cell_click:
                            on_cell_click(cell)
                else:
                    st.warning("Failed")

    return clicked_cell


def render_cell_details(cell: MatrixCell, session: SessionManager) -> dict | None:
    """Render selected cell details panel.

    Args:
        cell: Selected cell to display.
        session: Session manager.

    Returns:
        Mutation request dict if user submits, None otherwise.
    """
    st.subheader(f"🔬 Cell [{cell.row},{cell.col}] Details")

    # Image preview
    if cell.image_url:
        st.image(cell.image_url, width=400)

    # JSON DNA
    st.markdown("**JSON DNA:**")
    st.json({
        "position": cell.position,
        "seed": session.matrix.seed if session.matrix else None,
        "angle": cell.angle,
        "lighting": cell.lighting,
        "prompt": cell.prompt,
    })

    # Mutation controls
    st.markdown("**🧬 Mutate Parameters:**")

    col1, col2 = st.columns(2)

    with col1:
        new_angle = st.selectbox(
            "Camera Angle",
            options=session.camera_angles + ["custom..."],
            index=session.camera_angles.index(cell.angle)
            if cell.angle in session.camera_angles
            else 0,
            key="mutate_angle",
        )
        if new_angle == "custom...":
            new_angle = st.text_input("Custom angle", key="custom_angle")

    with col2:
        new_lighting = st.selectbox(
            "Lighting Style",
            options=session.lighting_styles + ["custom..."],
            index=session.lighting_styles.index(cell.lighting)
            if cell.lighting in session.lighting_styles
            else 0,
            key="mutate_lighting",
        )
        if new_lighting == "custom...":
            new_lighting = st.text_input("Custom lighting", key="custom_lighting")

    # Submit mutation
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Apply Mutation", use_container_width=True, type="primary"):
            mutations = {}
            if new_angle != cell.angle:
                mutations["angle"] = new_angle
            if new_lighting != cell.lighting:
                mutations["lighting"] = new_lighting

            if mutations:
                return {
                    "asset_id": cell.asset_id,
                    "mutations": mutations,
                }
            else:
                st.info("No changes to apply")

    with col2:
        if st.button("🔄 Spawn New Matrix", use_container_width=True):
            # Signal to generate new matrix from this cell
            return {"spawn_matrix": True, "seed": session.matrix.seed if session.matrix else None}

    return None


def render_history(session: SessionManager) -> int | None:
    """Render matrix history panel.

    Args:
        session: Session manager.

    Returns:
        Selected history index or None.
    """
    if not session.history:
        st.info("No history yet. Generate a matrix to start.")
        return None

    st.subheader("📜 History")

    for i, matrix in enumerate(reversed(session.history)):
        actual_index = len(session.history) - 1 - i

        with st.expander(f"Matrix #{actual_index + 1} - Seed: {matrix.seed}"):
            st.caption(f"Prompt: {matrix.base_prompt}")
            st.caption(f"Created: {matrix.created_at.strftime('%H:%M:%S')}")

            if st.button(f"Restore", key=f"restore_{actual_index}"):
                return actual_index

    return None
