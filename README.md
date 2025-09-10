# Packing Form Parser API

A small FastAPI service that accepts a Bank of Baroda Packing Credit/PCFC form PDF, extracts structured fields, returns JSON, and stores them in a local SQLite database.

## Setup

```bash
# From project root (Windows PowerShell)
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` for Swagger UI.

## API

- POST `/upload` (multipart/form-data)
  - field `file`: the PDF file
  - Response: `{"id": <record_id>, "data": { ... parsed fields ... }}`

- GET `/records`
  - Returns all parsed records.

## Notes

- Parsing uses heuristics; consistent form layout yields best results. If some fields are missing, consider improving regex in `app/parser.py`.
- Database path can be changed with env var `PACKING_DB_PATH`.
