#!/bin/bash
# IntelliWeather - Quick Start Script

set -e

echo "🚀 IntelliWeather - Starting System..."
echo "======================================"

# Check Python version
python_version=$(python --version 2>&1)
echo "✓ $python_version"

# Check data directory
if [ ! -d "data" ]; then
    echo "Creating data directory..."
    mkdir -p data
fi
echo "✓ Data directory ready"

# Check environment file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.production .env
    echo "✓ Created .env file - PLEASE CONFIGURE IT!"
fi

# Install dependencies (if needed)
if [ ! -d "venv" ] && [ ! -f "/.dockerenv" ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt > /dev/null 2>&1
    echo "✓ Dependencies installed"
fi

# Start the application
echo ""
echo "🌟 Starting IntelliWeather API..."
echo "======================================"
echo "Access points:"
echo "  - Main site: http://localhost:8000"
echo "  - Dashboard: http://localhost:8000/static/dashboard.html"
echo "  - API Docs:  http://localhost:8000/docs"
echo "  - Metrics:   http://localhost:8000/metrics"
echo ""
echo "Press Ctrl+C to stop"
echo "======================================"

# Start uvicorn
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
