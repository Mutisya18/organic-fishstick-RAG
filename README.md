# RAG Tutorial Setup Guide

This guide will walk you through setting up a RAG (Retrieval-Augmented Generation) system that uses Chroma for vector storage, Ollama for embeddings and LLM, and LangChain for orchestration.

## Prerequisites

- Python 3.8 or higher
- Ollama installed and running (or access to a remote Ollama instance)
- Git (optional, for version control)

## Step 1: Clone or Create Project Directory

```bash
# Create a new directory for your project
mkdir rag-tutorial-v2
cd rag-tutorial-v2
```

## Step 2: Set Up Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

## Step 3: Install Dependencies

```bash
# Install all required packages
pip install pypdf langchain langchain-community langchain-chroma langchain-ollama chromadb pytest boto3
```

Alternatively, if you have the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Step 4: Set Up Ollama

### Option A: Local Ollama Installation

1. **Install Ollama** from [ollama.ai](https://ollama.ai)

2. **Pull required models:**
```bash
ollama pull nomic-embed-text  # For embeddings
ollama pull llama3.2:3b       # For LLM responses
```

3. **Update configuration** in `get_embedding_function.py`:
```python
embeddings = OllamaEmbeddings(model="nomic-embed-text")
```

And in `query_data.py`:
```python
model = OllamaLLM(model="llama3.2:3b")
```

### Option B: Remote Ollama Instance

If using the ngrok URL (as in your files), ensure your remote Ollama instance is running and accessible.

## Step 5: Create Data Directory

```bash
# Create directory for PDF documents
mkdir data
```

## Step 6: Add PDF Documents

Place your PDF files in the `data` directory. For the tests to work, you'll need:
- A PDF with Monopoly rules
- A PDF with Ticket to Ride rules

Example:
```bash
# Example - download sample PDFs (replace with your actual PDFs)
# Place them in the data/ directory
```

## Step 7: Initialize the Vector Database

```bash
# First time setup - populate the database
python populate_database.py
```

This will:
- Load PDFs from the `data` directory
- Split documents into chunks
- Generate embeddings
- Store them in the Chroma vector database

If you need to reset the database:
```bash
python populate_database.py --reset
```

## Step 8: Query the System

```bash
# Ask a question
python query_data.py "How much money does a player start with in Monopoly?"
```

## Step 9: Run Tests (Optional)

```bash
# Run the test suite
pytest test_rag.py -v
```

## Project Structure

```
rag-tutorial-v2/
├── rag/                           # RAG module
│   ├── data/                      # PDF documents go here
│   ├── chroma/                    # Vector database (auto-created)
│   ├── config/                    # Configuration (prompts)
│   ├── get_embedding_function.py  # Embedding configuration
│   ├── populate_database.py       # Database population script
│   ├── query_data.py              # Query interface
│   └── test_rag.py                # Test suite
├── eligibility/                   # Eligibility module
├── logger/                        # Logging module
├── venv/                          # Virtual environment
├── requirements.txt               # Python dependencies
├── .gitignore                     # Git ignore rules
└── README.md                      # Project readme
```

## Common Commands

### Adding New Documents
```bash
# Add PDFs to data/ directory, then run:
python populate_database.py
```

### Resetting the Database
```bash
python populate_database.py --reset
```

### Querying
```bash
python rag/query_data.py "Your question here"
```

### Running Tests
```bash
pytest rag/test_rag.py -v
```

## Troubleshooting

### Issue: "Connection refused" or Ollama errors
- **Solution**: Ensure Ollama is running (`ollama serve`)
- Check if models are downloaded (`ollama list`)

### Issue: No documents found
- **Solution**: Verify PDFs are in the `data/` directory
- Check PDF format is valid

### Issue: Database errors
- **Solution**: Try resetting: `python populate_database.py --reset`

### Issue: Import errors
- **Solution**: Ensure virtual environment is activated and dependencies are installed

## Configuration Options

### Chunk Size Settings
In `rag/populate_database.py`, adjust chunking parameters:
```python
chunk_size=800,      # Characters per chunk
chunk_overlap=80,    # Overlap between chunks
```

### Number of Results
In `rag/query_data.py`, adjust the number of relevant chunks retrieved:
```python
results = db.similarity_search_with_score(query_text, k=5)  # Change k value
```

### Using AWS Bedrock (Alternative)
Uncomment in `rag/get_embedding_function.py`:
```python
embeddings = BedrockEmbeddings(
    credentials_profile_name="default", 
    region_name="us-east-1"
)
```

## Next Steps

1. Add your PDF documents to the `data/` directory
2. Run `populate_database.py` to index them
3. Start querying with `query_data.py`
4. Customize the prompt template in `query_data.py` for your use case
5. Write additional tests in `test_rag.py`

## Notes

- The `.gitignore` file excludes the `chroma/` directory and backup files from version control
- Embeddings are generated using the `nomic-embed-text` model
- Responses are generated using `llama3.2:3b`
- The system uses similarity search to find relevant document chunks
- Context from top 5 most similar chunks is used to answer questions