"""Tests for quiz/generator.py — LangChain + OpenAI question generation.

The LLM call itself is not unit-tested (tested live via the manual E2E smoke
test). We verify the input-validation boundary and the chain wiring.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from quiz.schemas import Question, QuizSpec


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1")


class TestGenerateQuizValidation:
    def test_rejects_too_few_questions(self, mock_env):
        from quiz.generator import generate_quiz

        with pytest.raises(ValueError, match="num_questions"):
            generate_quiz(markdown="x", num_questions=4)

    def test_rejects_too_many_questions(self, mock_env):
        from quiz.generator import generate_quiz

        with pytest.raises(ValueError, match="num_questions"):
            generate_quiz(markdown="x", num_questions=9)


class TestGenerateQuizDispatch:
    def test_invokes_chain_with_expected_inputs_and_returns_result(self, mock_env):
        from quiz import generator

        fake_question = Question(
            prompt="What is Pipecat?",
            options=["A voice framework", "A cat", "A music tool", "A database"],
            correct_indices=[0],
            is_multi_select=False,
        )
        fake_spec = QuizSpec(questions=[fake_question] * 5)

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = fake_spec

        with patch.object(generator, "_build_chain", return_value=mock_chain):
            result = generator.generate_quiz(
                markdown="# Pipecat\nreal-time voice agents",
                num_questions=5,
                topic="voice agents",
            )

        assert result is fake_spec
        mock_chain.invoke.assert_called_once()
        call_kwargs = mock_chain.invoke.call_args.args[0]
        assert call_kwargs["n"] == 5
        assert "Pipecat" in call_kwargs["markdown"]
        assert "voice agents" in call_kwargs["topic_clause"]

    def test_empty_topic_produces_empty_topic_clause(self, mock_env):
        from quiz import generator

        fake_spec = QuizSpec(
            questions=[
                Question(
                    prompt="x",
                    options=["a", "b", "c", "d"],
                    correct_indices=[0],
                    is_multi_select=False,
                )
            ]
            * 5
        )
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = fake_spec

        with patch.object(generator, "_build_chain", return_value=mock_chain):
            generator.generate_quiz(markdown="x", num_questions=5)

        call_kwargs = mock_chain.invoke.call_args.args[0]
        assert call_kwargs["topic_clause"] == ""

    def test_raises_if_llm_returns_wrong_count(self, mock_env):
        from quiz import generator

        # Return 3 questions when 5 were requested.
        fake_spec = QuizSpec(
            questions=[
                Question(
                    prompt="x",
                    options=["a", "b", "c", "d"],
                    correct_indices=[0],
                    is_multi_select=False,
                )
            ]
            * 3
        )
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = fake_spec

        with patch.object(generator, "_build_chain", return_value=mock_chain):
            with pytest.raises(RuntimeError, match="expected 5"):
                generator.generate_quiz(markdown="x", num_questions=5)
