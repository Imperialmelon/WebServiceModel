from functools import wraps
from typing import Callable
from app.models import models
from app.logger import logger as context_logger


def auth_check(func: Callable) -> Callable:
    """Проверка авторизации"""
    @wraps(func)
    async def wrapper(
            self,
            request: models.Request,
            *args,
            **kwargs) -> Callable:
        if not request.user.authorized:
            logger = context_logger.get_logger()
            logger.warning(
                f"🚫 Пользователь {
                    request.user.id} не авторизован для {
                    self.name}")
            raise PermissionError("Пользователь не авторизован")
        return await func(self, request, *args, **kwargs)
    return wrapper
