"""One shared way to call the OpenAI Responses API.

The API key is read from settings and is never written to the log.
"""

import logging
from collections.abc import Callable
from typing import Protocol

from openai import OpenAI

from studymaster.agents.errors import MissingApiKeyError
from studymaster.config import Settings, get_settings

logger = logging.getLogger(__name__)

Completer = Callable[..., str]


class ModelClient(Protocol):
    """The small surface agents use to call a model."""

    def complete(self, *, instructions: str, prompt: str) -> str:
        """Return the model text for one prompt."""


class OpenAIModelClient:
    """Call client.responses.create with the configured model, timeout, and temperature."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.openai_api_key:
            logger.warning("Model call blocked because the API key is missing")
            raise MissingApiKeyError(
                "Add OPENAI_API_KEY to the .env file before generating study material."
            )
        self._client = OpenAI(
            api_key=self._settings.openai_api_key,
            timeout=self._settings.openai_timeout_seconds,
        )

    def complete(self, *, instructions: str, prompt: str) -> str:
        """Send one prompt. The key is not included in the log."""
        logger.info("Model call model=%s", self._settings.openai_model)
        response = self._client.responses.create(
            model=self._settings.openai_model,
            instructions=instructions,
            input=prompt,
            temperature=self._settings.openai_temperature,
            timeout=self._settings.openai_timeout_seconds,
        )
        return response.output_text
