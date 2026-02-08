from langchain_ollama import OllamaEmbeddings
from langchain_community.embeddings.bedrock import BedrockEmbeddings
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure Ollama URL - supports both local and remote (ngrok)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")



def get_embedding_function():
    # embeddings = BedrockEmbeddings(
    #     credentials_profile_name="default", region_name="us-east-1"
    # )
    print(f"[DIAGNOSTIC] Initializing OllamaEmbeddings with base_url: {OLLAMA_BASE_URL}")
    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=OLLAMA_BASE_URL
    )
    print(f"[DIAGNOSTIC] OllamaEmbeddings initialized successfully")
    return embeddings
