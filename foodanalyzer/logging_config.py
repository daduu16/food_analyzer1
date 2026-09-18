"""Application logging configured from the LOG_LEVEL environment setting."""

from __future__ import annotations

import logging


def configure_logging(log_level: str = "INFO") -> None:
    """Configure a consistent, timestamped root logger without duplicate handlers."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
