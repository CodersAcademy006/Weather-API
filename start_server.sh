#!/bin/bash
# IntelliWeather API Server Startup Script
# This script properly starts the Weather API server with uvicorn

cd /workspaces/Weather-API

# Kill any existing instances
pkill -f "uvicorn app:app" || true
sleep 1

echo "Starting IntelliWeather API Server..."
echo "=================================="
echo ""

# Start uvicorn with proper configuration
python -m uvicorn app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info

# Note: Use --reload for development (auto-restart on code changes)
# For production, remove --reload and add --workers 4
