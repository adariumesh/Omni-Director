"""Matrix generation page."""

import streamlit as st

from app.components.ui_components import (
    render_cell_details,
    render_header,
    render_matrix_grid,
    render_sidebar,
)
from app.services.api_client import APIClient, APIError
from app.state.session_manager import SessionManager


def render_matrix_page() -> None:
    """Render the main matrix generation page."""
    # Initialize
    session = SessionManager()
    api = APIClient()

    # Render header
    render_header()

    # Render sidebar and get settings
    sidebar_inputs = render_sidebar(session)

    # Update session from sidebar
    session.update_project(name=sidebar_inputs["project_name"])
    session.aspect_ratio = sidebar_inputs["aspect_ratio"]
    session.camera_angles = sidebar_inputs["camera_angles"]
    session.lighting_styles = sidebar_inputs["lighting_styles"]

    if sidebar_inputs["negative_prompt"]:
        session.update_project(negative_prompt=sidebar_inputs["negative_prompt"])

    # Main content area
    st.divider()

    # Generation form
    col1, col2 = st.columns([4, 1])

    with col1:
        base_prompt = st.text_input(
            "🎨 Describe your subject",
            placeholder="e.g., Luxury watch on polished marble surface",
            key="base_prompt",
        )

    with col2:
        seed_input = st.number_input(
            "🎲 Seed (optional)",
            min_value=0,
            max_value=2147483647,
            value=None,
            key="seed_input",
            help="Leave empty for random seed",
        )

    # Generate button
    if st.button(
        "🚀 Generate Matrix",
        use_container_width=True,
        type="primary",
        disabled=not base_prompt,
    ):
        if base_prompt:
            with st.spinner("Generating 3x3 matrix... (this may take ~30 seconds)"):
                try:
                    response = api.generate_matrix(
                        base_prompt=base_prompt,
                        seed=seed_input if seed_input else None,
                        aspect_ratio=session.aspect_ratio,
                        camera_angles=session.camera_angles,
                        lighting_styles=session.lighting_styles,
                    )

                    session.set_matrix_from_response(response)
                    st.success(
                        f"Generated {response['successful_count']}/9 images with seed {response['seed']}"
                    )
                    st.rerun()

                except APIError as e:
                    st.error(f"Generation failed: {e.message}")

    st.divider()

    # Display matrix if exists
    if session.matrix:
        # Two-column layout: matrix on left, details on right
        col_matrix, col_details = st.columns([2, 1])

        with col_matrix:
            st.subheader("🎯 Deterministic Matrix")
            render_matrix_grid(session.matrix, session)

        with col_details:
            if session.selected_cell:
                mutation_request = render_cell_details(session.selected_cell, session)

                if mutation_request:
                    if mutation_request.get("spawn_matrix"):
                        # Spawn new matrix from selected cell
                        with st.spinner("Generating new matrix..."):
                            try:
                                response = api.generate_matrix(
                                    base_prompt=base_prompt or session.matrix.base_prompt,
                                    seed=mutation_request.get("seed"),
                                    aspect_ratio=session.aspect_ratio,
                                    camera_angles=session.camera_angles,
                                    lighting_styles=session.lighting_styles,
                                )
                                session.set_matrix_from_response(response)
                                st.rerun()

                            except APIError as e:
                                st.error(f"Failed: {e.message}")

                    elif mutation_request.get("asset_id"):
                        # Apply mutation
                        with st.spinner("Applying mutation..."):
                            try:
                                response = api.mutate_cell(
                                    asset_id=mutation_request["asset_id"],
                                    mutations=mutation_request["mutations"],
                                )
                                st.success("Mutation applied!")
                                st.image(response["image_url"], width=300)

                            except APIError as e:
                                st.error(f"Mutation failed: {e.message}")
            else:
                st.info("👆 Click a cell to inspect and mutate its DNA")

    else:
        # Empty state
        st.markdown(
            """
            ### 👋 Welcome to FIBO Omni-Director Pro

            **How it works:**
            1. Enter a description of your subject above
            2. Click "Generate Matrix" to create 9 variations
            3. Click any cell to inspect its JSON DNA
            4. Mutate parameters to refine your vision

            **The Magic:** All 9 images share the same seed, so the subject
            remains identical—only the lighting and camera angle change!
            """
        )


if __name__ == "__main__":
    render_matrix_page()
