import contextvars
import logging
from contextlib import asynccontextmanager

logger_var = contextvars.ContextVar("logger")


def get_logger() -> contextvars.ContextVar:
    """Получение логгера"""
    return logger_var.get()


def setup_logger() -> logging.Logger:
    """Установка логгера"""
    logger = logging.getLogger("simulation")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger


@asynccontextmanager
async def app_logger():
    """Асинхронный менеджер контекста для логгера"""
    logger = setup_logger()
    token = logger_var.set(logger)
    try:
        yield logger
    finally:
        logger_var.reset(token)