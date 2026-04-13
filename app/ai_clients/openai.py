from functools import lru_cache

from openai import OpenAI
from pydantic import BaseModel, Field

from app.config import settings


SYSTEM_PROMPT = (
    "You are an annotation assistant for the GMF Annotation Platform MVP. "
    "Read the incident carefully and classify it into the two GMF technical "
    "failure categories. Return JSON only with exactly these keys: "
    "`known_ai_technical_failure` and `potential_ai_technical_failure`. "
    "Each value must be an array of label strings. Use an empty array when "
    "the incident does not support any label in that category. Base your "
    "answer only on the provided incident data."
)


class StructuredPrediction(BaseModel):
    known_ai_technical_failure: list[str] = Field(default_factory=list)
    potential_ai_technical_failure: list[str] = Field(default_factory=list)


@lru_cache(maxsize=1)
def _get_openai_client() -> OpenAI:
    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
    )


def predict_incident(title: str | None, report_text: str) -> dict[str, object]:
    client = _get_openai_client()
    user_prompt = (
        "Incident data:\n"
        f"Title: {title or 'N/A'}\n"
        "Report Text:\n"
        f"{report_text}"
    )

    request_kwargs = {
        "model": settings.openai_model,
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
        "temperature": settings.openai_temperature,
    }
    if settings.openai_max_completion_tokens is not None:
        request_kwargs["max_output_tokens"] = settings.openai_max_completion_tokens

    try:
        response = client.responses.parse(**request_kwargs)
    except Exception as exc:
        raise RuntimeError("OpenAI request failed.") from exc

    raw_response = response.model_dump_json()
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("OpenAI response did not include structured prediction output.")

    usage = getattr(response, "usage", None)
    return {
        "known_ai_technical_failure": parsed.known_ai_technical_failure,
        "potential_ai_technical_failure": parsed.potential_ai_technical_failure,
        "model_name": settings.openai_model,
        "raw_response": raw_response,
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }
