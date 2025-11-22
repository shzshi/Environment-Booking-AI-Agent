#!/usr/bin/env python3
"""
Simple script to run the Flask application.
This script sets up the proper environment and imports the Flask app.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
project_root = Path(__file__).parent
load_dotenv(project_root / '.env', override=True)

# Add the src directory to Python path
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Set default environment variables (only if not already set)
os.environ.setdefault('PROJECT_NAME', 'Environment Booking Tool')
os.environ.setdefault('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
os.environ.setdefault('TEMPERATURE', '0.0')
os.environ.setdefault('GROQ_MODEL_NAME', 'llama3-8b-8192')
os.environ.setdefault('OLLAMA_MODEL_NAME', '')
os.environ.setdefault('GEMINI_MODEL_NAME', '')
os.environ.setdefault('LANGCHAIN_TRACING_V2', 'true')
os.environ.setdefault('LANGCHAIN_ENDPOINT', 'https://api.smith.langchain.com')
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('FLASK_DEBUG', 'True')

# Print current environment for debugging
print(f"GROQ_API_KEY is set: {'Yes' if os.getenv('GROQ_API_KEY') else 'No'}")
print(f"GROQ_MODEL_NAME: {os.getenv('GROQ_MODEL_NAME')}")

# Import and run the Flask app
from app import app

if __name__ == '__main__':
    print("Starting Flask application...")
    print("Access the application at: http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
