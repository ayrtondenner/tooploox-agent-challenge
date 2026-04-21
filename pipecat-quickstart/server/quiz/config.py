"""Quiz app configuration — env loading and constants."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)


DEFAULT_SOURCE_URL = "https://github.com/pipecat-ai/pipecat/blob/main/README.md"
DEFAULT_MODEL = "gpt-4.1"
MIN_QUESTIONS = 5
MAX_QUESTIONS = 8
OPTIONS_PER_QUESTION = 4
CORRECT_POINTS = 4
WEIGHT_GROWTH = 1.1


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    db_path: Path
    default_source_url: str


def _env(name: str) -> str | None:
    """Read an env var, treating whitespace-only or inline-comment values as unset.

    The pipecat-quickstart `.env` template uses `KEY= # comment` lines, which
    python-dotenv loads as "# comment". This normalizes those to None so the
    defaults below kick in.
    """
    raw = os.getenv(name)
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        return None
    return stripped


def load_settings() -> Settings:
    api_key = _env("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to pipecat-quickstart/server/.env"
        )
    return Settings(
        openai_api_key=api_key,
        openai_model=_env("OPENAI_MODEL") or DEFAULT_MODEL,
        db_path=Path(_env("QUIZ_DB_PATH") or "quiz.db"),
        default_source_url=_env("QUIZ_DEFAULT_URL") or DEFAULT_SOURCE_URL,
    )
