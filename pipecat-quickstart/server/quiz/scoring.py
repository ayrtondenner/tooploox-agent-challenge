"""Per-answer scoring and geometric-weighted final score.

**Scoring rules (from task_description.txt):**

- **Single-select question:**  4 points if the user's selection matches the correct
  option, 0 otherwise.
- **Multi-select question:**  the raw score equals the *number of correctly selected
  options*, between 0 and 4. Task wording is literally "number of correctly selected
  answers", so we do not deduct for false positives — a false pick simply does not
  contribute. This interpretation is documented in `.planning/REQUIREMENTS.md`.

**Weights:**  geometric sequence starting at 1.0, each subsequent weight multiplied
by 1.1 — so w_i = 1.1^(i-1) for 1-based position i.

**Final score:**  sum(raw_i * w_i) / sum(w_i) — a weighted average, guaranteed to
stay in [0, 4] when individual scores do.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from .config import CORRECT_POINTS, WEIGHT_GROWTH
from .schemas import Question, QuizResult, ScoredAnswer


def score_answer(question: Question, selected_indices: Iterable[int]) -> float:
    selected = set(selected_indices)
    correct = set(question.correct_indices)
    if len(correct) == 1:
        # Single-select: all-or-nothing — the user must select *exactly* the correct one.
        return float(CORRECT_POINTS) if selected == correct else 0.0
    # Multi-select: literal count of correct picks; false positives don't deduct.
    return float(len(selected & correct))


def compute_weight(position: int) -> float:
    if position < 1:
        raise ValueError(f"position must be >= 1, got {position}")
    return WEIGHT_GROWTH ** (position - 1)


def weighted_average(scores: Sequence[float], weights: Sequence[float]) -> float:
    if len(scores) != len(weights):
        raise ValueError(
            f"scores and weights length mismatch: {len(scores)} vs {len(weights)}"
        )
    if not scores:
        raise ValueError("cannot average an empty sequence")
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("sum of weights must be > 0")
    return sum(s * w for s, w in zip(scores, weights)) / total_weight


def score_quiz(
    questions: Sequence[Question],
    answers: Sequence[Iterable[int]],
) -> QuizResult:
    if len(questions) != len(answers):
        raise ValueError(
            f"questions and answers length mismatch: {len(questions)} vs {len(answers)}"
        )
    scored: list[ScoredAnswer] = []
    for i, (question, selected) in enumerate(zip(questions, answers), start=1):
        selected_tuple = tuple(sorted(set(selected)))
        raw = score_answer(question, selected_tuple)
        weight = compute_weight(i)
        scored.append(
            ScoredAnswer(
                position=i,
                selected_indices=selected_tuple,
                raw_score=raw,
                weight=weight,
                weighted_score=raw * weight,
            )
        )
    final = weighted_average(
        [sa.raw_score for sa in scored],
        [sa.weight for sa in scored],
    )
    return QuizResult(scored=tuple(scored), final_score=final)
