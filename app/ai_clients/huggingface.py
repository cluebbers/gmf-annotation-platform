"""HuggingFace Inference integration for predictions and chat."""

import json
from functools import lru_cache

from huggingface_hub import InferenceClient

from app.ai_clients.gmf_taxonomy import StructuredPrediction, build_incident_prompt
from app.config import settings


@lru_cache(maxsize=1)
def _get_hf_client() -> InferenceClient:
    return InferenceClient(
        provider=settings.hf_provider,
        api_key=settings.hf_token,
        timeout=settings.hf_timeout_seconds,
    )


def chat_completion(
    title: str | None,
    report_text: str,
    history: list[dict[str, str]],
    message: str,
    system_prompt: str = "",
) -> str:
    """Get chat completion for an incident.

    Args:
        title: Incident title.
        report_text: Incident report text.
        history: Chat history as list of {"role": "user"/"assistant", "content": "..."} dicts.
        message: User message.
        system_prompt: System prompt text.

    Returns:
        Chat completion response.

    Raises:
        RuntimeError: If HuggingFace request fails.
    """
    client = _get_hf_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": build_incident_prompt(title, report_text)},
        *history,
        {"role": "user", "content": message},
    ]
    try:
        response = client.chat_completion(
            messages=messages,
            model=settings.hf_model,
        )
    except Exception as exc:
        raise RuntimeError("HuggingFace request failed.") from exc
    return response.choices[0].message.content


def predict_incident(
    title: str | None,
    report_text: str,
    model_name: str | None = None,
    temperature: float | None = None,
    system_prompt: str = "",
) -> dict[str, object]:
    """Predict GMF labels for an incident using HuggingFace Inference.

    Args:
        title: Incident title.
        report_text: Incident report text.
        model_name: Optional model name override.
        temperature: Optional temperature override.
        system_prompt: System prompt text.

    Returns:
        Prediction result with labels, model name, and token counts.

    Raises:
        RuntimeError: If HuggingFace request fails or response cannot be parsed.
    """
    client = _get_hf_client()
    user_prompt = build_incident_prompt(title, report_text)
    model = model_name or settings.hf_model
    temp = temperature if temperature is not None else settings.hf_temperature

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "StructuredPrediction",
            "schema": StructuredPrediction.model_json_schema(),
            "strict": True,
        },
    }

    kwargs: dict[str, object] = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "model": model,
        "response_format": response_format,
        "temperature": temp,
    }
    if settings.hf_max_tokens is not None:
        kwargs["max_tokens"] = settings.hf_max_tokens

    try:
        response = client.chat_completion(**kwargs)
    except Exception as exc:
        raise RuntimeError("HuggingFace request failed.") from exc

    raw_content = response.choices[0].message.content
    try:
        parsed_dict = json.loads(raw_content)
        parsed = StructuredPrediction.model_validate(parsed_dict)
    except Exception as exc:
        raise RuntimeError(
            "HuggingFace response could not be parsed as StructuredPrediction."
        ) from exc

    usage = getattr(response, "usage", None)
    return {
        "known_ai_technical_failure": parsed.known_ai_technical_failure,
        "potential_ai_technical_failure": parsed.potential_ai_technical_failure,
        "model_name": model,
        "raw_response": raw_content,
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
    }
