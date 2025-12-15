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
