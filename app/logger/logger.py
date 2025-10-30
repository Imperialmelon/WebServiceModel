import contextvars
import logging

logger_var = contextvars.ContextVar("logger")


def get_logger() -> contextvars.ContextVar:
    return logger_var.get()


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("simulation")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger
