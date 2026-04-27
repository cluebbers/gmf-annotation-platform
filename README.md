# GMF Annotation Platform

> Multi-provider LLM annotation platform that classifies real-world AI incidents against the GMF taxonomy and evaluates predicted labels against expert gold annotations.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?logo=google&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Inference-FFD21E?logo=huggingface&logoColor=black)

---

## Why this project?

The [AI Incident Database (AIID)](https://incidentdatabase.ai/) records real-world AI failures, and the [Global AI Fault (GMF) taxonomy](https://aiid.partnershiponai.org/gmf/) provides a structured vocabulary for categorising those failures — but applying that vocabulary at scale requires expert annotators. This platform automates that annotation step: it ingests AIID incident reports, runs structured LLM predictions against the full GMF label set, and measures how closely each model's output matches expert gold labels using precision, recall, and F1. The result is a reproducible pipeline for evaluating LLM suitability as annotation assistants in an AI safety research context.

---

## Architecture

```text
AIID backup (.tar.bz2)
        │
        ▼
 import script ──────────────────────────────────────────────┐
        │                                                     │
        ▼                                                     ▼
  PostgreSQL  ◄──── FastAPI backend (/incidents, /predict, /compare)
                           │
                           ├── OpenAI (GPT-4o, gpt-4o-mini, …)
                           ├── Google Gemini (gemini-2.0-flash, …)
                           └── HuggingFace Inference API
                                       ▲
                           Streamlit frontend
```

| Layer | Responsibility |
| --- | --- |
| **Import script** | Parses the AIID backup, upserts incidents, replaces gold annotations, clears stale predictions |
| **PostgreSQL** | Stores incidents, model runs, and annotations (gold + predicted) in three normalised tables |
| **FastAPI backend** | REST API: serves incidents, dispatches predictions to the configured provider, runs cross-model evaluation |
| **LLM providers** | OpenAI, Gemini, and HuggingFace — all behind a single `predict_incident()` interface |
| **Streamlit frontend** | Browse incidents, run predictions, compare gold vs predicted labels, view cross-model evaluation metrics |

---

## Technical Highlights

**Unified multi-provider interface**
All three providers — OpenAI (`client.responses.parse`), Google Gemini (`response_schema` + `response_mime_type`), and HuggingFace (`InferenceClient` with manual JSON parsing) — expose the same two entry points: `predict_incident()` and `chat_completion()`. The backend resolves the provider from the model name at runtime (`gemini-*` → Google, `org/model` → HuggingFace, everything else → OpenAI) with no branching in callers.

**Structurally enforced taxonomy**
GMF labels are declared as `Literal` types in `gmf_taxonomy.py`. Pydantic's `StructuredPrediction` model uses those types directly, so a label that isn't in the taxonomy cannot survive deserialisation — hallucination is caught at the type boundary, not in validation logic. The system prompt is also generated from the same `Literal` definitions, keeping prompt and schema in sync automatically.

**Evaluation pipeline**
`GET /compare` iterates over every gold-set incident, finds the most recent successful `ModelRun` matching the requested `(model_name, prompt_version, temperature)` triple, and computes per-label TP/FP/FN before aggregating to precision/recall/F1 for each GMF category. The Streamlit frontend exposes this as an interactive model comparison tab.

**Idempotent import**
Re-running the import script is safe: incidents are upserted, gold annotations are replaced from the latest archive, and predicted annotations for modified incidents are cleared so stale model runs don't pollute evaluation results.

---

## Features

- Browse and full-text search imported AIID incidents
- See at a glance whether an incident belongs to the gold evaluation set
- Run a prediction against any configured model — OpenAI, Gemini, or HuggingFace
- Compare predicted labels against gold annotations side by side
- Inspect raw model run metadata: model name, prompt version, token counts, latency
- Cross-model evaluation: precision / recall / F1 per GMF category across the full gold set
- Interactive model comparison tab with configurable model, prompt version, and temperature

---

## Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- [`uv`](https://github.com/astral-sh/uv)
- API keys for whichever providers you want to use (see [Environment Variables](#environment-variables))

### Quick start

```bash
# Start Postgres
docker compose up -d postgres

# Install dependencies
uv sync

# Import AIID incident data and gold labels (idempotent — safe to re-run)
uv run python scripts/import_aiid_backup.py

# Start backend (terminal 1)
uv run uvicorn app.main:app --reload

# Start frontend (terminal 2)
uv run streamlit run app/frontend/streamlit_app.py
```

The API is available at `http://localhost:8000` and the Streamlit UI at `http://localhost:8501`.

### Custom backup archive

```bash
uv run python scripts/import_aiid_backup.py /path/to/backup.tar.bz2
```

---

## API Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/incidents` | List all incidents (supports search) |
| `GET` | `/incidents/{id}` | Incident detail with gold annotations if available |
| `POST` | `/predict/{id}` | Run a prediction for an incident; stores a `ModelRun` and `Annotation` rows |
| `GET` | `/system-prompt` | Return the current system prompt |
| `POST` | `/chat/{id}` | Chat completion scoped to an incident |
| `GET` | `/compare/configs` | Available models grouped by provider, prompt versions, temperatures |
| `GET` | `/compare` | Per-category precision/recall/F1 for a given `(model_name, prompt_version, temperature)` |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the keys for the providers you want to use.

| Variable | Default | Description |
| --- | --- | --- |
| `POSTGRES_HOST` | `localhost` | |
| `POSTGRES_PORT` | `5432` | |
| `POSTGRES_DB` | `gmf_annotation` | |
| `POSTGRES_USER` | `postgres` | |
| `POSTGRES_PASSWORD` | `postgres` | |
| `OPENAI_API_KEY` | — | Required for OpenAI predictions |
| `OPENAI_MODEL` | `gpt-4o-mini` | Default model shown in the UI |
| `OPENAI_PROMPT_VERSION` | `v1` | |
| `OPENAI_TEMPERATURE` | `0.0` | |
| `OPENAI_MAX_COMPLETION_TOKENS` | — | Leave blank for model default |
| `OPENAI_TIMEOUT_SECONDS` | `30` | |
| `GOOGLE_API_KEY` | — | Required for Gemini predictions |
| `GOOGLE_PROMPT_VERSION` | `v1` | |
| `GOOGLE_TEMPERATURE` | `0.0` | |
| `GOOGLE_MAX_OUTPUT_TOKENS` | — | |
| `GOOGLE_TIMEOUT_SECONDS` | `30` | |
| `HF_TOKEN` | — | Required for HuggingFace predictions |
| `HF_PROVIDER` | `auto` | HuggingFace inference provider |
| `HF_PROMPT_VERSION` | `v1` | |
| `HF_TEMPERATURE` | `0.0` | |
| `HF_MAX_TOKENS` | — | |
| `HF_TIMEOUT_SECONDS` | `60` | |
| `API_BASE_URL` | `http://localhost:8000` | Consumed by the Streamlit frontend, not the backend |

> Browsing incidents works without any API key. Prediction requests fail gracefully if the relevant key is unset.

---

## Data Model

```text
incidents          model_runs              annotations
──────────         ──────────              ───────────
id                 id                      id
incident_id        incident_id ──────────► incident_id
title              model_name              gmf_category
report_text        provider                label
is_gold_set        prompt_version          source (gold | prediction)
                   temperature             model_run_id ──► model_runs.id
                   input_tokens
                   output_tokens
                   latency_ms
                   status
                   raw_response (JSON)
                   created_at
```

Gold annotations share the `annotations` table with predicted ones, distinguished by `source`. This means evaluation queries are a single join — no separate gold table to keep in sync.
