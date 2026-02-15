# Portal UI

Web UI for the NCBA Operations Assistant. Same backend as the Streamlit app (RAG, eligibility, database).

## Run the portal

From the project root:

```bash
bash start_portal.sh
```

Then open **http://localhost:8000**.

## Run both UIs (dev)

```bash
bash start_dev.sh
```

- Streamlit: http://localhost:8501  
- Portal: http://localhost:8000  

## Environment

Uses the same `.env` as the main app (database, RAG, eligibility). Ensure the database and RAG are set up (e.g. run `bash start.sh` once) before using the portal.

## Features

- Single conversation per user (get/create on init).
- Chat over `POST /api/chat/send` using the same RAG and eligibility pipeline as Streamlit.
- Dark mode (persisted in `localStorage`).
- Quick action cards for common prompts.
