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


def _fake_capacity_db(running_count, pipe_org=5):
    db = MagicMock()
    q = db.query.return_value
    q.filter.return_value.first.return_value = MagicMock(organization_id=pipe_org)
    q.join.return_value.filter.return_value.count.return_value = running_count
    return db


def test_org_at_capacity_true_when_at_cap(monkeypatch):
    monkeypatch.setattr(pt, "_MAX_ORG_CONCURRENCY", 3)
    with patch("backend.database.get_db_session", return_value=_fake_capacity_db(3)):
        assert pt._org_at_capacity(1, 99) is True


def test_org_at_capacity_false_when_under_cap(monkeypatch):
    monkeypatch.setattr(pt, "_MAX_ORG_CONCURRENCY", 3)
    with patch("backend.database.get_db_session", return_value=_fake_capacity_db(2)):
        assert pt._org_at_capacity(1, 99) is False


def test_org_at_capacity_disabled_when_zero(monkeypatch):
    monkeypatch.setattr(pt, "_MAX_ORG_CONCURRENCY", 0)
    # Cap disabled -> never at capacity, no DB call needed.
    assert pt._org_at_capacity(1, 99) is False
