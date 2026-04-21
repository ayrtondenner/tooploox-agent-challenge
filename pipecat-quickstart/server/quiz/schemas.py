"""Pydantic schemas — LLM output contract and internal data types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from pydantic import BaseModel, Field, field_validator

from .config import OPTIONS_PER_QUESTION


class Question(BaseModel):
    prompt: str = Field(description="The full question text, self-contained.")
    options: List[str] = Field(
        description=f"Exactly {OPTIONS_PER_QUESTION} distinct answer options."
    )
    correct_indices: List[int] = Field(
        description=(
            "0-based indices of the correct option(s). "
            "One index for single-select; two or more for multi-select."
        )
    )
    is_multi_select: bool = Field(
        description="True if the question has more than one correct answer."
    )

    @field_validator("options")
    @classmethod
    def _options_count(cls, v: List[str]) -> List[str]:
        if len(v) != OPTIONS_PER_QUESTION:
            raise ValueError(f"expected {OPTIONS_PER_QUESTION} options, got {len(v)}")
        return v

    @field_validator("correct_indices")
    @classmethod
    def _indices_in_range(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("must have at least one correct index")
        if any(i < 0 or i >= OPTIONS_PER_QUESTION for i in v):
            raise ValueError(f"indices must be in [0, {OPTIONS_PER_QUESTION})")
        if len(set(v)) != len(v):
            raise ValueError("correct_indices must not repeat")
        return sorted(v)


class QuizSpec(BaseModel):
    """Wrapper the LLM returns via structured output — a list of questions."""

    questions: List[Question] = Field(
        description="Between 5 and 8 quiz questions derived from the source text."
    )


@dataclass(frozen=True)
class ScoredAnswer:
    """A user's answer after scoring."""

    position: int  # 1-based, drives weighting
    selected_indices: tuple[int, ...]
    raw_score: float  # 0..4
    weight: float  # 1.1^(position-1)
    weighted_score: float  # raw_score * weight


@dataclass(frozen=True)
class QuizResult:
    scored: tuple[ScoredAnswer, ...]
    final_score: float  # weighted average, in [0, 4]
