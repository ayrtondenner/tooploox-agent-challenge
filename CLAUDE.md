# CLAUDE.md

Repo orientation for Claude Code. Keep this short and load-bearing — the README is the full write-up.

## What this repo is

Tooploox **Senior AI NodeJS Engineer** code challenge. Deliverable is a **Python** Markdown-to-quiz agent that:

1. Fetches a Markdown doc from a URL (handles GitHub `/blob/` → raw).
2. Generates a 5–8 question quiz via **LangChain** `ChatOpenAI.with_structured_output(QuizSpec)`.
3. Runs the quiz in a **Gradio** UI (single-select + multi-select).
4. Scores with a geometric-weighted average and persists everything to **SQLite** (`quiz.db`).

Full write-up, scoring interpretation, and future-extensions list: [README.md](README.md).

## Layout

```
tooploox-agent-challenge/
├── README.md                         # submission write-up (reviewer-facing)
├── pipecat-quickstart/
│   ├── README.md                     # pointer to root + untouched voice-bot docs
│   └── server/                       # the uv project (cwd for all commands)
│       ├── pyproject.toml            # deps: gradio<6, langchain, langchain-openai, pipecat-ai, pytest
│       ├── .env.example
│       ├── bot.py                    # pre-existing Pipecat voice agent — DO NOT TOUCH
│       ├── quiz/                     # the deliverable
│       │   ├── app.py                # Gradio 3-view app (setup → quiz → results)
│       │   ├── config.py             # env loading with inline-comment-tolerant `_env()`
│       │   ├── sources.py            # fetch_markdown() + GitHub /blob/ normalization
│       │   ├── schemas.py            # Pydantic: Question, QuizSpec, ScoredAnswer, QuizResult
│       │   ├── generator.py          # ChatOpenAI.with_structured_output + .with_retry(2)
│       │   ├── scoring.py            # score_answer, compute_weight, weighted_average
│       │   └── storage.py            # SQLite: quiz_runs, questions, answers
│       └── tests/                    # pytest — 60 tests total
│           ├── test_sources.py       # 9
│           ├── test_schemas.py       # 9
│           ├── test_scoring.py       # 25
│           ├── test_storage.py       # 12
│           └── test_generator.py     # 5 (LLM mocked)
├── .planning/                        # GSD planning trail (see below)
└── .claude/                          # Claude Code config (GSD + Superpowers tooling)
```

## Commands (run from `pipecat-quickstart/server/`)

```bash
uv sync                                # install deps
uv run pytest                          # full test suite — expect 60/60
uv run python -m quiz.app              # launch Gradio at http://127.0.0.1:7860
sqlite3 quiz.db "SELECT * FROM quiz_runs;"   # inspect persisted results
```

**Conventions** (from `.planning/config.json`):
- line length 100, lint via `ruff`, types via `pyright`
- tests before commit, atomic commits per phase

## Env vars

All live in `pipecat-quickstart/server/.env` (see `.env.example`). Key ones for the quiz:

| Variable | Required | Default |
|---|---|---|
| `OPENAI_API_KEY` | yes | — |
| `OPENAI_MODEL` | no | `gpt-4.1` |
| `QUIZ_DB_PATH` | no | `quiz.db` |
| `QUIZ_DEFAULT_URL` | no | pipecat README |

The `_env()` helper in `quiz/config.py` treats whitespace-only and `#`-prefixed values as unset (so the scaffold's `KEY= # comment` style doesn't leak comment strings into config).

## Notable design decisions (already locked)

- **Multi-select scoring** uses a *literal* reading of the task wording: raw score = count of the user's correct picks, capped at 4; **false positives do not deduct**. This caps some quizzes below 4.0 by construction — that's intended. See [quiz/scoring.py](pipecat-quickstart/server/quiz/scoring.py) and the "Scoring interpretation" section of the root README.
- **Gradio** was chosen over a Pipecat voice UI because multi-select-by-voice is awkward. Voice is listed as a future extension.
- **LangChain `with_structured_output` + Pydantic validators** — type-safe LLM boundary; malformed shapes never reach scoring/storage.
- **`bot.py` is the original Pipecat voice-agent scaffold**, left untouched as a parallel entry point.

## How this repo was built

Claude Code (Anthropic's coding CLI) drove the typing. Two tools layered on top:

- **GSD (Get Shit Done)** under `.claude/get-shit-done/` — workflow machinery that produced the `.planning/` trail (`PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`). The project was decomposed into 7 phases (8 with a 3a/3b split) executed from an approved plan file at `~/.claude/plans/we-are-starting-tender-shore.md`. Note: this project does **not** use GSD's `.planning/phases/` directory — STATE.md is the authoritative record of phase completion.
- **Superpowers** Claude Code marketplace plugin — enabled via `"superpowers@superpowers-marketplace": true` in [.claude/settings.json](.claude/settings.json). Provides on-demand skills for TDD, brainstorming, and planning that shaped the test-first cadence.

## What to check before changing things

- **Run `uv run pytest` first.** All 60 tests should pass cleanly. If they don't, something upstream is broken — investigate before adding.
- **Don't touch `bot.py`** — it's a parallel entry point and outside the challenge scope.
- **Read `.planning/PROJECT.md`** for locked decisions before proposing architectural changes. In particular: the language is Python, the LLM is `gpt-4.1` via LangChain, and v1 is frozen (see "Out of scope for v1" in PROJECT.md).
- **STATE.md is the source of truth** for "what's done". The `gsd-sdk query roadmap.analyze` parser returns 0 phases because ROADMAP.md uses a table format — ignore that, read STATE.md.
