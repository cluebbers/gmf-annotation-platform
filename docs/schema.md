# Database Schema

## Overview

The GMF Annotation Platform uses a small relational schema for storing:

- incident reports
- model runs
- gold annotations
- model predictions
- evidence snippets

The schema is intentionally minimal for the MVP.

## Supported GMF Scope

The MVP only supports two GMF categories:

- `known_ai_technical_failure`
- `potential_ai_technical_failure`

## Design Principles

- one incident can have multiple annotations
- one annotation can have multiple snippets
- gold annotations and model predictions share the same annotation structure
- predictions are linked to a model run
- gold annotations are not linked to a model run

---

## Enums

### `run_status`

Defines the status of a model execution.

Allowed values:

- `success`
- `failed`

### `annotation_source`

Defines whether an annotation is manual gold data or model-generated.

Allowed values:

- `gold`
- `prediction`

### `gmf_category`

Defines the supported GMF category in the MVP.

Allowed values:

- `known_ai_technical_failure`
- `potential_ai_technical_failure`

---

## Tables

## 1. `incidents`

Stores the incident reports that will be classified.

### Fields

- `id`  
  Primary key
- `title`  
  Optional short title
- `report_text`  
  Main incident text used for annotation
- `source_url`  
  Optional source URL
- `created_at`  
  Timestamp of creation

### Example

```text
id: 1
title: Google Photos mislabeling incident
report_text: Google has been forced to apologise...
source_url: https://example.com
```

---

## 2. `model_runs`

Stores one model execution for one incident.

A single incident can have multiple model runs, for example:

- one run with OpenAI
- one run with Gemini
- repeated runs with different prompt versions

### Fields

- `id`
  Primary key
- `incident_id`
  Foreign key to `incidents.id`
- `model_name`
  Name of the model, e.g. `gpt-4.1`
- `prompt_version`
  Version label for the prompt, e.g. `v1`
- `status`
  `success` or `failed`
- `latency_ms`
  Request latency in milliseconds
- `input_tokens`
  Number of input tokens
- `output_tokens`
  Number of output tokens
- `estimated_cost_usd`
  Approximate request cost
- `raw_response`
  Raw model response for debugging
- `created_at`
  Timestamp of creation

### Relationship

- one `incident` → many `model_runs`

---

## 3. `annotations`

Stores both:

- gold annotations
- prediction annotations

This avoids duplicate table structures.

### Fields

- `id`
  Primary key
- `incident_id`
  Foreign key to `incidents.id`
- `source`
  `gold` or `prediction`
- `model_run_id`
  Nullable foreign key to `model_runs.id`
  `NULL` for gold annotations
- `gmf_category`
  One of the supported GMF categories
- `label`
  The GMF label, e.g. `Underfitting`
- `classification_discussion`
  Optional short reasoning text
- `created_at`
  Timestamp of creation

### Relationship

- one `incident` → many `annotations`
- one `model_run` → many prediction `annotations`
- gold annotations have no `model_run_id`

### Examples

#### Gold annotation

```text
incident_id: 1
source: gold
model_run_id: NULL
gmf_category: known_ai_technical_failure
label: Underfitting
classification_discussion: The report explicitly describes a misclassification failure.
```

#### Prediction annotation

```text
incident_id: 1
source: prediction
model_run_id: 12
gmf_category: potential_ai_technical_failure
label: Dataset Imbalance
classification_discussion: This is suggested but not directly confirmed in the report.
```

---

## 4. `annotation_snippets`

Stores one or more evidence snippets for one annotation.

This table is separate because:

- one annotation can have multiple snippets
- snippets should stay normalized
- snippets belong to both gold annotations and predictions

### Fields

- `id`
  Primary key
- `annotation_id`
  Foreign key to `annotations.id`
- `snippet_text`
  The evidence snippet text
- `snippet_order`
  Order of snippets within one annotation
- `created_at`
  Timestamp of creation

### Relationship

- one `annotation` → many `annotation_snippets`

### Example

```text
annotation_id: 5
snippet_text: Google has been forced to apologise after its image recognition software mislabelled photographs of black people as gorillas.
snippet_order: 1
```

---

## Entity Relationships

### One-to-many relationships

- `incidents` → `model_runs`
- `incidents` → `annotations`
- `model_runs` → `annotations`
- `annotations` → `annotation_snippets`

### Summary

- one incident can have many gold annotations
- one incident can have many prediction annotations
- one prediction run can generate many annotations
- one annotation can have many snippets

---

## Why this schema fits the GMF reality

The GMF data structure is not “one label per incident”.
A single incident can contain:

- multiple labels
- labels from different GMF categories
- multiple snippets per label

This schema supports that structure while keeping the MVP small.

For the MVP, the schema supports only:

- `known_ai_technical_failure`
- `potential_ai_technical_failure`

Later, additional GMF categories can be added by extending the `gmf_category` enum.

---

## Future Extensions

Possible later additions:

- more GMF categories
- users / authentication
- evaluation result table
- prompt registry
- model config table
- batch job tracking

These are not required for the MVP.
