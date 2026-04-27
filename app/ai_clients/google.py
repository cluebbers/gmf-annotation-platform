"""Google AI integration for predictions and chat."""

from functools import lru_cache

from google import genai
from google.genai import types

from app.ai_clients.gmf_taxonomy import (
    SYSTEM_PROMPT,
    StructuredPrediction,
    build_incident_prompt,
)
from app.config import settings


@lru_cache(maxsize=1)
def _get_google_client() -> genai.Client:
    return genai.Client(
        api_key=settings.google_api_key,
        http_options=types.HttpOptions(timeout=settings.google_timeout_seconds * 1000),
    )


def chat_completion(
    title: str | None,
    report_text: str,
    history: list[dict[str, str]],
    message: str,
) -> str:
    """Get chat completion for an incident.

    Args:
        title: Incident title.
        report_text: Incident report text.
        history: Chat history as list of {"role": "user"/"assistant", "content": "..."} dicts.
        message: User message.

    Returns:
        Chat completion response.

    Raises:
        RuntimeError: If Google request fails.
    """
    client = _get_google_client()

    contents = [
        {
            "role": "user",
            "parts": [{"text": build_incident_prompt(title, report_text)}],
        },
        *[
            {"role": "model" if m["role"] == "assistant" else m["role"], "parts": [{"text": m["content"]}]}
            for m in history
        ],
        {"role": "user", "parts": [{"text": message}]},
    ]
    try:
        response = client.models.generate_content(
            model=settings.google_model,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=settings.google_temperature,
            ),
            contents=contents,
        )
    except Exception as exc:
        raise RuntimeError("Google request failed.") from exc
    return response.text


def predict_incident(
    title: str | None,
    report_text: str,
    model_name: str | None = None,
    temperature: float | None = None,
) -> dict[str, object]:
    """Predict GMF labels for an incident using Google AI.

    Args:
        title: Incident title.
        report_text: Incident report text.
        model_name: Optional model name override.
        temperature: Optional temperature override.

    Returns:
        Prediction result with labels, model name, and token counts.

    Raises:
        RuntimeError: If Google request fails.
    """
    client = _get_google_client()
    user_prompt = build_incident_prompt(title, report_text)
    model = model_name or settings.google_model
    temp = temperature if temperature is not None else settings.google_temperature

    config_kwargs: dict[str, object] = {
        "system_instruction": SYSTEM_PROMPT,
        "temperature": temp,
        "response_mime_type": "application/json",
        "response_schema": StructuredPrediction,
    }
    if settings.google_max_output_tokens is not None:
        config_kwargs["max_output_tokens"] = settings.google_max_output_tokens

    try:
        response = client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(**config_kwargs),
            contents=user_prompt,
        )
    except Exception as exc:
        raise RuntimeError("Google request failed.") from exc

    parsed: StructuredPrediction | None = response.parsed
    if parsed is None:
        raise RuntimeError(
            "Google response did not include structured prediction output."
        )

    usage = getattr(response, "usage_metadata", None)
    return {
        "known_ai_technical_failure": parsed.known_ai_technical_failure,
        "potential_ai_technical_failure": parsed.potential_ai_technical_failure,
        "model_name": model,
        "raw_response": response.text,
        "input_tokens": getattr(usage, "prompt_token_count", None),
        "output_tokens": getattr(usage, "candidates_token_count", None),
    }
