"""Gradio UI for the Markdown-powered quiz agent.

Run with::

    uv run python -m quiz.app
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Sequence, Tuple

import gradio as gr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("quiz.app")

from .config import MAX_QUESTIONS, MIN_QUESTIONS, load_settings
from .generator import generate_quiz
from .schemas import Question, ScoredAnswer
from .scoring import compute_weight, score_answer, score_quiz
from .sources import fetch_markdown
from .storage import finalize_run, init_db, record_answer, start_run


# A single module-scoped SQLite connection is shared across all Gradio sessions.
# Gradio dispatches event handlers on anyio's worker-thread pool, so the
# connection is opened with ``check_same_thread=False`` in ``init_db``. We
# additionally serialise DB writes through ``_db_lock`` so multi-statement
# sequences (start_run inserts both a run row and its question rows) remain
# atomic under concurrent requests.
_settings = load_settings()
_conn = init_db(_settings.db_path)
_db_lock = threading.Lock()


def _option_choices(q: Question) -> List[Tuple[str, int]]:
    """(label, value) pairs so Gradio returns the index directly."""
    return [(f"{chr(ord('A') + i)}. {opt}", i) for i, opt in enumerate(q.options)]


def _question_updates(q: Question) -> Tuple[Any, Any]:
    """Build gr.update() values for single/multi-choice widgets for a given question."""
    choices = _option_choices(q)
    if q.is_multi_select:
        return (
            gr.update(choices=[], value=None, visible=False),
            gr.update(choices=choices, value=[], visible=True),
        )
    return (
        gr.update(choices=choices, value=None, visible=True),
        gr.update(choices=[], value=None, visible=False),
    )


def _format_breakdown(questions: Sequence[Question], scored: Sequence[ScoredAnswer]) -> str:
    lines = ["| # | Question | Your answer | Correct | Raw | Weight | Weighted |",
             "|---|----------|-------------|---------|-----|--------|----------|"]
    for q, s in zip(questions, scored):
        user = ", ".join(chr(ord("A") + i) for i in s.selected_indices) or "_(none)_"
        correct = ", ".join(chr(ord("A") + i) for i in q.correct_indices)
        prompt = q.prompt.replace("|", "\\|")
        lines.append(
            f"| {s.position} | {prompt} | {user} | {correct} "
            f"| {s.raw_score:.1f} | {s.weight:.4f} | {s.weighted_score:.4f} |"
        )
    return "\n".join(lines)


def on_generate(url: str, topic: str, n: float, state: Dict[str, Any]):
    """Fetch → generate → start_run → advance to the first question."""
    logger.info("on_generate ENTER url=%r topic=%r n=%s", url, topic, n)
    del state  # new run, discard old state
    n_int = int(n)
    try:
        source = fetch_markdown(url)
    except Exception as e:  # pragma: no cover — UI error path
        logger.exception("on_generate EXIT (fetch failed)")
        return (
            {}, gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(), gr.update(),
            gr.update(value=f"**Fetch failed:** {e}"),
            gr.update(value="Generate Quiz"),
        )

    try:
        spec = generate_quiz(source.text, n_int, topic=topic.strip() or None)
    except Exception as e:  # pragma: no cover — UI error path
        logger.exception("on_generate EXIT (generation failed)")
        return (
            {}, gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(), gr.update(),
            gr.update(value=f"**Generation failed:** {e}"),
            gr.update(value="Generate Quiz"),
        )

    questions = list(spec.questions)
    with _db_lock:
        run_id = start_run(
            _conn,
            source_url=source.url,
            source_md_sha256=source.sha256,
            topic=topic.strip() or None,
            questions=questions,
        )
    q0 = questions[0]
    single_upd, multi_upd = _question_updates(q0)
    is_last = len(questions) == 1
    new_state = {
        "questions": questions,
        "idx": 0,
        "scored": [],
        "run_id": run_id,
    }
    logger.info("on_generate EXIT run_id=%s n_questions=%s", run_id, len(questions))
    return (
        new_state,
        gr.update(visible=False),   # setup view
        gr.update(visible=True),    # quiz view
        gr.update(visible=False),   # results view
        gr.update(value=f"### Question 1 of {len(questions)}"),
        gr.update(value=f"**{q0.prompt}**"),
        single_upd,
        multi_upd,
        gr.update(value=""),
        gr.update(value="Submit" if is_last else "Next →"),
    )


def on_next(
    single_val, multi_val, state: Dict[str, Any]
):
    """Score the current answer, persist it, advance or finalize."""
    questions: List[Question] = state["questions"]
    idx: int = state["idx"]
    scored_so_far: List[ScoredAnswer] = list(state.get("scored", []))
    run_id: int = state["run_id"]
    logger.info(
        "on_next ENTER run_id=%s idx=%s/%s single=%r multi=%r",
        run_id, idx, len(questions), single_val, multi_val,
    )

    q = questions[idx]
    if q.is_multi_select:
        selected = tuple(sorted(set(multi_val or [])))
    else:
        selected = () if single_val is None else (single_val,)

    raw = score_answer(q, selected)
    weight = compute_weight(idx + 1)
    scored = ScoredAnswer(
        position=idx + 1,
        selected_indices=selected,
        raw_score=raw,
        weight=weight,
        weighted_score=raw * weight,
    )
    with _db_lock:
        record_answer(_conn, run_id, scored)
    scored_so_far.append(scored)

    next_idx = idx + 1
    if next_idx >= len(questions):
        # Finalize and switch to results view.
        result = score_quiz(questions, [sa.selected_indices for sa in scored_so_far])
        with _db_lock:
            finalize_run(_conn, run_id, result.final_score)
        breakdown = _format_breakdown(questions, result.scored)
        state["scored"] = scored_so_far
        state["idx"] = next_idx
        logger.info(
            "on_next EXIT (finalize) run_id=%s final_score=%.3f",
            run_id, result.final_score,
        )
        return (
            state,
            gr.update(visible=False),   # setup
            gr.update(visible=False),   # quiz
            gr.update(visible=True),    # results
            gr.update(),                # progress
            gr.update(),                # prompt
            gr.update(choices=[], value=None, visible=False),  # single
            gr.update(choices=[], value=None, visible=False),  # multi
            gr.update(),                # setup_status
            gr.update(value="Submit"),  # button label reset (unused)
            gr.update(
                value=(
                    f"## Final score: **{result.final_score:.3f} / 4.000**\n\n"
                    f"Run ID **{run_id}** saved to `{_settings.db_path}`."
                )
            ),
            gr.update(value=breakdown),
        )

    q_next = questions[next_idx]
    single_upd, multi_upd = _question_updates(q_next)
    is_last = next_idx == len(questions) - 1
    state["scored"] = scored_so_far
    state["idx"] = next_idx
    logger.info(
        "on_next EXIT (advance) run_id=%s next_idx=%s/%s",
        run_id, next_idx, len(questions),
    )
    return (
        state,
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(value=f"### Question {next_idx + 1} of {len(questions)}"),
        gr.update(value=f"**{q_next.prompt}**"),
        single_upd,
        multi_upd,
        gr.update(),
        gr.update(value="Submit" if is_last else "Next →"),
        gr.update(),
        gr.update(),
    )


def on_new():
    logger.info("on_new ENTER/EXIT (reset to setup)")
    return (
        {},
        gr.update(visible=True),   # setup
        gr.update(visible=False),  # quiz
        gr.update(visible=False),  # results
    )


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Markdown Quiz Agent") as app:
        gr.Markdown(
            "# Markdown Quiz Agent\n"
            "Generate a short quiz from any Markdown document on the web."
        )
        state = gr.State({})

        with gr.Group(visible=True) as setup_view:
            url_input = gr.Textbox(
                value=_settings.default_source_url,
                label="Markdown URL",
                placeholder="https://github.com/.../README.md",
            )
            topic_input = gr.Textbox(
                value="",
                label="Topic focus (optional)",
                placeholder="e.g. 'voice transports' or leave blank for full-document coverage",
            )
            n_slider = gr.Slider(
                minimum=MIN_QUESTIONS,
                maximum=MAX_QUESTIONS,
                value=MIN_QUESTIONS,
                step=1,
                label="Number of questions",
            )
            generate_btn = gr.Button("Generate Quiz", variant="primary")
            setup_status = gr.Markdown("")

        with gr.Group(visible=False) as quiz_view:
            progress_md = gr.Markdown("")
            prompt_md = gr.Markdown("")
            single_choice = gr.Radio(choices=[], label="Your answer", visible=False)
            multi_choice = gr.CheckboxGroup(
                choices=[], label="Your answers (select all that apply)", visible=False
            )
            next_btn = gr.Button("Next →", variant="primary")

        with gr.Group(visible=False) as results_view:
            final_score_md = gr.Markdown("")
            breakdown_md = gr.Markdown("")
            new_btn = gr.Button("New quiz")

        generate_btn.click(
            fn=on_generate,
            inputs=[url_input, topic_input, n_slider, state],
            outputs=[
                state,
                setup_view, quiz_view, results_view,
                progress_md, prompt_md, single_choice, multi_choice,
                setup_status, next_btn,
            ],
        )
        next_btn.click(
            fn=on_next,
            inputs=[single_choice, multi_choice, state],
            outputs=[
                state,
                setup_view, quiz_view, results_view,
                progress_md, prompt_md, single_choice, multi_choice,
                setup_status, next_btn,
                final_score_md, breakdown_md,
            ],
        )
        new_btn.click(
            fn=on_new,
            inputs=[],
            outputs=[state, setup_view, quiz_view, results_view],
        )

    return app


def main() -> None:
    app = build_app()
    app.queue(default_concurrency_limit=1, max_size=16)
    app.launch()


if __name__ == "__main__":
    main()
