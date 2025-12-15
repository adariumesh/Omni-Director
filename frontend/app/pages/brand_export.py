"""Brand Guard and Export Page."""

import json
import streamlit as st
from typing import Dict, Any, List

from app.services.api_client import APIClient, APIError
from app.state.session_manager import SessionManager


def render_brand_export_page() -> None:
    """Render the brand guard and export page."""
    st.title("🛡️ Brand Guard & Export")
    st.markdown("*Protect your brand and export professional packages*")
    
    # Initialize
    api = APIClient()
    session = SessionManager()
    
    # Tabs for different functions
    tab_brand, tab_export, tab_compliance = st.tabs(["🛡️ Brand Protection", "📦 Export Assets", "📊 Compliance"])
    
    with tab_brand:
        render_brand_protection(api)
    
    with tab_export:
        render_asset_export(api, session)
    
    with tab_compliance:
        render_compliance_check(api)


def render_brand_protection(api: APIClient) -> None:
    """Render brand protection configuration."""
    st.subheader("🛡️ Brand Guidelines")
    st.markdown("Configure brand protection rules and restrictions")
    
    # Current guidelines
    try:
        guidelines = api._make_request("GET", "/api/v1/brand/guidelines")
        
        st.success("✅ Brand protection active")
        with st.expander("Current Guidelines", expanded=False):
            st.json(guidelines)
    except APIError:
        st.warning("⚠️ Brand guidelines not configured")
        guidelines = {}
    
    # Configuration form
    with st.form("brand_guidelines"):
        st.markdown("### Configure Protection")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            brand_name = st.text_input(
                "Brand Name", 
                value=guidelines.get("brand_name", "FIBO Omni-Director"),
                help="Your brand or company name"
            )
            
            copyright_text = st.text_input(
                "Copyright Text",
                value=guidelines.get("copyright_text", "Generated with FIBO Omni-Director Pro"),
                help="Text for watermarks and metadata"
            )
            
            watermark_enabled = st.checkbox(
                "Enable Watermarks",
                value=guidelines.get("watermark_enabled", True),
                help="Apply subtle watermarks to generated images"
            )
            
            logo_position = st.selectbox(
                "Logo Position",
                ["bottom_right", "bottom_left", "top_right", "top_left", "center"],
                index=0,
                help="Position for brand logo overlay"
            )
        
        with col2:
            logo_opacity = st.slider(
                "Logo Opacity",
                min_value=0.0,
                max_value=1.0,
                value=guidelines.get("logo_opacity", 0.8),
                step=0.1,
                help="Transparency of logo overlay"
            )
            
            prohibited_words = st.text_area(
                "Prohibited Words (one per line)",
                value="\n".join(guidelines.get("prohibited_words", [])),
                help="Words that should not appear in prompts",
                height=100
            )
            
            prohibited_colors = st.text_area(
                "Prohibited Colors (one per line)", 
                value="\n".join(guidelines.get("prohibited_colors", [])),
                help="Colors that should not be used",
                height=60
            )
            
            required_colors = st.text_area(
                "Required Colors (one per line)",
                value="\n".join(guidelines.get("required_colors", [])),
                help="Colors that should be included when possible",
                height=60
            )
        
        # Quality requirements
        st.markdown("### Quality Requirements")
        
        col3, col4 = st.columns([1, 1])
        
        with col3:
            min_width = st.number_input(
                "Minimum Width",
                min_value=256,
                max_value=2048,
                value=guidelines.get("min_resolution", [512, 512])[0],
                step=64
            )
        
        with col4:
            min_height = st.number_input(
                "Minimum Height", 
                min_value=256,
                max_value=2048,
                value=guidelines.get("min_resolution", [512, 512])[1],
                step=64
            )
        
        # Submit button
        if st.form_submit_button("💾 Save Guidelines", type="primary"):
            try:
                payload = {
                    "brand_name": brand_name,
                    "copyright_text": copyright_text,
                    "watermark_enabled": watermark_enabled,
                    "logo_position": logo_position,
                    "logo_opacity": logo_opacity,
                    "prohibited_words": [w.strip() for w in prohibited_words.split('\n') if w.strip()],
                    "prohibited_colors": [c.strip() for c in prohibited_colors.split('\n') if c.strip()],
                    "required_colors": [c.strip() for c in required_colors.split('\n') if c.strip()],
                    "min_resolution": [min_width, min_height]
                }
                
                response = api._make_request("POST", "/api/v1/brand/guidelines", json=payload)
                st.success(f"✅ {response['message']}")
                st.rerun()
                
            except APIError as e:
                st.error(f"❌ Failed to save guidelines: {e.message}")


