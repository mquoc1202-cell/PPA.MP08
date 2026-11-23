import logging
import sys

def setup_logging(log_level: str = "INFO") -> None:
    """Configures centralized standard logging. Print statements are strictly forbidden."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

def get_logger(name: str) -> logging.Logger:
    """Returns a named logger instance adhering to SLF4J / Python logging standard."""
    return logging.getLogger(name)
