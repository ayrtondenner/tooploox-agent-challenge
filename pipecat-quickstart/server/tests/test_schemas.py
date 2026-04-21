"""Tests for quiz/schemas.py — Pydantic models + validators."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from quiz.schemas import Question, QuizSpec


def _valid_question(**overrides) -> dict:
    base = {
        "prompt": "What is 2 + 2?",
        "options": ["3", "4", "5", "6"],
        "correct_indices": [1],
        "is_multi_select": False,
    }
    base.update(overrides)
    return base


class TestQuestion:
    def test_accepts_valid_single_select(self):
        q = Question(**_valid_question())
        assert q.correct_indices == [1]
        assert q.is_multi_select is False

    def test_accepts_valid_multi_select(self):
        q = Question(**_valid_question(correct_indices=[0, 2], is_multi_select=True))
        assert q.correct_indices == [0, 2]

    def test_rejects_wrong_option_count(self):
        with pytest.raises(ValidationError, match="expected 4 options"):
            Question(**_valid_question(options=["a", "b", "c"]))

    def test_rejects_empty_correct_indices(self):
        with pytest.raises(ValidationError, match="at least one correct"):
            Question(**_valid_question(correct_indices=[]))

    def test_rejects_out_of_range_index(self):
        with pytest.raises(ValidationError, match=r"indices must be in"):
            Question(**_valid_question(correct_indices=[4]))

    def test_rejects_negative_index(self):
        with pytest.raises(ValidationError, match=r"indices must be in"):
            Question(**_valid_question(correct_indices=[-1]))

    def test_rejects_duplicate_indices(self):
        with pytest.raises(ValidationError, match="must not repeat"):
            Question(**_valid_question(correct_indices=[1, 1]))

    def test_sorts_correct_indices(self):
        q = Question(**_valid_question(correct_indices=[3, 0, 2], is_multi_select=True))
        assert q.correct_indices == [0, 2, 3]


class TestQuizSpec:
    def test_accepts_list_of_questions(self):
        spec = QuizSpec(questions=[Question(**_valid_question())])
        assert len(spec.questions) == 1
