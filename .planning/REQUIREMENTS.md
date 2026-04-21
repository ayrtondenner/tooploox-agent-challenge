# REQUIREMENTS

Derived from [task_description.txt](../task_description.txt). Each requirement is falsifiable — mapped to a verification path.

## Functional

| ID | Requirement | Verification |
|---|---|---|
| R1 | Fetch knowledge from a Markdown file at a configurable URL (default example `https://github.com/pipecat-ai/pipecat/blob/main/README.md`) | `test_sources.py` — GitHub `/blob/` normalization + HTTP fetch (mocked); manual smoke test paste |
| R2 | Auto-generate a quiz with **between 5 and 8 questions**, user-configurable | Gradio slider clamped to [5, 8]; generator call passes `N` to LangChain chain |
| R3 | Each question has exactly **4 possible answers** (closed list) | Pydantic validator on `Question.options` enforces `len == 4`; tested in `test_scoring.py` helpers |
| R4 | Support multi-answer questions (multi-select) | `Question.is_multi_select` flag; generator prompt requests a mix; UI renders `gr.CheckboxGroup` when flag set |
| R5 | Score per answer: 4 for correct single-select, 0 for wrong, N correct selections for multi-select | `score_answer` unit tests cover all three cases |
| R6 | Final score = weighted average with geometric weights `w_i = 1.0 * 1.1^(i-1)` | `final_score` unit test: all-4 → 4.0, all-0 → 0.0, mixed matches hand-computed value; weight sequence test |
| R7 | Persist all answers AND the final score in a database | SQLite `answers` and `quiz_runs` tables; `test_storage.py` round-trip + FK integrity |
| R8 | User interaction via CLI **or** any UI (Gradio chosen) | Gradio `app.py` entry point; manual smoke test |

## Non-functional

| ID | Requirement | Verification |
|---|---|---|
| NF1 | Python implementation | Only Python files created under `quiz/` |
| NF2 | Use any free-tier LLM (OpenAI chosen, key already in `.env`) | `quiz/generator.py` reads `OPENAI_API_KEY` |
| NF3 | Structured LLM output (no string parsing) | LangChain `llm.with_structured_output(QuizSpec)` |
| NF4 | Validated LLM output with one retry on failure | `.with_retry(stop_after_attempt=2)` + Pydantic validators |
| NF5 | Reproducible source snapshot per run | `quiz_runs.source_md_sha256` column |

## Interpretation notes

- **R5 multi-select scoring (ambiguous in task):** Task says "between 0 and 4 — number of correctly selected answers in case of multiple answers question." We interpret literally: count of correct picks, capped at 4, no deduction for false positives. Documented in `scoring.py` docstring and README.
- **R6 weight sequence:** "starting from 1.0, with each subsequent weight increased by 10%" → multiplicative (geometric), not additive. So w1=1.0, w2=1.1, w3=1.21, w4=1.331, w5=1.4641. If additive were meant, it would be 1.0, 1.1, 1.2, 1.3, 1.4. We go with geometric because the task explicitly says *"geometric sequence."*
