# ROADMAP

7 dependency-ordered phases. Each ends in a working atomic commit.

## Milestone 1: v1 Challenge Submission

| # | Phase | Maps to reqs | Deliverables | Verification |
|---|---|---|---|---|
| 1 | Project scaffolding + deps | NF1 | `quiz/__init__.py`, `quiz/config.py`, updated `pyproject.toml` (adds `langchain-openai`, `pytest`), `.gitignore` additions (`quiz.db`, `__pycache__`) | `uv sync` succeeds; `python -c "from quiz import config"` OK |
| 2 | Markdown fetcher | R1 | `quiz/sources.py` with `fetch_markdown(url)` + GitHub `/blob/` → raw URL normalization; `tests/test_sources.py` | `pytest tests/test_sources.py` passes |
| 3 | Schemas + LangChain generator | R2, R3, R4, NF2, NF3, NF4 | `quiz/schemas.py` (Pydantic models with validators), `quiz/generator.py` (`ChatOpenAI` + `with_structured_output`) | Live call against pipecat README returns 5 valid questions (smoke, not unit — requires API key) |
| 4 | Scoring | R5, R6 | `quiz/scoring.py` (`score_answer`, `compute_weights`, `weighted_average`); `tests/test_scoring.py` | All scoring tests pass; hand-computed case matches |
| 5 | SQLite storage | R7, NF5 | `quiz/storage.py` with schema init + `save_run` / `load_run`; `tests/test_storage.py` | Round-trip test passes; FK constraints enforced |
| 6 | Gradio UI | R8 | `quiz/app.py` with 3-state UI (setup → quiz → results) | Manual: launch, complete a quiz, see score, verify `quiz.db` row |
| 7 | README + E2E | (all) | Update root `README.md` and `pipecat-quickstart/README.md`; document multi-select scoring choice + future extensions | Manual smoke test against pipecat README URL |

## Phase dependencies

```
1 ──► 2 ──► 3 ──┐
      │         ├──► 6 ──► 7
      │    4 ───┤
      └──► 5 ───┘
```

- Phases 2, 4, 5 can start after 1.
- Phase 3 needs 2 (for fetching) — but schemas are independent, so schemas could actually land in Phase 1 if convenient. Keeping 3 as a unit for atomicity.
- Phase 6 needs 2, 3, 4, 5 complete.

## Post-v1 (not scheduled)

See "Future Extensions" in `/home/ayrton/.claude/plans/we-are-starting-tender-shore.md` — Pipecat voice, deeper LangChain, RAG, multi-agent, eval suite, MCP, TS client.
