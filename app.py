import os
import sys
import uvicorn

# Add backend directory to sys.path so internal imports inside 'backend' resolve correctly
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Import the FastAPI application instance from backend/main.py
from main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
