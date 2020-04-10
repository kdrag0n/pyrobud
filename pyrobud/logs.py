import logging

import colorlog

LOG_LEVEL = logging.INFO
LOG_FORMAT = "  %(log_color)s%(levelname)-8s%(reset)s | %(name)-7s | %(log_color)s%(message)s%(reset)s"


def setup_logging() -> None:
    """Configures the logging module with colored level and message formatting."""

    logging.root.setLevel(LOG_LEVEL)
    formatter = colorlog.ColoredFormatter(LOG_FORMAT)

    stream = logging.StreamHandler()
    stream.setLevel(LOG_LEVEL)
    stream.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    root.addHandler(stream)
