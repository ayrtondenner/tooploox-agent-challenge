"""LangChain + OpenAI structured-output quiz generator."""

from __future__ import annotations

from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from .config import (
    MAX_QUESTIONS,
    MIN_QUESTIONS,
    OPTIONS_PER_QUESTION,
    load_settings,
)
from .schemas import QuizSpec

_SYSTEM_TEMPLATE = (
    "You are an expert quiz designer. Given a source document, write {n} multiple-choice "
    "questions that test comprehension of its key concepts.\n\n"
    "Rules:\n"
    "- Each question has exactly {opts} distinct answer options as plain strings — "
    "do NOT prefix options with 'A)', 'B)', numbers, or bullets.\n"
    "- Include at least one multi-select question (2+ correct answers). Mix single and multi-select.\n"
    "- For single-select: correct_indices has exactly one index; is_multi_select = false.\n"
    "- For multi-select: correct_indices has 2 or more indices; is_multi_select = true.\n"
    "- All correct_indices are 0-based and in [0, {opts}).\n"
    "- Questions must be answerable from the source text alone — no outside knowledge.\n"
    "- Avoid trick questions, double negatives, and 'all/none of the above' style options.\n"
    "- Keep option lengths roughly similar so length doesn't leak the answer.\n"
    "{topic_clause}"
)

_USER_TEMPLATE = (
    "Source document:\n---\n{markdown}\n---\n\nGenerate exactly {n} quiz questions now."
)


def _build_chain(model: str, api_key: str) -> Runnable:
    llm = ChatOpenAI(api_key=api_key, model=model).with_structured_output(QuizSpec)
    llm_with_retry = llm.with_retry(stop_after_attempt=2)
    prompt = ChatPromptTemplate.from_messages(
        [("system", _SYSTEM_TEMPLATE), ("human", _USER_TEMPLATE)]
    )
    return prompt | llm_with_retry


def generate_quiz(
    markdown: str,
    num_questions: int,
    topic: Optional[str] = None,
    model: Optional[str] = None,
) -> QuizSpec:
    if not (MIN_QUESTIONS <= num_questions <= MAX_QUESTIONS):
        raise ValueError(
            f"num_questions must be in [{MIN_QUESTIONS}, {MAX_QUESTIONS}], got {num_questions}"
        )
    settings = load_settings()
    chain = _build_chain(
        model=model or settings.openai_model,
        api_key=settings.openai_api_key,
    )
    topic_clause = f"- Focus especially on: {topic}.\n" if topic else ""
    result: QuizSpec = chain.invoke(
        {
            "markdown": markdown,
            "n": num_questions,
            "opts": OPTIONS_PER_QUESTION,
            "topic_clause": topic_clause,
        }
    )
    if len(result.questions) != num_questions:
        raise RuntimeError(
            f"LLM returned {len(result.questions)} questions, expected {num_questions}"
        )
    return result
