"""
The sync-capacity endpoint's worker inspection must never raise (observability
should degrade to None, not 500 the endpoint).
"""
from unittest.mock import patch

import backend.api.routes.admin as admin


def test_inspect_workers_returns_none_on_failure():
    with patch("backend.celery_app.celery_app") as celery_app:
        celery_app.control.inspect.side_effect = RuntimeError("broker down")
        assert admin._inspect_workers() is None


def test_inspect_workers_parses_stats():
    fake_stats = {"celery@w1": {"pool": {"max-concurrency": 4}}}
    with patch("backend.celery_app.celery_app") as celery_app:
        celery_app.control.inspect.return_value.stats.return_value = fake_stats
        workers = admin._inspect_workers()
    assert workers == [{"name": "celery@w1", "concurrency": 4}]
