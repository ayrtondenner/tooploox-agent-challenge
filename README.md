# Markdown Quiz Agent — Tooploox Code Challenge

A Python agent that auto-generates a short multiple-choice quiz from any Markdown document on the web, runs it in a Gradio UI, scores answers with a geometric-weighted average, and persists everything to SQLite.

Submission for the **Senior AI NodeJS Engineer** role ([job_description.md](job_description.md)) — implementation in Python per the task spec ([task_description.txt](task_description.txt)).

## Quick start

```bash
cd pipecat-quickstart/server

# One-time setup
uv sync
cp .env.example .env          # (if not already present)
# Edit .env: set OPENAI_API_KEY at minimum.

# Run tests
uv run pytest

# Launch the app
uv run python -m quiz.app
# → opens http://127.0.0.1:7860/
```

Paste a Markdown URL (a raw URL *or* a GitHub `/blob/` URL both work), pick 5–8 questions, answer through, see your score, inspect the SQLite row.

## What it does

1. **Fetch** — `quiz/sources.py`. Given a URL, normalizes GitHub `/blob/<branch>/…` URLs to their raw equivalent, downloads the Markdown, returns text + SHA-256 content hash for reproducibility.
2. **Generate** — `quiz/generator.py`. Feeds the Markdown to `ChatOpenAI.with_structured_output(QuizSpec)` via a LangChain chain. The LLM is instructed to return 5–8 questions, each with exactly 4 options and a correct-index list. Pydantic validators enforce the shape; the chain retries once on validation failure.
3. **Run & score** — `quiz/app.py` + `quiz/scoring.py`. The Gradio UI walks through questions one at a time (Radio for single-select, CheckboxGroup for multi-select). Scoring rules:
   - **Single-select:** 4 points if the user's selection equals the correct option, 0 otherwise.
   - **Multi-select:** raw score = count of the user's correct picks, capped at 4. False positives do not deduct. *(See "Scoring interpretation" below.)*
   - **Weights:** geometric sequence `w_i = 1.1^(i-1)` for 1-based position `i` — later questions matter more.
   - **Final score:** weighted average `Σ(rawᵢ·wᵢ) / Σ(wᵢ)`, stays in `[0, 4]`.
4. **Persist** — `quiz/storage.py`. SQLite at `quiz.db` (configurable via `QUIZ_DB_PATH`). Three tables: `quiz_runs`, `questions`, `answers`. Every answer is saved as the user submits it; the final score is written when the last question is finalized.

## Architecture

```
pipecat-quickstart/server/
├── bot.py                  # (pre-existing) Pipecat voice agent — untouched
├── quiz/                   # ← the challenge deliverable
│   ├── app.py              # Gradio UI (module entry point)
│   ├── config.py           # env loading, constants
│   ├── sources.py          # MD fetch + GitHub URL normalization
│   ├── schemas.py          # Pydantic models + ScoredAnswer dataclass
│   ├── generator.py        # LangChain + ChatOpenAI, structured output
│   ├── scoring.py          # Pure scoring functions
│   └── storage.py          # SQLite persistence
└── tests/                  # pytest — 60 unit tests
    ├── test_sources.py     (9)
    ├── test_schemas.py     (9)
    ├── test_scoring.py     (25)
    ├── test_storage.py     (12)
    └── test_generator.py   (5, LLM mocked)
```

The existing `pipecat-quickstart/server/bot.py` (a voice-agent scaffold) is left in place as a parallel entry point and is **not** a dependency of the quiz app.

## Key technical choices

| Decision | Rationale |
|---|---|
| **Python** | Task mandates it. Role lists Python as nice-to-have. |
| **LangChain (`ChatOpenAI` + `with_structured_output`)** | Matches role's "LLM orchestration and frameworks like Langchain" expectation. Keeps the door open for the stretch goals below without refactoring. |
| **Pydantic structured output + validators** | Type-safe LLM boundary — bad shapes never reach the scoring/storage layer. |
| **Gradio** | Cleanly maps 4-option MCQs to Radio/CheckboxGroup. Avoids the multi-select-by-voice awkwardness of a Pipecat interface. |
| **SQLite** | Stdlib, file-based, zero ops overhead. Clear relational schema: `quiz_runs` → `questions` → `answers`. |
| **TDD for all pure logic** | Fetcher, schemas, scoring, and storage all have tests written first, watched to fail, then made green. Generator has unit tests at the validation boundary and was live-smoke-tested against OpenAI. |

