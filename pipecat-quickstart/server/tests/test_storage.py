"""Tests for quiz/storage.py — SQLite persistence for runs, questions, answers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from quiz.schemas import Question, ScoredAnswer
from quiz.storage import finalize_run, init_db, load_run, record_answer, start_run


def _q(i: int, correct: list[int]) -> Question:
    return Question(
        prompt=f"Question {i}",
        options=[f"opt-{i}-a", f"opt-{i}-b", f"opt-{i}-c", f"opt-{i}-d"],
        correct_indices=correct,
        is_multi_select=len(correct) > 1,
    )


@pytest.fixture
def conn(tmp_path: Path):
    c = init_db(tmp_path / "test.db")
    yield c
    c.close()


class TestInitDb:
    def test_creates_expected_tables(self, conn):
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        tables = [r[0] for r in rows]
        assert "quiz_runs" in tables
        assert "questions" in tables
        assert "answers" in tables

    def test_enables_foreign_keys(self, conn):
        (fk_on,) = conn.execute("PRAGMA foreign_keys").fetchone()
        assert fk_on == 1


class TestStartRun:
    def test_returns_integer_run_id(self, conn):
        run_id = start_run(
            conn,
            source_url="https://example.com/doc.md",
            source_md_sha256="deadbeef",
            topic=None,
            questions=[_q(1, [0]), _q(2, [1, 2])],
        )
        assert isinstance(run_id, int)
        assert run_id > 0

    def test_persists_run_metadata(self, conn):
        run_id = start_run(
            conn,
            source_url="https://example.com/doc.md",
            source_md_sha256="deadbeef",
            topic="Pipecat",
            questions=[_q(1, [0])],
        )
        row = conn.execute(
            "SELECT source_url, source_md_sha256, topic, started_at, completed_at, final_score "
            "FROM quiz_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        assert row[0] == "https://example.com/doc.md"
        assert row[1] == "deadbeef"
        assert row[2] == "Pipecat"
        assert row[3] is not None  # started_at populated
        assert row[4] is None  # completed_at not set yet
        assert row[5] is None  # final_score not set yet

    def test_persists_questions_with_1_based_position(self, conn):
        questions = [_q(1, [0]), _q(2, [1, 2]), _q(3, [3])]
        run_id = start_run(
            conn, source_url="u", source_md_sha256="h", topic=None, questions=questions
        )
        rows = conn.execute(
            "SELECT position, prompt, options_json, correct_indices_json, is_multi_select "
            "FROM questions WHERE run_id = ? ORDER BY position",
            (run_id,),
        ).fetchall()
        assert [r[0] for r in rows] == [1, 2, 3]
        assert [r[1] for r in rows] == ["Question 1", "Question 2", "Question 3"]
        assert rows[1][4] == 1  # question 2 is multi-select
        assert rows[0][4] == 0  # question 1 is single-select

    def test_second_run_gets_distinct_id(self, conn):
        r1 = start_run(conn, source_url="u", source_md_sha256="h", topic=None, questions=[_q(1, [0])])
        r2 = start_run(conn, source_url="u", source_md_sha256="h", topic=None, questions=[_q(1, [0])])
        assert r1 != r2


class TestRecordAnswer:
    def test_persists_answer_linked_to_question(self, conn):
        questions = [_q(1, [0]), _q(2, [1, 2])]
        run_id = start_run(
            conn, source_url="u", source_md_sha256="h", topic=None, questions=questions
        )
        scored = ScoredAnswer(
            position=1,
            selected_indices=(0,),
            raw_score=4.0,
            weight=1.0,
            weighted_score=4.0,
        )
        record_answer(conn, run_id, scored)

        row = conn.execute(
            "SELECT selected_indices_json, raw_score, weight, weighted_score FROM answers"
        ).fetchone()
        assert row[0] == "[0]"
        assert row[1] == 4.0
        assert row[2] == 1.0
        assert row[3] == 4.0

    def test_rejects_unknown_position(self, conn):
        run_id = start_run(
            conn, source_url="u", source_md_sha256="h", topic=None, questions=[_q(1, [0])]
        )
        bogus = ScoredAnswer(
            position=99, selected_indices=(0,), raw_score=4.0, weight=1.0, weighted_score=4.0
        )
        with pytest.raises(ValueError, match="position"):
            record_answer(conn, run_id, bogus)


class TestFinalizeRun:
    def test_sets_final_score_and_completed_at(self, conn):
        run_id = start_run(
            conn, source_url="u", source_md_sha256="h", topic=None, questions=[_q(1, [0])]
        )
        finalize_run(conn, run_id, 3.14)
        row = conn.execute(
            "SELECT final_score, completed_at FROM quiz_runs WHERE id = ?", (run_id,)
        ).fetchone()
        assert row[0] == 3.14
        assert row[1] is not None


class TestLoadRun:
    def test_roundtrips_full_run(self, conn):
        questions = [_q(1, [0]), _q(2, [1, 2])]
        run_id = start_run(
            conn,
            source_url="https://example.com/d.md",
            source_md_sha256="cafef00d",
            topic="topic-x",
            questions=questions,
        )
        scores = [
            ScoredAnswer(1, (0,), 4.0, 1.0, 4.0),
            ScoredAnswer(2, (1, 2), 2.0, 1.1, 2.2),
        ]
        for s in scores:
            record_answer(conn, run_id, s)
        finalize_run(conn, run_id, 2.95238)

        loaded = load_run(conn, run_id)
        assert loaded.run_id == run_id
        assert loaded.source_url == "https://example.com/d.md"
        assert loaded.source_md_sha256 == "cafef00d"
        assert loaded.topic == "topic-x"
        assert loaded.final_score == 2.95238
        assert len(loaded.questions) == 2
        assert loaded.questions[0].prompt == "Question 1"
        assert loaded.questions[1].correct_indices == [1, 2]
        assert len(loaded.scored_answers) == 2
        assert loaded.scored_answers[0].raw_score == 4.0
        assert loaded.scored_answers[1].selected_indices == (1, 2)

    def test_missing_run_returns_none(self, conn):
        assert load_run(conn, 9999) is None


class TestCrossThreadUsage:
    """Gradio invokes handlers on worker threads, so a connection opened on the
    main thread must be usable from other threads. Regression test for the
    ``sqlite3.ProgrammingError: SQLite objects created in a thread can only be
    used in that same thread`` crash that hit on first use of Generate Quiz.
    """

    def test_connection_usable_from_worker_thread(self, conn):
        questions = [_q(1, [0])]

        def _do_writes() -> int:
            run_id = start_run(
                conn,
                source_url="u",
                source_md_sha256="h",
                topic=None,
                questions=questions,
            )
            record_answer(
                conn,
                run_id,
                ScoredAnswer(1, (0,), 4.0, 1.0, 4.0),
            )
            finalize_run(conn, run_id, 4.0)
            return run_id

        with ThreadPoolExecutor(max_workers=1) as ex:
            run_id = ex.submit(_do_writes).result()

        loaded = load_run(conn, run_id)
        assert loaded is not None
        assert loaded.final_score == 4.0
