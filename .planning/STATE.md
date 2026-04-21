# STATE

## Current

- **Milestone:** v1 Challenge Submission — **COMPLETE**
- **Active phase:** _(none — all phases complete; ready for commit + submission)_
- **Started:** 2026-04-21
- **Completed:** 2026-04-21
- **Plan:** `/home/ayrton/.claude/plans/we-are-starting-tender-shore.md` (approved 2026-04-21)

## Completed

- **Phase 1:** Project scaffolding + deps — `pyproject.toml` updated (`langchain-openai`, `pytest`), `quiz/__init__.py`, `quiz/config.py` with `_env()` helper for inline-comment-tolerant env loading, `.gitignore` updates, `.env.example` appended with quiz vars.
- **Phase 2:** Markdown fetcher — `quiz/sources.py` with GitHub `/blob/` → raw URL normalization, SHA-256 content hash, error handling for 404/network. TDD, 9 tests.
- **Phase 3a:** Pydantic schemas — `quiz/schemas.py` with `Question`, `QuizSpec`, `ScoredAnswer`, `QuizResult`. Validators enforce 4 options, index range, dedupe. TDD, 9 tests.
- **Phase 4:** Scoring logic — `quiz/scoring.py` with `score_answer`, `compute_weight`, `weighted_average`, `score_quiz`. Literal interpretation of multi-select rule (count correct picks, cap at 4). TDD, 25 tests.
- **Phase 5:** SQLite storage — `quiz/storage.py` with `init_db`, `start_run`, `record_answer`, `finalize_run`, `load_run`. FK constraints enforced. TDD, 11 tests.
- **Phase 3b:** LangChain generator — `quiz/generator.py` with `ChatOpenAI.with_structured_output(QuizSpec)` + `.with_retry(2)`. Validation boundary unit-tested (5 tests); live smoke-tested against OpenAI API (5 valid questions on pipecat summary).
- **Phase 6:** Gradio UI — `quiz/app.py` with 3-view Blocks app (setup → quiz → results). Verified in-process end-to-end: generate → answer each question → finalize → persisted to `quiz.db`.
- **Phase 7:** READMEs — root `README.md` (full submission write-up, scoring interpretation, future extensions) + `pipecat-quickstart/README.md` (points at the quiz app alongside the voice bot). Test count: 59.

## Verification summary

- `uv run pytest` → **59/59 pass** in ~3.7s.
- `uv run python -m quiz.app` → server launches, responds at `http://127.0.0.1:7860/`, homepage renders.
- In-process E2E walk (mocked user picks first correct answer per question) → run persisted, `final_score=3.58/4.0` (reflects multi-select cap), `scored_answers=5`, `completed_at` populated.

## Blocked

_(none)_

## Notes

- User pre-installed `gradio`, `langchain`, `pipecat-ai` and added `OPENAI_API_KEY`, `CARTESIA_API_KEY`, `DEEPGRAM_API_KEY` to `pipecat-quickstart/server/.env`.
- `pipecat-quickstart/server/bot.py` is untouched — a parallel voice-agent entry point.
- Multi-select scoring uses literal task-wording interpretation (count of correct picks, no false-positive deduction). Documented in `scoring.py`, `REQUIREMENTS.md`, and the root README.
