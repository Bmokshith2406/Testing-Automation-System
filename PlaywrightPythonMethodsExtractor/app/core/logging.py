import logging
import sys


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure centralized application logging for the
    Playwright Python Method Extractor.
    """

    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # ensures no duplicate handlers across reloads
    )


# Project-wide logger namespace
logger = logging.getLogger("playwright_python_method_extractor")
