#!/bin/bash
# Production setup script for FIBO Omni-Director Pro

set -e  # Exit on any error

echo "🚀 Setting up FIBO Omni-Director Pro for Production"
echo "=================================================="

# Check requirements
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed."; exit 1; }

# Create production environment file
if [ ! -f .env.production ]; then
    echo "📝 Creating production environment file..."
    cat > .env.production << EOF
# Production Environment Configuration
ENVIRONMENT=production
DEBUG=false

# Bria API (REQUIRED - Set your actual API key)
BRIA_API_KEY=your_production_api_key_here

# Database
DATABASE_URL=sqlite:///./data/omni_director.db

# Server
HOST=0.0.0.0
PORT=8000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security (CHANGE THESE IN PRODUCTION)
SECRET_KEY=$(openssl rand -hex 32)
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# File Storage
MAX_FILE_SIZE=10485760
UPLOAD_PATH=./data/uploads
EOF
    echo "✅ Created .env.production (Please update BRIA_API_KEY and ALLOWED_ORIGINS)"
else
    echo "ℹ️  .env.production already exists"
fi

# Create production data directories
echo "📁 Creating production directories..."
mkdir -p data/images data/uploads logs ssl

# Create nginx configuration
if [ ! -f nginx.conf ]; then
    echo "🌐 Creating nginx configuration..."
    cat > nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }
    
    upstream frontend {
        server frontend:8501;
    }
    
    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone \$binary_remote_addr zone=web:10m rate=50r/s;
    
    server {
        listen 80;
        server_name localhost;
        
        # Security headers
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options DENY;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
        
        # API endpoints
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        }
        
        # Frontend
        location / {
            limit_req zone=web burst=50 nodelay;
            proxy_pass http://frontend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            
            # WebSocket support for Streamlit
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
EOF
    echo "✅ Created nginx.conf"
fi

# Create production deployment script
cat > deploy.sh << 'EOF'
#!/bin/bash
# Production deployment script

set -e

echo "🚀 Deploying FIBO Omni-Director Pro"
echo "=================================="

# Load production environment
export $(cat .env.production | xargs)

# Validate required environment variables
if [ "$BRIA_API_KEY" = "your_production_api_key_here" ]; then
    echo "❌ Please set BRIA_API_KEY in .env.production"
    exit 1
fi

# Build and start services
echo "🐳 Building and starting Docker services..."
docker-compose -f docker-compose.yml --env-file .env.production up -d --build

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
if curl -f http://localhost:8000/api/v1/health >/dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend is not responding"
    docker-compose logs backend
    exit 1
fi

echo "🎉 Deployment complete!"
echo "Frontend: http://localhost"
echo "API: http://localhost/api/v1/docs"
EOF

chmod +x deploy.sh
echo "✅ Created deploy.sh"

# Create production health check script
cat > health_check.sh << 'EOF'
#!/bin/bash
# Production health check script

echo "🔍 Health Check Results"
echo "====================="

# Check backend
if curl -f http://localhost/api/v1/health >/dev/null 2>&1; then
    echo "✅ Backend API: Healthy"
else
    echo "❌ Backend API: Unhealthy"
fi

# Check frontend
if curl -f http://localhost >/dev/null 2>&1; then
    echo "✅ Frontend: Healthy" 
else
    echo "❌ Frontend: Unhealthy"
fi

# Check disk space
DISK_USAGE=$(df -h ./data | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "⚠️  Disk Usage: ${DISK_USAGE}% (Warning: >80%)"
else
    echo "✅ Disk Usage: ${DISK_USAGE}%"
fi

# Check logs for errors
ERROR_COUNT=$(docker-compose logs --since 1h 2>/dev/null | grep -i error | wc -l)
echo "📊 Recent Errors (1h): $ERROR_COUNT"

echo "====================="
EOF

chmod +x health_check.sh
echo "✅ Created health_check.sh"

echo ""
echo "🎉 Production setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env.production with your actual Bria API key"
echo "2. Update ALLOWED_ORIGINS in .env.production with your domain"
echo "3. Run: ./deploy.sh"
echo "4. Monitor with: ./health_check.sh"
echo ""
echo "📚 Documentation: See README.md for more details"