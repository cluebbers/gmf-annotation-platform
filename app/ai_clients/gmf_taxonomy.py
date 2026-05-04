"""GMF taxonomy definitions and system prompt."""

from typing import Literal
from pydantic import BaseModel, Field



def build_incident_prompt(title: str | None, report_text: str) -> str:
    """Build incident prompt for OpenAI.

    Args:
        title: Incident title.
        report_text: Incident report text.

    Returns:
        Formatted prompt.
    """
    return (
        "Incident data:\n"
        f"Title: {title or 'N/A'}\n"
        "Report Text:\n"
        f"{report_text}"
    )


KnownAITechnicalFailureLabel = Literal[
    "Adversarial Data",
    "Algorithmic Bias",
    "Black Swan Event",
    "Concept Drift",
    "Context Misidentification",
    "Covariate Shift",
    "Data or Labelling Noise",
    "Dataset Imbalance",
    "Distributional Artifacts",
    "Distributional Bias",
    "Domain Adaptation Deficit",
    "Faulty Interface or Instructions",
    "Faulty or Inadequate Preprocessing",
    "Gaming Vulnerability",
    "Generalization Failure",
    "Hardcoding",
    "Hardware Failure",
    "Harmful Application",
    "Human Error",
    "Inadequate Anonymization",
    "Inadequate Data Augmentation",
    "Inadequate Data Sampling",
    "Inadequate Output Filtering",
    "Inadequate Provenance",
    "Inadequate Verification",
    "Inappropriate Training Content",
    "Incomplete Data Attribute Capture",
    "Input Sensitivity",
    "Lack of Adversarial Robustness",
    "Lack of Authenticity Assurance",
    "Lack of Capability Control",
    "Lack of Corrigibility",
    "Lack of Explainability",
    "Lack of Interruptability",
    "Lack of Safety Protocols",
    "Lack of Transparency",
    "Latency Issues",
    "Limited Dataset",
    "Limited Receptive Field",
    "Malicious Marketing",
    "Misaligned Objective",
    "Misconfigured Threshold",
    "Miscoordination",
    "Misinformation Generation Hazard",
    "Misuse",
    "Multiagent Goal Divergence",
    "Outdated Ground Truth",
    "Overfitting",
    "Overpersonalization",
    "Pose Estimation",
    "Privacy Concerns",
    "Problematic Features",
    "Problematic Input",
    "Prompt Injection",
    "Robustness Failure",
    "Scaling Limitations",
    "Security Vulnerability",
    "Software Bug",
    "System Manipulation",
    "Task Mismatch",
    "Tuning Issues",
    "Unauthorized Data",
    "Underfitting",
    "Underspecification",
    "Unsafe Exposure or Access",
    "Untested Deployment",
]
"""Known AI technical failure labels."""


PotentialAITechnicalFailureLabel = Literal[
    "Adversarial Data",
    "Algorithmic Bias",
    "Backup Failure",
    "Black Box",
    "Concept Drift",
    "Context Misidentification",
    "Covariate Shift",
    "Data Memorization",
    "Data or Labelling Noise",
    "Dataset Imbalance",
    "Deployment Misconfiguration",
    "Distributional Bias",
    "Domain Adaptation Deficit",
    "Faulty or Inadequate Preprocessing",
    "Gaming Vulnerability",
    "Generalization Failure",
    "Hardcoding",
    "Hardware Failure",
    "Harmful Application",
    "Human Error",
    "Inadequate Anonymization",
    "Inadequate Data Augmentation",
    "Inadequate Data Sampling",
    "Inadequate Regularization",
    "Inadequate Sequential Memory",
    "Inadequate Verification",
    "Inappropriate Training Content",
    "Incomplete Data Attribute Capture",
    "Lack of Adversarial Robustness",
    "Lack of Capability Control",
    "Lack of Explainability",
    "Lack of Interruptability",
    "Lack of Safety Protocols",
    "Lack of Transparency",
    "Latency Issues",
    "Limited Dataset",
    "Limited Receptive Field",
    "Limited User Access",
    "Malicious Marketing",
    "Misaligned Objective",
    "Misconfigured Aggregation",
    "Misconfigured Prompt",
    "Misconfigured Threshold",
    "Miscoordination",
    "Misinformation Generation Hazard",
    "Misuse",
    "Outdated Input",
    "Overfitting",
    "Privacy Concerns",
    "Problematic Features",
    "Problematic Input",
    "Robustness Failure",
    "Security Vulnerability",
    "Software Bug",
    "System Manipulation",
    "Task Mismatch",
    "Tuning Issues",
    "Unauthorized Data",
    "Underfitting",
    "Underspecification",
    "Unsafe Exposure or Access",
    "Untested Deployment",
]
"""Potential AI technical failure labels."""

class StructuredPrediction(BaseModel):
    """Schema for structured prediction output from OpenAI."""

    known_ai_technical_failure: list[KnownAITechnicalFailureLabel] = Field(
        default_factory=list
    )
    potential_ai_technical_failure: list[PotentialAITechnicalFailureLabel] = Field(
        default_factory=list
    )