# Needed Endpoints

## Purpose

The canonical logical model for the MVP is:

- `incidents`
- `model_runs`
- `annotations` for both gold and prediction data
- `annotation_snippets`

## Required MVP Endpoints

### 1. Health

| Method | Path | Why it is needed |
| --- | --- | --- |
| `GET` | `/health` | Simple readiness and liveness check for backend and Docker setup |

### 2. Incidents

| Method | Path | Why it is needed |
| --- | --- | --- |
| `GET` | `/incidents` | List all incidents for the UI and API consumers |
| `POST` | `/incidents` | Create a new incident report |
| `GET` | `/incidents/{incident_id}` | Fetch one incident by ID |
| `PUT` | `/incidents/{incident_id}` | Update title, report text, or source URL |
| `DELETE` | `/incidents/{incident_id}` | Remove an incident and its related data |

Key request fields:

- `POST` and `PUT /incidents`: `title`, `report_text`, `source_url`

### 3. Gold Annotations

Even though gold annotations are stored in the shared `annotations` table, the
API should expose explicit gold routes because the frontend and the project
requirements treat gold labels as a separate workflow.

| Method | Path | Why it is needed |
| --- | --- | --- |
| `GET` | `/incidents/{incident_id}/gold-annotations` | List all gold annotations for one incident |
| `POST` | `/incidents/{incident_id}/gold-annotations` | Create a gold annotation for one incident |
| `GET` | `/gold-annotations/{annotation_id}` | Fetch one gold annotation |
| `PUT` | `/gold-annotations/{annotation_id}` | Update one gold annotation |
| `DELETE` | `/gold-annotations/{annotation_id}` | Delete one gold annotation |

Key request fields:

- `POST` and `PUT /gold-annotations`: `gmf_category`, `label`, `classification_discussion`

### 4. Annotation Snippets

Snippets are a separate resource because one annotation can have multiple pieces
of evidence.

| Method | Path | Why it is needed |
| --- | --- | --- |
| `GET` | `/annotations/{annotation_id}/snippets` | List evidence snippets for one annotation |
| `POST` | `/annotations/{annotation_id}/snippets` | Add a snippet to an annotation |
| `PUT` | `/snippets/{snippet_id}` | Update one snippet |
| `DELETE` | `/snippets/{snippet_id}` | Delete one snippet |

Key request fields:

- `POST` and `PUT /snippets`: `snippet_text`, `snippet_order`

### 5. Model Runs And Predictions

These endpoints cover the GenAI part of the project. A prediction request should
create one `model_run`, one or more `annotations` with `source = prediction`,
and their related `annotation_snippets`.

| Method | Path | Why it is needed |
| --- | --- | --- |
| `POST` | `/predict/{incident_id}` | Run one model on one incident and persist the result |
| `GET` | `/runs` | List all model runs |
| `GET` | `/runs/{run_id}` | Inspect one run including tokens, latency, status, and raw response |
| `GET` | `/runs/{run_id}/predictions` | Return prediction annotations for one run |
| `GET` | `/incidents/{incident_id}/predictions` | Return all predictions for one incident across runs |

Key request fields:

- `POST /predict/{incident_id}`: `model_name`, `prompt_version`

### 6. Comparison And Evaluation

These endpoints support the model comparison and grading workflow described in
the architecture and project plan.

| Method | Path | Why it is needed |
| --- | --- | --- |
| `POST` | `/compare/{incident_id}` | Run two models for one incident and compute inter-model agreement |
| `GET` | `/evaluation/incident/{incident_id}` | Compare stored predictions against gold annotations for one incident |
| `GET` | `/evaluation/summary` | Return aggregate metrics such as agreement, latency, cost, and JSON validity |

Key request fields:

- `POST /compare/{incident_id}`: `model_a`, `model_b`, `prompt_version`

## Recommended Response Expectations

- List endpoints should return arrays.
- Create endpoints should return the created resource, including its generated ID.
- Read endpoints should return the full resource representation.
- Update endpoints should return the updated resource.
- Delete endpoints can return either a small confirmation payload or `204 No Content`.
- Prediction and comparison endpoints should return both the stored run metadata and the structured annotation output.

## Recommended But Not Strictly Required For MVP

| Method | Path | Why it may be useful |
| --- | --- | --- |
| `POST` | `/predict/batch` | Helpful for bulk experiments and evaluation runs |
| `GET` | `/incidents/{incident_id}/runs` | Easier UI query for incident-specific run history |
| `GET` | `/meta/gmf-categories` | Lets the frontend populate dropdowns from the backend |
| `GET` | `/meta/models` | Lets the frontend discover available model options |

## Not Needed In The MVP

The current docs explicitly exclude these areas from scope:

- authentication endpoints
- role and permission endpoints
- human review workflow endpoints
- full GMF taxonomy management endpoints
- RAG or vector database endpoints
