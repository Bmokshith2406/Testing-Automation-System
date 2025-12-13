import logging
import sys


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure centralized application logging.
    Suitable for both development and production.
    """

    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # ensures handlers are not duplicated during reload
    )


# Project-wide logger namespace (renamed for JavaScript extractor)
logger = logging.getLogger("selenium_javascript_method_extractor")
