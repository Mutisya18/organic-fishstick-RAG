# Organic Fishstick RAG Chatbot & Eligibility Module

## Setup Guide

### 1. Prerequisites
- **Hardware:** Minimum 8GB RAM, 2+ CPU cores, 10GB free disk space recommended
- **OS:** Linux, Windows, or Mac
- **Python:** Version 3.10 or higher
- **Ollama:** Install from https://ollama.com/download
- **ngrok:** For remote access, install from https://ngrok.com/

### 2. Environment Configuration
- Copy `.env.example` to `.env` and edit as needed
- Key variables:
    - `OLLAMA_BASE_URL`: Ollama server URL (local or ngrok)
    - `CONTEXT_MESSAGE_LIMIT`: Max previous messages for LLM context (default: 5)
    - `CHROMA_PATH`, `DATA_PATH`, `ELIGIBILITY_DATA_PATH`: Database/data paths
    - `LOG_DIR`: Log directory

### 3. Installing Dependencies
- Run: `pip install -r requirements.txt`
- Ensure Streamlit, Chroma, SQLAlchemy, and other packages are installed

### 4. Model Setup
- Pull required Ollama models:
    - `ollama pull nomic-embed-text`
    - `ollama pull llama3.2:3b`
- Start Ollama server:
    - `ollama serve` (ensure `OLLAMA_HOST=0.0.0.0:11434` for ngrok)

### 5. ngrok Forwarding (Remote Access)
- Start ngrok: `ngrok http 11434`
- Update `.env` with your ngrok URL for `OLLAMA_BASE_URL`
- Ensure Ollama is bound to `0.0.0.0` (not `127.0.0.1`) for external access

### 6. Database Initialization
- Run: `python rag/populate_database.py` (or use `start.sh`)
- Check logs for successful population (should see 90+ documents)

### 7. Starting the Application
- Run: `./start.sh` or `streamlit run app.py`
- Access the UI at `http://localhost:8501` or your ngrok URL

---

## Troubleshooting Guide

### 1. Common Issues
- **Ollama 403 Forbidden:**
    - Cause: Ollama bound to `127.0.0.1` (localhost only)
    - Fix: Restart Ollama with `OLLAMA_HOST=0.0.0.0:11434` and re-pull models
- **Database not populating:**
    - Check logs for errors
    - Ensure data files are present in `rag/data` and `eligibility/data`
- **Missing Python packages:**
    - Run `pip install -r requirements.txt` again
- **Streamlit not launching:**
    - Check Python version and package installation

### 2. Diagnostic Steps
- Check logs in `logs/` for errors and session details
- Test Ollama connectivity:
    - `curl http://localhost:11434/api/tags` (local)
    - `curl https://your-ngrok-url.ngrok-free.dev/api/tags` (remote)
- Verify database status:
    - Run `python tests/portal/test_context_flow.py` for context checks

### 3. Configuration Problems
- Double-check `.env` values
- Ensure models are downloaded and server is running
- Check for port conflicts (11434, 8501)

### 4. Performance Issues
- Slow LLM responses: Reduce `CONTEXT_MESSAGE_LIMIT` in `.env`
- Memory/CPU bottlenecks: Close unused apps, upgrade hardware

### 5. FAQ
- **How to change context message limit?**
    - Edit `CONTEXT_MESSAGE_LIMIT` in `.env` and restart app
- **How to update models?**
    - Run `ollama pull <model>`
- **How to reset database?**
    - Run `python rag/populate_database.py --reset`

### 6. Support & Contribution
- For help, open issues in GitHub repo
- Contributions welcome via pull requests

---