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
