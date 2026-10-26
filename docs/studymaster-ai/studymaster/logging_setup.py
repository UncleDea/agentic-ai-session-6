"""Turn on logging for the application.

Other modules should record events with logging.getLogger(__name__).
They should not configure logging themselves.
"""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Set one readable log format for this process."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
