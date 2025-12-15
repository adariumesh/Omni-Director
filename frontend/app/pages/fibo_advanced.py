"""FIBO Advanced Generation Page with JSON Inspector."""

import json
import streamlit as st
from typing import Dict, Any, Optional

from app.services.api_client import APIClient, APIError
from app.state.session_manager import SessionManager


def render_fibo_advanced_page() -> None:
    """Render the advanced FIBO generation page."""
    st.title("🎯 FIBO Advanced Generation")
    st.markdown("*Professional image generation with full JSON control*")
    
    # Initialize
    api = APIClient()
    session = SessionManager()
    
    # Tabs for different interfaces
    tab_modes, tab_json, tab_history = st.tabs(["🎮 Generation Modes", "🔬 JSON Editor", "📚 History"])
    
    with tab_modes:
        # Mode selection
        mode = st.selectbox(
            "🎮 Generation Mode",
            ["Generate", "Refine", "Inspire"],
            help="Generate: Natural language → JSON → Image | Refine: Modify specific attributes | Inspire: Style variations"
        )
        
        # Layout based on mode
        if mode == "Generate":
            render_generate_mode(api, session)
        elif mode == "Refine":
            render_refine_mode(api, session)
        else:  # Inspire
            render_inspire_mode(api, session)
    
    with tab_json:
        render_json_editor(api, session)
    
    with tab_history:
        render_fibo_history(session)


def render_generate_mode(api: APIClient, session: SessionManager) -> None:
    """Render Generate mode interface."""
    st.subheader("🚀 Generate Mode")
    st.markdown("*Expand natural language into professional photography parameters*")
    
    # Input form
    col1, col2 = st.columns([3, 1])
    
    with col1:
        natural_prompt = st.text_area(
            "Natural Language Description",
            placeholder="e.g., A luxury Swiss watch photographed for a magazine ad",
            height=100,
            key="generate_prompt"
        )
    
    with col2:
        seed = st.number_input("Seed (optional)", min_value=0, max_value=2147483647, value=None, key="gen_seed")
        aspect_ratio = st.selectbox("Aspect Ratio", ["1:1", "4:3", "16:9", "3:4", "9:16"], key="gen_aspect")
        project_id = st.text_input("Project ID (optional)", key="gen_project")
    
    if st.button("🎯 Generate", type="primary", disabled=not natural_prompt):
        with st.spinner("Translating prompt and generating..."):
            try:
                response = api.fibo_generate(
                    natural_prompt=natural_prompt,
                    seed=seed,
                    aspect_ratio=aspect_ratio,
                    project_id=project_id
                )
                
                # Store in session
                session.last_fibo_result = response
                
                # Display results
                display_fibo_results(response, "Generated")
                
            except APIError as e:
                st.error(f"Generation failed: {e.message}")


