"""Application configuration settings."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _optional_int(name: str) -> int | None:
    """Parse an optional integer environment variable.

    Args:
        name: The environment variable name.

    Returns:
        The parsed integer or None if not set or empty.
    """
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return int(value)


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: str = os.getenv("POSTGRES_PORT", "5432")
    postgres_db: str = os.getenv("POSTGRES_DB", "gmf_annotation")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    openai_prompt_version: str = os.getenv("OPENAI_PROMPT_VERSION", "v2")
    openai_temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))
    openai_max_completion_tokens: int | None = _optional_int(
        "OPENAI_MAX_COMPLETION_TOKENS"
    )
    openai_timeout_seconds: int = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    google_model: str = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")
    google_prompt_version: str = os.getenv("GOOGLE_PROMPT_VERSION", "v2")
    google_temperature: float = float(os.getenv("GOOGLE_TEMPERATURE", "0.0"))
    google_max_output_tokens: int | None = _optional_int("GOOGLE_MAX_OUTPUT_TOKENS")
    google_timeout_seconds: int = int(os.getenv("GOOGLE_TIMEOUT_SECONDS", "30"))
    hf_token: str = os.getenv("HF_TOKEN", "")
    hf_model: str = os.getenv("HF_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
    hf_provider: str = os.getenv("HF_PROVIDER", "auto")
    hf_prompt_version: str = os.getenv("HF_PROMPT_VERSION", "v2")
    hf_temperature: float = float(os.getenv("HF_TEMPERATURE", "0.0"))
    hf_max_tokens: int | None = _optional_int("HF_MAX_TOKENS")
    hf_timeout_seconds: int = int(os.getenv("HF_TIMEOUT_SECONDS", "60"))

    @property
    def database_url(self) -> str:
        """Construct the database URL from PostgreSQL settings.

        Returns:
            The database connection URL.
        """
        return (
            "postgresql+psycopg2://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
