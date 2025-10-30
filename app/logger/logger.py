import contextvars
import logging

logger_var = contextvars.ContextVar("logger")

def get_logger():
    return logger_var.get()

def setup_logger():
    logger = logging.getLogger("simulation")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger
