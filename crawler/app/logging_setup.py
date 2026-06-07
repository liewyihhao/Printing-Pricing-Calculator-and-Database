"""Structured logging (console + rotating file)."""
from __future__ import annotations

import logging
import sys

import structlog

from . import config

_LOG_FILE = config.CRAWLER_DIR / "crawl.log"


def _configure():
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        ],
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure()
log = structlog.get_logger("printoka")
