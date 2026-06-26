"""Centralized logging configuration for CLI scripts."""

import logging
from datetime import datetime
from pathlib import Path


DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_LOGS_DIR = Path(__file__).resolve().parents[2] / "logs"


def configure_logging(level: int = logging.INFO, fmt: str = DEFAULT_LOG_FORMAT) -> None:
    _LOGS_DIR.mkdir(exist_ok=True)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = _LOGS_DIR / f"pipeline_{run_tag}.log"

    formatter = logging.Formatter(fmt)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logging.basicConfig(level=level, handlers=[file_handler, console_handler])
