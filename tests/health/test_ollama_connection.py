import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Ollama base URL from environment variable or use default
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Test endpoint (e.g., /api/tags)
url = f"{OLLAMA_BASE_URL}/api/tags"

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    print(f"Success! Ollama responded: {response.json()}")
except Exception as e:
    print(f"Failed to connect to Ollama at {url}\nError: {e}")
