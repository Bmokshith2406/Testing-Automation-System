import logging


def setup_logging() -> logging.Logger:
    try:
        # Avoid adding duplicate handlers if logging is already configured
        root = logging.getLogger()
        if not root.handlers:

            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            )

        logger = logging.getLogger("testcase-search")

        return logger

    except Exception:
        # Absolute fallback — never allow logging setup to crash the app
        try:
            logger = logging.getLogger("testcase-search")
            logger.setLevel(logging.INFO)

            if not logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
                )
                handler.setFormatter(formatter)
                logger.addHandler(handler)

            return logger

        except Exception:
            # Final fallback — return root logger to avoid total failure
            return logging.getLogger()


logger = setup_logging()
