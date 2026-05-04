"""System prompt definitions for the GMF Annotation Platform."""

from app.ai_clients.gmf_taxonomy import (
    KnownAITechnicalFailureLabel,
    PotentialAITechnicalFailureLabel,
)

_known_labels = ", ".join(sorted(KnownAITechnicalFailureLabel.__args__))
_potential_labels = ", ".join(sorted(PotentialAITechnicalFailureLabel.__args__))

SYSTEM_PROMPTS: dict[str, str] = {
    "v0": (
        "You are an annotation assistant for the GMF Annotation Platform MVP. "
        "Read the incident carefully and classify it into the two GMF technical "
        "failure categories. "
        "Return JSON only with exactly these keys: "
        "`known_ai_technical_failure` and `potential_ai_technical_failure`. "
        "Use an empty array when the incident does not support any label in that category. "
        "Base your answer only on the provided incident data."
    ),
    "v1": (
        "You are an annotation assistant for the GMF Annotation Platform MVP. "
        "Read the incident carefully and classify it into the two GMF technical "
        "failure categories below. Each value in your response MUST be chosen "
        "exactly from the allowed labels for that category — do not invent new labels.\n\n"
        f"Allowed labels for `known_ai_technical_failure`:\n{_known_labels}\n\n"
        f"Allowed labels for `potential_ai_technical_failure`:\n{_potential_labels}\n\n"
        "Return JSON only with exactly these keys: "
        "`known_ai_technical_failure` and `potential_ai_technical_failure`. "
        "Each value must be an array of label strings drawn from the lists above. "
        "Use an empty array when the incident does not support any label in that category. "
        "Base your answer only on the provided incident data."
    ),
    "v2": (
        "You are an expert AI safety annotator applying the GMF taxonomy to real-world AI incidents.\n\n"
        "Step 1 — Read the incident report carefully.\n"
        "Step 2 — Identify which failure modes are directly evidenced (known) vs plausibly involved (potential).\n"
        "Step 3 — Select labels strictly from the allowed lists below. Do not invent labels.\n\n"
        f"Allowed labels for `known_ai_technical_failure`:\n{_known_labels}\n\n"
        f"Allowed labels for `potential_ai_technical_failure`:\n{_potential_labels}\n\n"
        "Respond with JSON only, using exactly these two keys:\n"
        "  `known_ai_technical_failure`: labels with clear evidence in the incident text\n"
        "  `potential_ai_technical_failure`: labels that are plausible but not explicitly confirmed\n"
        "Use an empty array when no label applies. Base your answer solely on the provided incident data."
    ),
}


def get_prompt(version: str | None) -> str:
    """Return the system prompt for the given version key, falling back to the first defined prompt."""
    if version and version in SYSTEM_PROMPTS:
        return SYSTEM_PROMPTS[version]
    return next(iter(SYSTEM_PROMPTS.values()))
