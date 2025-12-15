# 🚀 Deployment Instructions

## Streamlit Cloud Deployment (Recommended for Hackathon)

### 1. Repository Setup ✅ 
Your code is already at: `https://github.com/adariumesh/Omni-Director`

### 2. Deploy to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub account
3. Select repository: `adariumesh/Omni-Director`
4. Main file: `streamlit_app.py`
5. Click "Deploy"

### 3. Configure API Keys
In your Streamlit app settings → Secrets, add:
```toml
BRIA_API_KEY = "your_bria_api_key"
OPENAI_API_KEY = "your_openai_api_key"
DATABASE_URL = "sqlite:///./data/omni_director.db"
ENVIRONMENT = "production"
```
(See API_KEYS.md for actual values - local file only)

### 4. Your Live Demo
Will be available at: `https://your-app-name.streamlit.app`

## Local Development

### Quick Start
```bash
./scripts/run_backend.sh    # Terminal 1
./scripts/run_frontend.sh   # Terminal 2
```

### Docker Production
```bash
./deploy.sh
```

## 🎯 Perfect for Hackathon Showcase!
- ✅ Public URL for judges
- ✅ No server management needed  
- ✅ All features available
- ✅ Professional presentation

🏆 Ready to win the Bria FIBO Hackathon!