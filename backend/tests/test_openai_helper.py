"""Tests for the OpenAI fallback helper."""
from unittest.mock import MagicMock

import pytest

from backend.services.openai_helper import chat_completion
from backend.config import settings


def _client_that(side_effect):
    client = MagicMock()
    client.chat.completions.create.side_effect = side_effect
    return client


def test_model_not_found_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_MODEL_FALLBACK", "gpt-4o-mini")
    tried = []

    def side_effect(model, **kwargs):
        tried.append(model)
        if model == "gpt-5":
            raise Exception(
                "Error code: 404 - {'error': {'code': 'model_not_found', "
                "'message': 'The model gpt-5 does not exist'}}"
            )
        return "ok"

    result = chat_completion(_client_that(side_effect), model="gpt-5", messages=[])
    assert result == "ok"
    assert tried == ["gpt-5", "gpt-4o-mini"]


def test_happy_path_does_not_retry():
    tried = []

    def side_effect(model, **kwargs):
        tried.append(model)
        return "ok"

    result = chat_completion(_client_that(side_effect), model="gpt-4o-mini", messages=[])
    assert result == "ok"
    assert tried == ["gpt-4o-mini"]


def test_non_model_error_is_reraised():
    def side_effect(model, **kwargs):
        raise Exception("rate limit exceeded")

    with pytest.raises(Exception, match="rate limit"):
        chat_completion(_client_that(side_effect), model="gpt-4o-mini", messages=[])


def test_no_fallback_loop_when_fallback_equals_model(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_MODEL_FALLBACK", "gpt-4o-mini")
    tried = []

    def side_effect(model, **kwargs):
        tried.append(model)
        raise Exception("model_not_found: does not exist")

    with pytest.raises(Exception, match="model_not_found"):
        chat_completion(_client_that(side_effect), model="gpt-4o-mini", messages=[])
    # Only tried once — no infinite retry when fallback == model
    assert tried == ["gpt-4o-mini"]
