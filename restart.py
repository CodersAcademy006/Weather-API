#!/usr/bin/env python3
import subprocess
import sys
import signal
import time
import os

def kill_existing_server():
    """Kill any existing uvicorn process on port 8000"""
    try:
        subprocess.run(["fuser", "-k", "8000/tcp"], stderr=subprocess.DEVNULL)
        time.sleep(1)
    except:
        pass

def start_server():
    """Start the FastAPI server"""
    print("\n" + "="*60)
    print("🚀 Starting Weather API Server")
    print("="*60)
    print("📍 Server will be available at: http://localhost:8000")
    print("🌐 In Codespaces: Open PORTS tab → Click globe icon on port 8000")
    print("="*60 + "\n")
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")

if __name__ == "__main__":
    kill_existing_server()
    start_server()
