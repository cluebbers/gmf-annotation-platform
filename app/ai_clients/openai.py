"""OpenAI integration for predictions and chat."""


from openai import OpenAI

from app.ai_clients.gmf_taxonomy import (SYSTEM_PROMPT, StructuredPrediction,
                                         build_incident_prompt)
from app.config import settings


def _get_openai_client() -> OpenAI:
    """Get OpenAI client singleton.

    Returns:
        OpenAI client instance.
    """
    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
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
        history: Chat history.
        message: User message.

    Returns:
        Chat completion response.

    Raises:
        RuntimeError: If OpenAI request fails.
    """
    client = _get_openai_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_incident_prompt(title, report_text)},
        *history,
        {"role": "user", "content": message},
    ]
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=settings.openai_temperature,
        )
    except Exception as exc:
        raise RuntimeError("OpenAI request failed.") from exc
    return response.choices[0].message.content


def predict_incident(
    title: str | None,
    report_text: str,
    model_name: str | None = None,
    temperature: float | None = None,
) -> dict[str, object]:
    """Predict GMF labels for an incident using OpenAI.

    Args:
        title: Incident title.
        report_text: Incident report text.
        model_name: Optional model name override.
        temperature: Optional temperature override.

    Returns:
        Prediction result with labels, model name, and token counts.

    Raises:
        RuntimeError: If OpenAI request fails.
    """
    client = _get_openai_client()
    user_prompt = build_incident_prompt(title, report_text)
    model = model_name or settings.openai_model
    temp = temperature if temperature is not None else settings.openai_temperature

    request_kwargs = {
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_prompt,
                    }
                ],
            }
        ],
        "text_format": StructuredPrediction,
        "temperature": temp,
    }
    if settings.openai_max_completion_tokens is not None:
        request_kwargs["max_output_tokens"] = settings.openai_max_completion_tokens

    try:
        response = client.responses.parse(**request_kwargs)
    except Exception as exc:
        if temp is not None and "Unsupported parameter: 'temperature'" in str(exc):
            request_kwargs.pop("temperature", None)
            try:
                response = client.responses.parse(**request_kwargs)
            except Exception as retry_exc:
                raise RuntimeError("OpenAI request failed.") from retry_exc
        else:
            raise RuntimeError("OpenAI request failed.") from exc

    raw_response = response.model_dump_json()
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("OpenAI response did not include structured prediction output.")

    usage = getattr(response, "usage", None)
    return {
        "known_ai_technical_failure": parsed.known_ai_technical_failure,
        "potential_ai_technical_failure": parsed.potential_ai_technical_failure,
        "model_name": model,
        "raw_response": raw_response,
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }
