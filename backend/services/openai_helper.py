"""
Shared OpenAI helper.

Wraps chat.completions.create so a configured model that the current API
key cannot access (model_not_found 404) automatically retries once with a
known-good fallback model, instead of failing the whole AI feature. This
lets operators set OPENAI_MODEL / OPENAI_MODEL_ADVANCED to newer ids
(e.g. gpt-5) without risking a hard outage if the key lacks access.
"""
import logging

from backend.config import settings

logger = logging.getLogger(__name__)


def _is_model_not_found(exc: Exception) -> bool:
    text = str(exc).lower()
    return "model_not_found" in text or "does not exist" in text


def chat_completion(client, *, model: str, **kwargs):
    """Call chat.completions.create, retrying with the fallback model on 404.

    Args:
        client: an initialized OpenAI client
        model: the preferred model id
        **kwargs: passed straight through (messages, temperature, etc.)
    """
    try:
        return client.chat.completions.create(model=model, **kwargs)
    except Exception as exc:  # noqa: BLE001 - narrow via _is_model_not_found
        fallback = settings.OPENAI_MODEL_FALLBACK
        if _is_model_not_found(exc) and fallback and fallback != model:
            logger.warning(
                "Model '%s' unavailable for this API key; retrying with fallback '%s'",
                model,
                fallback,
            )
            return client.chat.completions.create(model=fallback, **kwargs)
        raise
