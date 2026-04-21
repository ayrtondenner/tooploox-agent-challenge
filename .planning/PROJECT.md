# PROJECT: Tooploox Quiz-Agent Code Challenge

## One-line summary

Python agent that fetches a Markdown doc, auto-generates a 5–8 question quiz with LangChain + OpenAI, runs it through a Gradio UI, scores with geometric-weighted average, and persists results in SQLite.

## Why this exists

Code challenge for a **Senior AI NodeJS Engineer** role (Solvd, recruited via Tooploox). See [job_description.md](../job_description.md) and [task_description.txt](../task_description.txt).

The role is NodeJS-primary but the task mandates Python. The "nice to have" list for the role includes Python source-code fluency, LangChain, RAG, Pipecat voice agents, and MCP. So this project's value story is: **build the Python task exactly as specified with polished, senior-level architecture, and hold the stretch ideas in reserve** as documented future work.

## Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python | Task mandates it; role lists Python as nice-to-have |
| Primary UI | Gradio (text) | Installed, maps cleanly to 4-option MCQ; avoids voice-UX awkwardness for multi-select |
| LLM orchestration | LangChain (`ChatOpenAI` + `with_structured_output`) | Already installed; matches role's listed orchestration expectation |
| LLM model | `gpt-4.1` | Matches existing `OPENAI_MODEL` default in `.env` |
| Database | SQLite | Stdlib, file-based, zero ops overhead |
| Project location | `pipecat-quickstart/server/quiz/` | Reuses existing `uv` project |

## Out of scope for v1 (documented as stretches)

Pipecat voice interface · deeper LangChain (agents, LCEL, tools) · RAG chunking · multi-agent decomposition · evaluation suite · MCP server wrapper · TypeScript client. All are listed in the README's "Future Extensions" section so a reviewer sees the thought.

## Stakeholders

- **User** (Ayrton Denner): the candidate.
- **Reviewer**: Solvd/Tooploox hiring panel. Will read the README and the code; may run the app briefly.

## Success criteria

1. Runs end-to-end: `uv run python -m quiz.app` opens Gradio, fetches the pipecat README, generates 5 questions with at least one multi-select, plays through, shows a score, writes to `quiz.db`.
2. All automated tests (`uv run pytest`) pass.
3. Reviewer can read all quiz-module code in ≤15 minutes.
4. README explains the approach, the multi-select scoring interpretation, and links to future-extension ideas.

## Pointers

- **Plan (approved):** `/home/ayrton/.claude/plans/we-are-starting-tender-shore.md`
- **Task spec:** [../task_description.txt](../task_description.txt)
- **Role description:** [../job_description.md](../job_description.md)
- **Existing pipecat bot (untouched):** [../pipecat-quickstart/server/bot.py](../pipecat-quickstart/server/bot.py)
