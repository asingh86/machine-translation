# Translation API
 
A RESTful API serving a machine translation model using FastAPI and HuggingFace Transformers.
 
## Setup
 
```bash
# Install dependencies
uv sync
 
# Run the API
uv run uvicorn app.main:app --reload
 
# Run tests
uv run pytest
 
# Lint
uv run ruff check .
```
 
## Project Structure
 
```
app/
├── main.py                 # FastAPI app with lifespan
├── config.py               # Settings via environment variables
├── api/routes.py           # Endpoint handlers
├── models/registry.py      # Model loading and translation
├── schemas/translation.py  # Request/response models
└── middleware/safeguard.py  # Content filtering
tests/
└── ...
```
 
## Status

Work in progress — see git history for incremental development.