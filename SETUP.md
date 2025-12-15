# 🎯 FIBO Omni-Director Pro - Setup Guide

## Current Status: Infrastructure Complete ✅

The application now has proper environment validation and health monitoring. Follow this guide to get everything running.

---

## 📋 Prerequisites

### Required
- **Python 3.10+** 
- **Git**
- **Internet connection** (for API calls)

### API Keys Needed
- **BRIA API Key** ([Get from bria.ai](https://bria.ai/))
- **OpenAI API Key** ([Get from OpenAI](https://platform.openai.com/api-keys))

---

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
# Clone the repository
cd "weapon/Omni - Director"

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies  
cd ../frontend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cd ..
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

**Required Environment Variables:**
```bash
# Get from https://bria.ai/
BRIA_API_KEY=your_actual_bria_api_key_here

# Get from https://platform.openai.com/api-keys  
OPENAI_API_KEY=your_actual_openai_api_key_here

# Optional - customize these as needed
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

### 3. Test Your Setup

```bash
# Start the backend
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# In another terminal, test health
curl "http://127.0.0.1:8000/api/v1/health/detailed" | python -m json.tool
```

**Expected Health Check Results:**
```json
{
  "overall_status": "available",
  "ready_for_production": true,
  "features_available": {
    "image_generation": true,
    "vlm_translation": true,
    "export": true,
    "brand_protection": true
  }
}
```

### 4. Start the Frontend

```bash
# In another terminal
cd frontend
streamlit run app/main.py --server.port 8501
```

Open **http://localhost:8501** in your browser.

---

## 🔍 Troubleshooting

### Common Issues

#### ❌ "BRIA_API key not configured"
```bash
# Check your .env file
cat .env | grep BRIA_API_KEY

# Make sure it's not a placeholder
BRIA_API_KEY=bria_xxxxxxxxxxxxx  # Should be real key
```

#### ❌ "Database connection failed"
```bash
# Check if data directory exists and is writable
ls -la data/
mkdir -p data  # Create if missing
chmod 755 data  # Ensure writable
```

#### ❌ "OpenAI API key invalid"
```bash
# Test your OpenAI key directly
curl -H "Authorization: Bearer your_key_here" \
  https://api.openai.com/v1/models
```

#### ❌ "File system not accessible"
```bash
# Check permissions
mkdir -p exports data
chmod 755 exports data
```

### Health Check Statuses

| Status | Meaning | Action |
|--------|---------|--------|
| `available` | ✅ Service working perfectly | Continue |
| `degraded` | ⚠️ Service partially working | Check warnings |
| `unavailable` | ❌ Service completely broken | Fix configuration |
| `not_configured` | ⚙️ Service not set up | Add API keys |

---

## 🎯 Feature Availability

### ✅ Currently Working
- **Environment Validation** - Comprehensive health checks
- **Database Operations** - SQLite with asset storage
- **File System** - Local storage and exports  
- **UI/API Structure** - Professional interface

### ⚠️ Requires API Keys
- **Image Generation** - Needs BRIA API key
- **VLM Translation** - Needs OpenAI API key
- **Advanced FIBO Features** - Needs both keys

### 🚧 In Development
- **Real Image Processing** - Currently using placeholder URLs
- **Multi-Provider Fallbacks** - Fal.ai, Replicate integration
- **Production Infrastructure** - Docker, PostgreSQL

---

## 🔧 Development Setup

### Environment Variables Reference

```bash
# Required APIs
BRIA_API_KEY=bria_xxxx                    # From bria.ai
OPENAI_API_KEY=sk-xxxx                    # From OpenAI

# Database  
DATABASE_URL=sqlite:///./data/omni_director.db

# Server Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=true
ENVIRONMENT=development

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Security (change in production)
SECRET_KEY=dev-secret-key
ALLOWED_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
```

### Testing Individual Components

```bash
# Test database
python -c "from app.models.database import init_db; init_db(); print('DB OK')"

# Test API validation
python -c "from app.services.environment_validator import EnvironmentValidator; v=EnvironmentValidator(); print(v.validate_environment())"

# Test FIBO endpoints
curl "http://127.0.0.1:8000/api/v1/fibo/modes"
```

---

## 📈 Next Steps

### Phase 2: Real API Integration
1. **Get BRIA API access** and test image generation
2. **Set up OpenAI API** for VLM translation  
3. **Test end-to-end workflows** with real images

### Phase 3: File Storage
1. **Implement image downloads** from API responses
2. **Build thumbnail generation** for UI
3. **Create export system** with real files

### Phase 4: Production Ready
1. **Docker configuration** for deployment
2. **PostgreSQL setup** for production database
3. **Security hardening** and performance optimization

---

## 🆘 Support

### Check System Status
```bash
# Detailed health check
curl "http://127.0.0.1:8000/api/v1/health/detailed"

# Simple health check  
curl "http://127.0.0.1:8000/api/v1/health"

# Feature availability
curl "http://127.0.0.1:8000/api/v1/health/detailed" | jq '.features_available'
```

### Debug Logs
```bash
# Backend logs
cd backend && python -m uvicorn app.main:app --log-level debug

# Frontend logs  
cd frontend && streamlit run app/main.py --logger.level debug
```

### Reset Everything
```bash
# Clean slate
rm -rf data/ exports/ __pycache__/ .pytest_cache/
rm backend/data/omni_director.db
python -m uvicorn app.main:app --reload
```

---

**🎯 Ready to build the future of image generation!**