def render_refine_mode(api: APIClient, session: SessionManager) -> None:
    """Render Refine mode interface."""
    st.subheader("🔧 Refine Mode")
    st.markdown("*Modify specific attributes without breaking scene consistency*")
    
    # Asset selection
    asset_id = st.text_input(
        "Asset ID to Refine",
        placeholder="Enter asset ID from previous generation",
        key="refine_asset_id",
        help="Get this from the asset list or previous generation results"
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        modification = st.text_area(
            "What to Change",
            placeholder="e.g., make it gold instead of silver\nmake the lighting more dramatic\nshow me the side view",
            height=100,
            key="refine_modification"
        )
    
    with col2:
        project_id = st.text_input("Project ID (optional)", key="refine_project")
        
        # Refinement hints
        st.markdown("""
        **Refinement Keywords:**
        - **Lighting**: dramatic, soft, bright, lighting
        - **Color**: gold, silver, red, blue, warm, cool
        - **Camera**: angle, view, perspective, side, close
        - **Background**: background, backdrop, surface
        - **Style**: elegant, modern, vintage, style
        """)
    
    if st.button("🔧 Refine", type="primary", disabled=not (asset_id and modification)):
        with st.spinner("Applying selective refinement..."):
            try:
                response = api.fibo_refine(
                    asset_id=asset_id,
                    modification=modification,
                    project_id=project_id
                )
                
                # Store in session
                session.last_fibo_result = response
                
                # Display results
                display_fibo_results(response, "Refined")
                
            except APIError as e:
                st.error(f"Refinement failed: {e.message}")


def render_inspire_mode(api: APIClient, session: SessionManager) -> None:
    """Render Inspire mode interface."""
    st.subheader("✨ Inspire Mode")
    st.markdown("*Generate variations maintaining style consistency*")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        reference_asset_id = st.text_input(
            "Reference Asset ID",
            placeholder="Asset ID to copy style from",
            key="inspire_reference"
        )
        
        subject_change = st.text_area(
            "New Subject",
            placeholder="e.g., sports car\nfashion model\narchitectural building",
            height=80,
            key="inspire_subject"
        )
    
    with col2:
        seed = st.number_input("Seed (optional)", min_value=0, max_value=2147483647, value=None, key="inspire_seed")
        aspect_ratio = st.selectbox("Aspect Ratio", ["1:1", "4:3", "16:9", "3:4", "9:16"], key="inspire_aspect")
        project_id = st.text_input("Project ID (optional)", key="inspire_project")
    
    if st.button("✨ Inspire", type="primary", disabled=not (reference_asset_id and subject_change)):
        with st.spinner("Creating inspired variations..."):
            try:
                response = api.fibo_inspire(
                    reference_asset_id=reference_asset_id,
                    subject_change=subject_change,
                    seed=seed,
                    aspect_ratio=aspect_ratio,
                    project_id=project_id
                )
                
                # Store in session
                session.last_fibo_result = response
                
                # Display multiple results
                if isinstance(response, list):
                    st.success(f"Generated {len(response)} inspired variations")
                    for i, result in enumerate(response):
                        st.markdown(f"### Variation {i+1}")
                        display_fibo_results(result, f"Inspired {i+1}")
                        st.divider()
                else:
                    display_fibo_results(response, "Inspired")
                
            except APIError as e:
                st.error(f"Inspiration failed: {e.message}")


def display_fibo_results(response: Dict[str, Any], title: str) -> None:
    """Display FIBO generation results with JSON inspector."""
    st.success(f"✅ {title} successfully!")
    
    # Two-column layout: images and JSON
    col_images, col_json = st.columns([1, 1])
    
    with col_images:
        st.markdown("### 🖼️ Generated Images")
        
        # Display images
        for i, image in enumerate(response.get("images", [])):
            st.image(
                image["url"],
                caption=f"Image {i+1} | Seed: {image.get('seed', 'N/A')}",
                width=300
            )
            
            # Asset ID if available
            if response.get("asset_ids") and i < len(response["asset_ids"]):
                st.code(f"Asset ID: {response['asset_ids'][i]}", language=None)
    
    with col_json:
        st.markdown("### 🧬 JSON Inspector")
        
        # Tabs for different JSON views
        tab_request, tab_prompt, tab_metadata = st.tabs(["Request JSON", "Structured Prompt", "Metadata"])
        
        with tab_request:
            st.markdown("**Request Parameters:**")
            st.json(response.get("request_json", {}))
            
            # Copy button
            if st.button("📋 Copy JSON", key=f"copy_json_{title}"):
                st.code(json.dumps(response.get("request_json", {}), indent=2))
        
        with tab_prompt:
            st.markdown("**Generated Prompt:**")
            st.text_area(
                "Structured prompt sent to BRIA:",
                value=response.get("structured_prompt", ""),
                height=150,
                disabled=True,
                key=f"prompt_{title}"
            )
        
        with tab_metadata:
            st.markdown("**Generation Metadata:**")
            st.json(response.get("metadata", {}))
    
    st.divider()


def render_json_editor(api: APIClient, session: SessionManager) -> None:
    """Render advanced JSON parameter editor."""
    st.subheader("🔬 Advanced JSON Editor")
    st.markdown("*Direct manipulation of FIBO parameters*")
    
    # Load from last result or default
    if session.last_fibo_result and st.button("📋 Load from Last Result"):
        template_json = session.last_fibo_result.get("request_json", {})
    else:
        # Default JSON template  
        template_json = {
        "subject": "luxury Swiss watch",
        "camera": {
            "angle": "three_quarter_view",
            "focal_length": "85mm",
            "depth_of_field": "shallow",
            "distance": "medium_shot"
        },
        "lighting": {
            "setup": "studio_three_point",
            "temperature": "daylight_5600k",
            "intensity": "medium",
            "direction": "front"
        },
        "composition": {
            "rule": "rule_of_thirds",
            "framing": "medium_shot"
        },
        "color_palette": {
            "primary_colors": ["silver", "black"],
            "temperature": "neutral",
            "saturation": "natural"
        },
        "mood": "professional",
        "style": "commercial",
        "background": "white_seamless",
        "aspect_ratio": "1:1",
        "seed": 12345
    }
    
    # JSON editor
    edited_json = st.text_area(
        "Edit JSON Parameters:",
        value=json.dumps(template_json, indent=2),
        height=400,
        key="json_editor"
    )
    
    # Validate and generate
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("✅ Validate JSON", type="secondary"):
            try:
                parsed = json.loads(edited_json)
                st.success("✅ JSON is valid!")
                st.json(parsed)
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {e}")
    
    with col2:
        if st.button("🚀 Generate from JSON", type="primary"):
            try:
                parsed = json.loads(edited_json)
                api = APIClient()
                
                with st.spinner("Generating from JSON..."):
                    response = api.fibo_advanced_direct(parsed)
                    session.last_fibo_result = response
                    display_fibo_results(response, "JSON Direct")
                    
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {e}")
            except APIError as e:
                st.error(f"Generation failed: {e.message}")


def render_fibo_history(session: SessionManager) -> None:
    """Render FIBO generation history."""
    st.subheader("📚 FIBO Generation History")
    
    if not session.fibo_history:
        st.info("No FIBO generations yet. Create some using the modes above!")
        return
    
    # History controls
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{len(session.fibo_history)} generations** in history")
    with col2:
        if st.button("🗑️ Clear History"):
            session.clear_fibo_history()
            st.rerun()
    
    # Display history items
    for i, result in enumerate(reversed(session.fibo_history)):
        with st.expander(f"Generation {len(session.fibo_history) - i}: {result.get('mode', 'unknown').title()}", expanded=i == 0):
            
            col_info, col_images = st.columns([1, 1])
            
            with col_info:
                st.markdown("**Details:**")
                st.write(f"Mode: {result.get('mode', 'N/A')}")
                st.write(f"Time: {result.get('timestamp', 'N/A')}")
                st.write(f"Images: {len(result.get('images', []))}")
                
                # Show metadata if available
                if result.get('metadata'):
                    st.markdown("**Metadata:**")
                    st.json(result['metadata'])
                
                # Action buttons
                col_load, col_copy = st.columns([1, 1])
                with col_load:
                    if st.button(f"🔄 Load", key=f"load_{i}"):
                        session.last_fibo_result = result
                        st.success("Loaded to current session!")
                        st.rerun()
                
                with col_copy:
                    if st.button(f"📋 Copy JSON", key=f"copy_{i}"):
                        st.code(json.dumps(result.get('request_json', {}), indent=2))
            
            with col_images:
                # Show images if available
                images = result.get('images', [])
                if images:
                    for j, image in enumerate(images[:3]):  # Show max 3 images
                        st.image(
                            image['url'], 
                            caption=f"Image {j+1}", 
                            width=150
                        )
                    if len(images) > 3:
                        st.markdown(f"*+{len(images)-3} more images*")


if __name__ == "__main__":
    render_fibo_advanced_page()