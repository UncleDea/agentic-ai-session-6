"""Errors raised before or during a model call.

Messages are safe to show. They never include the API key.
"""


class AgentError(Exception):
    """The study agent could not run."""


class EmptySourceError(AgentError):
    """There is no page text to study."""


class MissingApiKeyError(AgentError):
    """OPENAI_API_KEY is not set."""


class ModelResponseError(AgentError):
    """The model reply could not be read."""


class EmptyReplyError(AgentError):
    """The learner submitted a blank answer."""