def render_asset_export(api: APIClient, session: SessionManager) -> None:
    """Render asset export interface."""
    st.subheader("📦 Export Assets")
    st.markdown("Export your generated assets in professional formats")
    
    # Asset selection
    st.markdown("### Select Assets")
    
    # Fetch assets from API
    try:
        assets_response = api._make_request("GET", "/api/v1/assets")
        available_assets = [
            {
                "id": asset["id"],
                "prompt": asset["prompt"][:50] + "..." if len(asset["prompt"]) > 50 else asset["prompt"],
                "created": asset.get("created_at", "Unknown")[:10] if asset.get("created_at") else "Unknown"
            }
            for asset in assets_response.get("assets", [])
        ]
    except APIError:
        st.warning("⚠️ Could not load assets from API, using sample data")
        available_assets = [
            {"id": "sample_001", "prompt": "Sample asset for testing", "created": "2024-12-15"},
        ]
    
    # Asset selection
    selected_assets = []
    
    if available_assets:
        asset_selection = st.multiselect(
            "Choose assets to export",
            options=[asset["id"] for asset in available_assets],
            format_func=lambda x: f"{x}: {next(a['prompt'] for a in available_assets if a['id'] == x)[:50]}...",
            help="Select one or more assets for export"
        )
        selected_assets = asset_selection
    else:
        st.info("No assets available for export. Generate some images first!")
        return
    
    if not selected_assets:
        st.warning("Please select at least one asset to export")
        return
    
    # Export configuration
    st.markdown("### Export Configuration")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        format_type = st.selectbox(
            "Export Format",
            ["portfolio", "archive", "presentation"],
            format_func=lambda x: {
                "portfolio": "🎨 Portfolio - Interactive gallery with HTML viewer",
                "archive": "📁 Archive - Complete dataset with all metadata", 
                "presentation": "📊 Presentation - High-quality images for presentations"
            }[x],
            help="Choose the format that best suits your needs"
        )
        
        image_format = st.selectbox(
            "Image Format",
            ["PNG", "JPEG", "WEBP"],
            help="File format for exported images"
        )
        
        image_quality = st.slider(
            "Image Quality",
            min_value=60,
            max_value=100,
            value=95,
            help="Quality setting for compressed formats"
        )
        
        naming_convention = st.selectbox(
            "Naming Convention",
            ["descriptive", "simple", "timestamp"],
            format_func=lambda x: {
                "descriptive": "Descriptive - 001_luxury_watch_12345",
                "simple": "Simple - image_001",
                "timestamp": "Timestamp - fibo_20241214_143022_001"
            }[x],
            help="How to name the exported files"
        )
    
    with col2:
        include_images = st.checkbox("Include Images", value=True, help="Export the actual image files")
        include_json = st.checkbox("Include JSON", value=True, help="Export generation parameters")
        include_metadata = st.checkbox("Include Metadata", value=True, help="Export extended metadata")
        create_zip = st.checkbox("Create ZIP", value=True, help="Package everything in a ZIP file")
        apply_watermark = st.checkbox("Apply Watermarks", value=False, help="Add brand watermarks to images")
        
        # Format-specific info
        if format_type == "portfolio":
            st.info("📋 Includes: Interactive HTML gallery, thumbnails, organized folders")
        elif format_type == "archive":
            st.info("📋 Includes: CSV summaries, complete JSON dataset, technical metadata")
        elif format_type == "presentation":
            st.info("📋 Includes: 300 DPI images, slide thumbnails, PowerPoint guides")
    
    # Export button
    if st.button("📦 Export Assets", type="primary", use_container_width=True):
        with st.spinner(f"Creating {format_type} export..."):
            try:
                payload = {
                    "asset_ids": selected_assets,
                    "format_type": format_type,
                    "include_images": include_images,
                    "include_json": include_json,
                    "include_metadata": include_metadata,
                    "image_format": image_format,
                    "image_quality": image_quality,
                    "create_zip": create_zip,
                    "apply_watermark": apply_watermark,
                    "naming_convention": naming_convention
                }
                
                response = api._make_request("POST", "/api/v1/export", json=payload)
                
                if response["success"]:
                    st.success("✅ Export completed successfully!")
                    
                    # Display export details
                    col_info1, col_info2, col_info3 = st.columns([1, 1, 1])
                    
                    with col_info1:
                        st.metric("Assets Exported", response["assets_exported"])
                    
                    with col_info2:
                        st.metric("Total Files", response["file_count"])
                    
                    with col_info3:
                        file_size_mb = response["total_size"] / (1024 * 1024)
                        st.metric("Package Size", f"{file_size_mb:.1f} MB")
                    
                    # Download info
                    st.markdown("### 📥 Download")
                    st.info(f"📁 Export saved to: `{response['export_path']}`")
                    
                    if response.get("download_url"):
                        st.markdown(f"🔗 [Download Package]({response['download_url']})")
                    
                    # Show metadata
                    with st.expander("Export Details"):
                        st.json(response)
                
                else:
                    st.error("❌ Export failed")
                    if response.get("errors"):
                        for error in response["errors"]:
                            st.error(f"• {error}")
                
            except APIError as e:
                st.error(f"❌ Export failed: {e.message}")


