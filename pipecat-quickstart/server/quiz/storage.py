"""SQLite persistence for quiz runs, questions, and scored answers."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence

from .schemas import Question, ScoredAnswer

_SCHEMA = """
CREATE TABLE IF NOT EXISTS quiz_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_url TEXT NOT NULL,
  source_md_sha256 TEXT NOT NULL,
  topic TEXT,
  started_at TEXT NOT NULL,
  completed_at TEXT,
  final_score REAL
);

CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL REFERENCES quiz_runs(id),
  position INTEGER NOT NULL,
  prompt TEXT NOT NULL,
  options_json TEXT NOT NULL,
  correct_indices_json TEXT NOT NULL,
  is_multi_select INTEGER NOT NULL,
  UNIQUE (run_id, position)
);

CREATE TABLE IF NOT EXISTS answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question_id INTEGER NOT NULL REFERENCES questions(id),
  selected_indices_json TEXT NOT NULL,
  raw_score REAL NOT NULL,
  weight REAL NOT NULL,
  weighted_score REAL NOT NULL
);
"""


@dataclass(frozen=True)
class LoadedRun:
    run_id: int
    source_url: str
    source_md_sha256: str
    topic: Optional[str]
    started_at: str
    completed_at: Optional[str]
    final_score: Optional[float]
    questions: List[Question]
    scored_answers: List[ScoredAnswer]


def init_db(path: Path) -> sqlite3.Connection:
    # check_same_thread=False: Gradio dispatches handlers on worker threads from
    # anyio's thread pool, so the connection created on the main/import thread
    # needs to be usable from others. The quiz app serialises DB writes with a
    # Lock (see app.py), so sqlite3's own connection-level serialisation is the
    # only concurrency guarantee we rely on.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def start_run(
    conn: sqlite3.Connection,
    source_url: str,
    source_md_sha256: str,
    topic: Optional[str],
    questions: Sequence[Question],
) -> int:
    cursor = conn.execute(
        "INSERT INTO quiz_runs (source_url, source_md_sha256, topic, started_at) "
        "VALUES (?, ?, ?, ?)",
        (source_url, source_md_sha256, topic, _now_iso()),
    )
    run_id = cursor.lastrowid
    assert run_id is not None
    for position, q in enumerate(questions, start=1):
        conn.execute(
            "INSERT INTO questions "
            "(run_id, position, prompt, options_json, correct_indices_json, is_multi_select) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                run_id,
                position,
                q.prompt,
                json.dumps(q.options),
                json.dumps(q.correct_indices),
                1 if q.is_multi_select else 0,
            ),
        )
    conn.commit()
    return run_id


def record_answer(
    conn: sqlite3.Connection,
    run_id: int,
    scored: ScoredAnswer,
) -> None:
    row = conn.execute(
        "SELECT id FROM questions WHERE run_id = ? AND position = ?",
        (run_id, scored.position),
    ).fetchone()
    if row is None:
        raise ValueError(
            f"no question found for run_id={run_id}, position={scored.position}"
        )
    question_id = row[0]
    conn.execute(
        "INSERT INTO answers "
        "(question_id, selected_indices_json, raw_score, weight, weighted_score) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            question_id,
            json.dumps(list(scored.selected_indices)),
            scored.raw_score,
            scored.weight,
            scored.weighted_score,
        ),
    )
    conn.commit()


def finalize_run(conn: sqlite3.Connection, run_id: int, final_score: float) -> None:
    conn.execute(
        "UPDATE quiz_runs SET final_score = ?, completed_at = ? WHERE id = ?",
        (final_score, _now_iso(), run_id),
    )
    conn.commit()


def load_run(conn: sqlite3.Connection, run_id: int) -> Optional[LoadedRun]:
    run_row = conn.execute(
        "SELECT source_url, source_md_sha256, topic, started_at, completed_at, final_score "
        "FROM quiz_runs WHERE id = ?",
        (run_id,),
    ).fetchone()
    if run_row is None:
        return None

    q_rows = conn.execute(
        "SELECT id, position, prompt, options_json, correct_indices_json, is_multi_select "
        "FROM questions WHERE run_id = ? ORDER BY position",
        (run_id,),
    ).fetchall()
    questions = [
        Question(
            prompt=row[2],
            options=json.loads(row[3]),
            correct_indices=json.loads(row[4]),
            is_multi_select=bool(row[5]),
        )
        for row in q_rows
    ]

    scored: list[ScoredAnswer] = []
    for q_row in q_rows:
        question_id, position = q_row[0], q_row[1]
        a_row = conn.execute(
            "SELECT selected_indices_json, raw_score, weight, weighted_score "
            "FROM answers WHERE question_id = ?",
            (question_id,),
        ).fetchone()
        if a_row is None:
            continue
        scored.append(
            ScoredAnswer(
                position=position,
                selected_indices=tuple(json.loads(a_row[0])),
                raw_score=a_row[1],
                weight=a_row[2],
                weighted_score=a_row[3],
            )
        )

    return LoadedRun(
        run_id=run_id,
        source_url=run_row[0],
        source_md_sha256=run_row[1],
        topic=run_row[2],
        started_at=run_row[3],
        completed_at=run_row[4],
        final_score=run_row[5],
        questions=questions,
        scored_answers=scored,
    )
