import asyncio
import random
from app.services import service
from app.models import models
from app.store import cluster


class AuthService(service.Service):
    """Отдельный сервис авторизации"""

    def __init__(
            self,
            name,
            metrics_collector,
            db_cluster: cluster.DBCluster,
            cache=None,
            base_latency=0.05,
            fail_prob=0.05,
            requires_auth=False):
        super().__init__(
            name,
            metrics_collector,
            db_cluster,
            cache,
            base_latency,
            fail_prob,
            requires_auth)

    async def handle(self, request: models.Request):
        await self.tcp_handshake()
        await self.tls_handshake()
        if not request.user.authorized:
            await asyncio.sleep(random.uniform(0.05, 0.1))
            request.user.authorized = random.random() < 0.9
            if not request.user.authorized:
                raise Exception("Ошибка авторизации пользователя")
        return
