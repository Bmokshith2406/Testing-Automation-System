import logging
import sys


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure centralized application logging.
    """

    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # ensures no duplicate handlers
    )


# Project-wide logger namespace
logger = logging.getLogger("selenium_python_method_extractor")
