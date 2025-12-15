"""
FIBO Omni-Director Pro - Streamlit Cloud Entry Point
Competition-Winning Deterministic Visual Production Studio
"""

import streamlit as st
import sys
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="FIBO Omni-Director Pro",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add frontend to path
frontend_path = Path(__file__).parent / "frontend"
sys.path.insert(0, str(frontend_path))

# Import and run the main app
try:
    from app.main import main
    
    # Display header
    st.markdown("""
    # 🏆 FIBO Omni-Director Pro
    
    > **Competition-Winning Deterministic Visual Production Studio**
    
    The world's first professional AI studio leveraging FIBO's full JSON-native capabilities.
    Built for the **Bria FIBO Hackathon 2025**.
    
    ---
    """)
    
    # Run the main application
    main()
    
except Exception as e:
    st.error(f"""
    ## 🚧 Setup Required
    
    **For Streamlit Cloud deployment:**
    1. Add your API keys to the Streamlit secrets
    2. Install requirements from `frontend/requirements.txt`
    
    **Error:** {str(e)}
    
    **Local development:** Use `./scripts/run_frontend.sh` instead
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