## Scoring interpretation

The task wording for multi-select scoring is:

> between 0 and 4 - number of correctly selected answers in case of multiple answers question

I interpret this literally as **the count of correct options the user picked, capped at 4**. False positives do not deduct; missed correct answers simply aren't counted.

**Implication:** a multi-select question with, say, 2 correct answers caps out at a raw score of 2, not 4. Perfect play across a quiz with multi-select questions therefore yields a final weighted average *less than* 4.0 — not a bug, but a direct consequence of the task's rule. The alternative interpretations (`correct / total × 4`, or penalizing false positives) were rejected because neither matches the literal wording.

Documented in [quiz/scoring.py](pipecat-quickstart/server/quiz/scoring.py) and [.planning/REQUIREMENTS.md](.planning/REQUIREMENTS.md).

## Env vars

All live in `pipecat-quickstart/server/.env` — see `.env.example` for the full list.

| Variable | Required | Default |
|---|---|---|
| `OPENAI_API_KEY` | yes | — |
| `OPENAI_MODEL` | no | `gpt-4.1` |
| `QUIZ_DB_PATH` | no | `quiz.db` |
| `QUIZ_DEFAULT_URL` | no | `https://github.com/pipecat-ai/pipecat/blob/main/README.md` |

The `_env()` helper in `quiz/config.py` treats whitespace-only or `#`-prefixed values as unset so the pipecat-quickstart template's inline `KEY= # comment` convention doesn't leak comment strings into config.

## Verification

```bash
cd pipecat-quickstart/server
uv run pytest                          # 60 tests pass
uv run python -m quiz.app              # then use the UI
sqlite3 quiz.db "SELECT id, source_url, final_score, completed_at FROM quiz_runs;"
```

## Future extensions (not built in v1)

If the challenge were to grow beyond the current spec, the highest-value additions (in priority order):

1. **Pipecat voice interface** — repurpose the existing `bot.py` to read questions aloud and parse spoken A/B/C/D answers via Deepgram. Showcases voice-agent fluency (Pipecat is a job bonus). UX risk: multi-select is awkward by voice.
2. **Deeper LangChain usage** — move beyond a single structured-output call to a full LCEL pipeline (`MarkdownLoader → SplitChain → RetrievalChain → StructuredOutputChain`) and a `Runnable` agent that can call source-lookup tools.
3. **RAG for long documents** — chunk + embed the source MD, retrieve top-k chunks per question-generation call. Matches the role's RAG requirement and lets the app handle docs beyond the model's context window.
4. **Multi-agent decomposition** — split into `Generator` (drafts questions), `Validator` (confirms each answer is supported by the source text), and `Quizmaster` (runs the session). Shows multi-agent design.
5. **Evaluation suite** — curated (Markdown, expected-properties) pairs + LLM-as-judge scoring for question quality (relevance, difficulty, unambiguous correct answer). Matches the role's "evaluation-driven" language.
6. **MCP server wrapper** — expose `generate_quiz(url, n)` as an MCP tool for any MCP-compatible host.
7. **TypeScript client** — thin Node/TS CLI or Next.js page calling a FastAPI wrapper around the Python quiz — demonstrates the NodeJS side without rewriting the AI logic.

## Project planning artifacts

The [.planning/](.planning/) directory captures the planning trail: `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `config.json`. These aren't required to run the app, but they show how the work was scoped and tracked.

## How this was built

This submission was developed inside **Claude Code** (Anthropic's coding CLI) with two tools layered on top:

- **[GSD](https://github.com/rikkimax/get-shit-done-cc) (Get Shit Done)** — the workflow driver under [.claude/get-shit-done/](.claude/get-shit-done/). GSD is what produced the `.planning/` trail above (PROJECT → REQUIREMENTS → ROADMAP → STATE) and enforced atomic phase commits during the build. The approved pre-execution plan lives outside the repo at `~/.claude/plans/we-are-starting-tender-shore.md`.
- **[Superpowers](https://github.com/obra/superpowers)** — a Claude Code marketplace plugin enabled in [.claude/settings.json](.claude/settings.json) (`"superpowers@superpowers-marketplace": true`). It provides the on-demand skill library (TDD flow, brainstorming, planning helpers) that drove the 7-phase decomposition and the test-first cadence visible across [tests/](pipecat-quickstart/server/tests/).

The human (Ayrton) remained the decision-maker — scoping, locked decisions, scoring interpretation, and every verification step — with Claude Code doing the typing.
