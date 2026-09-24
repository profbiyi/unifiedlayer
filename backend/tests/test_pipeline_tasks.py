"""
Tests for the Celery pipeline execution tasks (run_pipeline, reconcile_stuck_runs).

These run the task bodies eagerly (no broker) with the flow + DB session mocked.
"""
import importlib
from unittest.mock import MagicMock, patch

import pytest

import backend.tasks.pipeline_tasks as pt
from backend.models.pipeline import PipelineStatus


# Every module a Celery worker imports at startup (celery_app.include). A broken
# import here would mean the worker never starts and syncs silently never run —
# guard it in CI since the worker itself isn't exercised there.
CELERY_TASK_MODULES = [
    "backend.tasks.pipeline_tasks",
    "backend.tasks.backfill_tasks",
    "backend.tasks.dbt_tasks",
    "backend.tasks.health_checks",
    "backend.tasks.pipeline_scheduler",
    "backend.tasks.anomaly_tasks",
    "backend.tasks.report_tasks",
    "backend.tasks.summary_tasks",
]


@pytest.mark.parametrize("module_path", CELERY_TASK_MODULES)
def test_celery_task_module_imports(module_path):
    importlib.import_module(module_path)


def test_run_pipeline_success_calls_flow():
    with patch(
        "backend.prefect_flows.pipeline_flow.execute_pipeline_flow",
        return_value={"status": "completed", "stats": {"rows_written": 5}},
    ) as flow:
        result = pt.run_pipeline.apply(args=[1, 42]).get()

    assert result["status"] == "completed"
    flow.assert_called_once_with(1, 42)


def test_run_pipeline_failure_marks_run_failed_and_reraises():
    run = MagicMock()
    run.status = PipelineStatus.RUNNING
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = run

    with patch(
        "backend.prefect_flows.pipeline_flow.execute_pipeline_flow",
        side_effect=RuntimeError("boom"),
    ), patch("backend.database.get_db_session", return_value=db):
        eager = pt.run_pipeline.apply(args=[1, 42])

    assert eager.failed()
    assert run.status == PipelineStatus.FAILED
    assert "boom" in run.error_message
    db.commit.assert_called_once()


def test_mark_run_failed_noop_when_already_completed():
    run = MagicMock()
    run.status = PipelineStatus.COMPLETED
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = run

    with patch("backend.database.get_db_session", return_value=db):
        pt._mark_run_failed(7, "should not apply")

    # A completed run must not be flipped to FAILED.
    assert run.status == PipelineStatus.COMPLETED
    db.commit.assert_not_called()


def test_reconcile_stuck_runs_fails_orphans():
    r1, r2 = MagicMock(), MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [r1, r2]

    with patch("backend.database.get_db_session", return_value=db):
        out = pt.reconcile_stuck_runs(max_age_hours=2)

    assert out["failed"] == 2
    assert r1.status == PipelineStatus.FAILED
    assert r2.status == PipelineStatus.FAILED
    db.commit.assert_called_once()


def test_reconcile_stuck_runs_noop_when_none():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []

    with patch("backend.database.get_db_session", return_value=db):
        out = pt.reconcile_stuck_runs()

    assert out["failed"] == 0
    db.commit.assert_not_called()


def _fake_fairness_db(org_running, others_waiting, pipe_org=5):
    """count() is called for org_running first, then others_waiting."""
    db = MagicMock()
    q = db.query.return_value
    q.filter.return_value.first.return_value = MagicMock(organization_id=pipe_org)
    q.join.return_value.filter.return_value.count.side_effect = [org_running, others_waiting]
    return db


def test_fairness_allows_within_fair_share(monkeypatch):
    monkeypatch.setattr(pt, "_MAX_ORG_CONCURRENCY", 3)
    # org running 2 (< 3) -> allowed regardless of who else is waiting
    with patch("backend.database.get_db_session", return_value=_fake_fairness_db(2, 9)):
        assert pt._should_defer_for_fairness(1, 99) is False


def test_fairness_defers_when_over_share_and_others_waiting(monkeypatch):
    monkeypatch.setattr(pt, "_MAX_ORG_CONCURRENCY", 3)
    with patch("backend.database.get_db_session", return_value=_fake_fairness_db(5, 2)):
        assert pt._should_defer_for_fairness(1, 99) is True


def test_fairness_allows_burst_when_no_one_waiting(monkeypatch):
    monkeypatch.setattr(pt, "_MAX_ORG_CONCURRENCY", 3)
    # org bursting to 10 (over share) but NO other org waiting -> allowed
    with patch("backend.database.get_db_session", return_value=_fake_fairness_db(10, 0)):
        assert pt._should_defer_for_fairness(1, 99) is False


def test_fairness_disabled_when_zero(monkeypatch):
    monkeypatch.setattr(pt, "_MAX_ORG_CONCURRENCY", 0)
    assert pt._should_defer_for_fairness(1, 99) is False
