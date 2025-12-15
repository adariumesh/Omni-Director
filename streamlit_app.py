"""
FIBO Omni-Director Pro - Streamlit Cloud Entry Point
Competition-Winning Deterministic Visual Production Studio
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="FIBO Omni-Director Pro",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Display header
st.markdown("""
# 🏆 FIBO Omni-Director Pro

> **Competition-Winning Deterministic Visual Production Studio**

The world's first professional AI studio leveraging FIBO's full JSON-native capabilities.
Built for the **Bria FIBO Hackathon 2025**.

---
""")

# Add frontend to path and import
frontend_path = Path(__file__).parent / "frontend"
sys.path.insert(0, str(frontend_path))

# Check for API keys in secrets
if hasattr(st, 'secrets'):
    if 'BRIA_API_KEY' in st.secrets:
        os.environ['BRIA_API_KEY'] = st.secrets['BRIA_API_KEY']
    if 'OPENAI_API_KEY' in st.secrets:
        os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']

# Try to import and run the main app
try:
    from app.main import main
    main()
    
except ImportError as e:
    st.error(f"""
    ## 🚧 Import Error
    
    **Missing module:** {str(e)}
    
    **This is likely due to backend dependencies not being available in Streamlit Cloud.**
    """)
    
    # Show simplified demo interface
    st.markdown("""
    ## 🎯 FIBO Omni-Director Pro Features
    
    ### 🔒 Deterministic Matrix Generation
    - 3x3 grid with seed-locked consistency
    - Reproducible results every time
    - Professional workflow control
    
    ### 🧬 JSON DNA System  
    - 1000+ word structured parameter control
    - Disentangled attribute modification
    - VLM translation for prompt expansion
    
    ### ⚡ Three Generation Modes
    - **Generate**: Create new variations
    - **Refine**: Improve existing images  
    - **Inspire**: Explore creative directions
    
    ### 🛡️ Brand Guard System
    - Automated logo overlays and watermarking
    - Brand compliance checking
    - Color palette validation
    - Negative prompt injection
    
    ### 📦 Professional Export Engine
    - **Portfolio**: Interactive HTML gallery
    - **Archive**: Complete dataset with metadata
    - **Presentation**: High-res images for slides
    - **ZIP Packaging**: Automated compression
    
    ---
    
    ## 🚀 Live Demo
    
    **For the full interactive demo, run locally:**
    ```bash
    git clone https://github.com/adariumesh/Omni-Director
    cd Omni-Director
    ./scripts/run_frontend.sh
    ```
    
    **Or deploy with Docker:**
    ```bash
    ./deploy.sh
    ```
    """)
    
except Exception as e:
    st.error(f"""
    ## 🚧 Setup Required
    
    **For Streamlit Cloud deployment:**
    1. Add your API keys to the Streamlit secrets
    2. Some backend features require local deployment
    
    **Error:** {str(e)}
    
    **Full experience:** Run `./scripts/run_frontend.sh` locally
    """)
    
    # Show setup instructions
    st.markdown("""
    ## 📋 Streamlit Cloud Setup Instructions
    
    ### 1. Fork this repository to your GitHub
    
    ### 2. Deploy to Streamlit Cloud:
    - Go to [share.streamlit.io](https://share.streamlit.io)
    - Connect your GitHub repository
    - Set main file: `streamlit_app.py`
    
    ### 3. Configure Secrets:
    Add to your Streamlit app secrets:
    ```toml
    BRIA_API_KEY = "your_bria_production_api_key_here"
    OPENAI_API_KEY = "your_openai_api_key_here"
    DATABASE_URL = "sqlite:///./data/omni_director.db"
    ENVIRONMENT = "production"
    ```
    
    ### 4. Access Your Live Demo:
    Your app will be available at: `https://your-app-name.streamlit.app`
    
    ---
    
    ## 🚀 Features Ready for Demo:
    - ✅ **Deterministic Matrix**: 3x3 seed-locked grid generation
    - ✅ **JSON DNA System**: 1000+ word structured control
    - ✅ **Brand Guard**: Logo overlays & compliance checking  
    - ✅ **Export Engine**: Portfolio/Archive/Presentation formats
    - ✅ **Three Modes**: Generate, Refine, Inspire workflows
    
    **Perfect for Hackathon Judging!** 🏆
    """)