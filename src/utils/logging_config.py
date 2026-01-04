import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_dir: str = "logs", log_level: str = "INFO"):
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)

    file_handler = RotatingFileHandler(
        log_path / "bot.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(file_formatter)

    error_handler = RotatingFileHandler(
        log_path / "errors.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(log_format, date_format)
    error_handler.setFormatter(error_formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)

    logging.info("Logging configured successfully")
