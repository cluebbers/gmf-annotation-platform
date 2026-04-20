# GMF Annotation Platform

This repository is a small MVP for a single workflow:

1. import AIID incidents and GMF gold labels from an AIID backup
2. browse incidents in a small Streamlit UI
3. run one OpenAI prediction per incident
4. compare predicted labels against imported gold labels when they exist

The MVP only supports these two GMF categories:

- `known_ai_technical_failure`
- `potential_ai_technical_failure`

## Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- `uv`
- `OPENAI_API_KEY` only if you want to run predictions

### If You Used An Older Version

This MVP uses a simplified schema. If you already ran an older version of the project, reset the local Postgres volume before reimporting:

```bash
docker compose down -v
```

### Environment File

Copy `.env.example` to `.env` and adjust values if needed.

Important defaults:

- Postgres runs on `localhost:5432`
- the default database is `gmf_annotation`
- the frontend expects the API at `http://localhost:8000`
- the default OpenAI model is `gpt-4o-mini`

### Install And Run

```bash
docker compose up -d postgres
uv sync
uv run python scripts/import_aiid_backup.py
uv run uvicorn app.main:app --reload
uv run streamlit run app/frontend/streamlit_app.py
```

Run the `uvicorn` and `streamlit` commands in separate terminals.

The backend starts on `http://localhost:8000` and the Streamlit app usually starts on `http://localhost:8501`.

### Import Data

The import script reads AIID incidents and GMF gold labels from a `.tar.bz2` backup archive.

By default it uses:

```text
backup-20260330103116.tar.bz2
```

You can also pass a custom archive path:

```bash
uv run python scripts/import_aiid_backup.py /path/to/backup.tar.bz2
```

Re-running the import is supported:

- incidents are inserted or updated
- gold annotations are replaced from the latest import
- saved predictions for changed incidents are cleared and must be regenerated

## Environment Variables

See `.env.example` for the full list.

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_PROMPT_VERSION`
- `OPENAI_TEMPERATURE`
- `OPENAI_MAX_COMPLETION_TOKENS`
- `OPENAI_TIMEOUT_SECONDS`
- `API_BASE_URL`

Notes:

- `API_BASE_URL` is used by the Streamlit frontend, not the FastAPI backend
- if `OPENAI_API_KEY` is unset, browsing incidents still works but prediction requests fail

## Frontend

The Streamlit frontend lets you:

- browse imported incidents
- search by incident id, title, or report text
- see whether an incident belongs to the gold set
- inspect gold annotations when they exist
- run a prediction and compare the predicted labels against the gold labels side by side
- inspect the saved model run metadata for that prediction

## API

The runtime API exposes three endpoints:

- `GET /incidents`
- `GET /incidents/{incident_id}` returns the incident detail and, for gold incidents, categorized `gold_annotations`
- `POST /predict/{incident_id}`

`POST /predict/{incident_id}`:

- sends the incident title and report text to the configured OpenAI model
- stores a `model_run` row
- stores predicted annotation rows
- returns the predicted labels and model run metadata

The API does not compute dataset-level evaluation metrics.

## Notes

- imported incidents are read-only in this MVP
- gold labels come from the AIID backup import and are not edited in the app
- predictions are also persisted, so running prediction for the same incident again creates another model run and another set of predicted annotations
- database tables are initialized on backend startup when Postgres is reachable

## Future Work

- [ ] additional model support through build.nvidia.com
- [x] model comparison
- [ ] prompt and parameter experiments

## Project requirements

- [x] Flask API - 2 POST endpoints & 2 GET endpoints
- [x] SQLite DB - 2 Tables inserting and reading entries
- [x] 1 Text Generation endpoint updating the DB
- [x] Structured output
- [x] Use case specific Comparative analysis
- [ ] 2 prompt engineering techniques
- [x] Retaining Conversation History
