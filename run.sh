#!/bin/bash
# Kill any process running on port 8000
fuser -k 8000/tcp || true

# Install dependencies if not installed
pip install -r requirements.txt

# Start the server
echo "Starting Weather API on port 8000..."
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
