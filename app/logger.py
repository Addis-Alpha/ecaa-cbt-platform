import logging
import os
from logging.handlers import RotatingFileHandler

# BUG FIX: "logs" was a RELATIVE path, resolved against whatever
# directory the process happened to be launched from -- not against
# where this file lives. That works fine if you always run
# `python run.py` from the project root, but breaks (wrong location,
# or a crash if that directory isn't writable) the moment the app is
# started any other way: a scheduled task, a Windows service, a
# different terminal cwd, or a production server like gunicorn with
# its own working directory.
#
# Anchoring to this file's own location makes the logs folder land
# in the same place every time, regardless of how/where the app is
# launched. This assumes logger.py lives at app/logger.py, so the
# project root is one level up from this file's directory.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name, filename):
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)

    logger.propagate = False

    return logger


app_logger = get_logger(
    "application",
    "application.log"
)

security_logger = get_logger(
    "security",
    "security.log"
)

error_logger = get_logger(
    "errors",
    "errors.log"
)