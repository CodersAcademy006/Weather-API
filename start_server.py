import os
import sys
import subprocess
import time

def install_dependencies():
    print("📦 Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def start_server():
    print("🚀 Starting Weather API Server...")
    print("👉 Please open: http://localhost:8000")
    # Run uvicorn
    subprocess.run([sys.executable, "-m", "uvicorn", "app:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])

if __name__ == "__main__":
    try:
        install_dependencies()
        start_server()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
