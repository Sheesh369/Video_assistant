#!/usr/bin/env python3
"""
Startup script for HeyGen Avatar Chat Application
This script helps you set up and run the backend server with proper configuration checks.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ Error: .env file not found")
        print("Please create a .env file with your API keys")
        print("Use the provided .env example as template")
        return False
    
    required_vars = [
        "HEYGEN_API_KEY",
        "OPENROUTER_API_KEY"
    ]
    
    env_content = env_path.read_text()
    missing_vars = []
    
    for var in required_vars:
        if f"{var}=" not in env_content or f"{var}=your_" in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing or incomplete environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print("✅ Environment variables configured")
    return True

def install_dependencies():
    """Install Python dependencies"""
    try:
        print("📦 Installing Python dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def start_server():
    """Start the FastAPI server"""
    try:
        print("🚀 Starting HeyGen Avatar Chat server...")
        print("Server will be available at: http://localhost:8000")
        print("Press Ctrl+C to stop the server")
        print("-" * 50)
        
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

def main():
    """Main startup sequence"""
    print("🎭 HeyGen Avatar Chat - Startup Script")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Check if we're in a virtual environment (recommended)
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Not running in a virtual environment")
        print("It's recommended to use a virtual environment")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Create a virtual environment with:")
            print("  python -m venv venv")
            print("  source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
            sys.exit(1)
    else:
        print("✅ Running in virtual environment")
    
    # Check environment file
    if not check_env_file():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Start server
    start_server()

if __name__ == "__main__":
    main()