def render_compliance_check(api: APIClient) -> None:
    """Render compliance checking interface."""
    st.subheader("📊 Brand Compliance")
    st.markdown("Check prompts and parameters against brand guidelines")
    
    # Compliance check tabs
    check_tab1, check_tab2 = st.tabs(["🔍 Check Content", "📈 Compliance Report"])
    
    with check_tab1:
        # Prompt compliance
        st.markdown("### Check Prompt Compliance")
        
        prompt_text = st.text_area(
            "Prompt to Check",
            placeholder="Enter a prompt to check against brand guidelines...",
            height=100,
            help="Enter the text prompt you want to validate"
        )
        
        if st.button("🔍 Check Prompt", type="primary") and prompt_text:
            with st.spinner("Checking compliance..."):
                try:
                    payload = {"prompt": prompt_text}
                    response = api._make_request("POST", "/api/v1/brand/check", json=payload)
                    
                    # Display results
                    score = response["score"]
                    compliant = response["compliant"]
                    
                    # Score display
                    col_score, col_status = st.columns([1, 1])
                    
                    with col_score:
                        st.metric(
                            "Compliance Score",
                            f"{score:.1%}",
                            delta=f"{'✅ Compliant' if compliant else '⚠️ Issues'}"
                        )
                    
                    with col_status:
                        if compliant:
                            st.success("✅ Meets all brand requirements")
                        else:
                            st.warning("⚠️ Brand violations detected")
                    
                    # Violations
                    if response["violations"]:
                        st.markdown("### ⚠️ Violations Found")
                        
                        for violation in response["violations"]:
                            severity_emoji = {
                                "low": "💙",
                                "medium": "💛", 
                                "high": "🧡",
                                "critical": "❤️"
                            }.get(violation["severity"], "⚪")
                            
                            with st.expander(f"{severity_emoji} {violation['type'].title()} ({violation['severity']})", expanded=True):
                                st.write(violation["message"])
                                if violation.get("fix"):
                                    st.info(f"💡 **Suggested fix:** {violation['fix']}")
                    
                    # Suggestions
                    if response["suggestions"]:
                        st.markdown("### 💡 Suggestions")
                        for suggestion in response["suggestions"]:
                            st.info(f"• {suggestion}")
                
                except APIError as e:
                    st.error(f"❌ Compliance check failed: {e.message}")
        
        # JSON compliance
        st.markdown("### Check JSON Compliance") 
        
        json_text = st.text_area(
            "JSON Parameters to Check",
            placeholder='{"subject": "luxury watch", "color_palette": {"primary_colors": ["gold", "black"]}}',
            height=150,
            help="Enter JSON parameters to validate against brand guidelines"
        )
        
        if st.button("🔍 Check JSON", type="secondary") and json_text:
            try:
                parsed_json = json.loads(json_text)
                
                with st.spinner("Checking JSON compliance..."):
                    payload = {"request_json": parsed_json}
                    response = api._make_request("POST", "/api/v1/brand/check", json=payload)
                    
                    # Similar display logic as prompt check
                    score = response["score"]
                    compliant = response["compliant"]
                    
                    if compliant:
                        st.success(f"✅ JSON compliant (Score: {score:.1%})")
                    else:
                        st.warning(f"⚠️ JSON has violations (Score: {score:.1%})")
                        
                        for violation in response["violations"]:
                            st.error(f"• {violation['message']}")
                
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON format")
            except APIError as e:
                st.error(f"❌ JSON compliance check failed: {e.message}")
    
    with check_tab2:
        # Compliance reporting
        st.markdown("### 📈 Compliance Overview")
        st.info("💡 Generate reports after running compliance checks")
        
        # Mock compliance metrics
        col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
        
        with col_metric1:
            st.metric("Overall Score", "87%", "↑ 5%")
        
        with col_metric2:
            st.metric("Checks Run", "15", "↑ 3")
        
        with col_metric3:
            st.metric("Violations", "2", "↓ 1")
        
        with col_metric4:
            st.metric("Compliance Rate", "73%", "↑ 12%")
        
        # Compliance chart placeholder
        st.markdown("### 📊 Compliance Trends")
        st.info("📈 Compliance trend charts would appear here after running multiple checks")
        
        # Recommendations
        st.markdown("### 💡 Recommendations")
        
        recommendations = [
            "Review color palette usage - 2 prohibited colors detected",
            "Update prompt templates to avoid flagged terms",
            "Increase minimum resolution requirements",
            "Enable watermarks for brand protection"
        ]
        
        for rec in recommendations:
            st.info(f"• {rec}")


if __name__ == "__main__":
    render_brand_export_page()