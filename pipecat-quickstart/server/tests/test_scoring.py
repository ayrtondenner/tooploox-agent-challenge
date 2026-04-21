"""Tests for quiz/scoring.py — per-answer scoring, geometric weights, weighted average."""

from __future__ import annotations

import math

import pytest

from quiz.schemas import Question
from quiz.scoring import compute_weight, score_answer, score_quiz, weighted_average


def _q(correct: list[int], multi: bool | None = None) -> Question:
    return Question(
        prompt="x",
        options=["a", "b", "c", "d"],
        correct_indices=correct,
        is_multi_select=multi if multi is not None else len(correct) > 1,
    )


class TestScoreAnswer:
    def test_single_select_correct_scores_4(self):
        assert score_answer(_q([2]), [2]) == 4.0

    def test_single_select_wrong_scores_0(self):
        assert score_answer(_q([2]), [0]) == 0.0

    def test_single_select_no_selection_scores_0(self):
        assert score_answer(_q([2]), []) == 0.0

    def test_multi_select_all_correct_scores_count(self):
        # 2 correct, user picks both, no wrongs → 2
        assert score_answer(_q([0, 2]), [0, 2]) == 2.0

    def test_multi_select_partial_correct_ignores_false_positives(self):
        # Task wording: "number of correctly selected answers"
        # Interpretation: count correct picks; false positives do not deduct.
        # 3 correct [0,1,2]; user picks [0,2,3] → 2 correct picks, 1 wrong → score 2.
        assert score_answer(_q([0, 1, 2]), [0, 2, 3]) == 2.0

    def test_multi_select_all_options_selected_caps_at_correct_count(self):
        # 2 correct; user picks all 4 options → 2 correct picks → score 2.
        assert score_answer(_q([0, 2]), [0, 1, 2, 3]) == 2.0

    def test_multi_select_only_wrong_scores_0(self):
        assert score_answer(_q([0, 2]), [1, 3]) == 0.0

    def test_multi_select_no_selection_scores_0(self):
        assert score_answer(_q([0, 2]), []) == 0.0

    def test_selection_duplicates_counted_once(self):
        # Defensive: duplicate selection shouldn't inflate the score.
        assert score_answer(_q([0, 2]), [0, 0, 2]) == 2.0


class TestComputeWeight:
    def test_position_1_is_1(self):
        assert compute_weight(1) == 1.0

    def test_position_2_is_1_1(self):
        assert compute_weight(2) == pytest.approx(1.1)

    def test_position_5_is_geometric(self):
        assert compute_weight(5) == pytest.approx(1.1**4)

    def test_position_must_be_positive(self):
        with pytest.raises(ValueError):
            compute_weight(0)


class TestWeightedAverage:
    def test_all_fours_returns_4(self):
        assert weighted_average([4, 4, 4], [1.0, 1.1, 1.21]) == pytest.approx(4.0)

    def test_all_zeros_returns_0(self):
        assert weighted_average([0, 0, 0], [1.0, 1.1, 1.21]) == 0.0

    def test_hand_computed_case(self):
        scores = [4.0, 0.0]
        weights = [1.0, 1.1]
        expected = (4.0 * 1.0 + 0.0 * 1.1) / (1.0 + 1.1)
        assert weighted_average(scores, weights) == pytest.approx(expected)

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            weighted_average([1.0, 2.0], [1.0])

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            weighted_average([], [])


class TestScoreQuiz:
    def test_all_correct_single_select_scores_4(self):
        questions = [_q([i % 4]) for i in range(5)]
        answers = [[q.correct_indices[0]] for q in questions]
        result = score_quiz(questions, answers)
        assert result.final_score == pytest.approx(4.0)
        assert len(result.scored) == 5

    def test_all_wrong_scores_0(self):
        questions = [_q([0]) for _ in range(5)]
        answers = [[1] for _ in range(5)]
        result = score_quiz(questions, answers)
        assert result.final_score == 0.0

    def test_weights_follow_geometric_sequence(self):
        questions = [_q([0]) for _ in range(5)]
        answers = [[0] for _ in range(5)]
        result = score_quiz(questions, answers)
        weights = [sa.weight for sa in result.scored]
        assert weights == pytest.approx([1.0, 1.1, 1.21, 1.331, 1.4641])

    def test_position_is_1_based(self):
        questions = [_q([0]) for _ in range(5)]
        answers = [[0] for _ in range(5)]
        result = score_quiz(questions, answers)
        positions = [sa.position for sa in result.scored]
        assert positions == [1, 2, 3, 4, 5]

    def test_weighted_score_is_raw_times_weight(self):
        questions = [_q([0]), _q([0])]
        answers = [[0], [1]]  # 4, 0
        result = score_quiz(questions, answers)
        assert result.scored[0].raw_score == 4.0
        assert result.scored[0].weighted_score == pytest.approx(4.0 * 1.0)
        assert result.scored[1].raw_score == 0.0
        assert result.scored[1].weighted_score == pytest.approx(0.0 * 1.1)
        expected_final = (4.0 + 0.0) / (1.0 + 1.1)
        assert result.final_score == pytest.approx(expected_final)

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            score_quiz([_q([0])], [[0], [1]])

    def test_final_score_stays_in_valid_range(self):
        # Property-ish: any mix of raw scores in [0,4] produces final in [0,4].
        questions = [_q([0]) for _ in range(5)]
        answers = [[0], [1], [0], [1], [0]]  # 4, 0, 4, 0, 4
        result = score_quiz(questions, answers)
        assert 0.0 <= result.final_score <= 4.0
        assert math.isfinite(result.final_score)
