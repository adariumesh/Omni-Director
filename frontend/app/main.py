"""Streamlit application entry point."""

import streamlit as st

from app.config import config
from app.pages.matrix import render_matrix_page
from app.pages.fibo_advanced import render_fibo_advanced_page
from app.pages.brand_export import render_brand_export_page

# Page configuration
st.set_page_config(
    page_title=config.page_title,
    page_icon=config.page_icon,
    layout=config.layout,
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
    <style>
    .stApp {
        max-width: 1400px;
        margin: 0 auto;
    }
    .stButton > button {
        border-radius: 8px;
    }
    .stImage {
        border-radius: 8px;
        border: 1px solid #333;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def main() -> None:
    """Main application entry point."""
    # Sidebar navigation
    st.sidebar.title("🎯 FIBO Omni-Director Pro")
    page = st.sidebar.selectbox(
        "Navigation",
        ["🎲 Matrix Generation", "🧬 FIBO Advanced", "🛡️ Brand & Export"],
        help="Choose between different application modes"
    )
    
    # Render selected page
    if page == "🎲 Matrix Generation":
        render_matrix_page()
    elif page == "🧬 FIBO Advanced":
        render_fibo_advanced_page()
    else:
        render_brand_export_page()


if __name__ == "__main__":
    main()
