import asyncio
import random
import time
from app.logger import logger as context_logger
from app.store.database import db
from app.store import cluster
from app.store.database.redis import redis
from app.models import models
from app.broker import rabbitmq
from app.utils import auth
from app.metrics import metrics


class Service:
    def __init__(
            self,
            name: str,
            metrics_collector: metrics.MetricsCollector,
            db_cluster: cluster.DBCluster | None,
            cache: redis.Redis = None,
            base_latency: float = 0.05,
            fail_prob: float = 0.05,
            requires_auth: bool = False,
            broker: rabbitmq.RabbitMQ | None = None
    ):
        self.name = name
        self.db_cluster = db_cluster
        self.metrics_collector = metrics_collector
        self.cache = cache
        self.base_latency = base_latency
        self.fail_prob = fail_prob
        self.available = True
        self.requires_auth = requires_auth
        self.broker = broker

    async def tcp_handshake(self):
        """TCP handshake"""
        await asyncio.sleep(random.uniform(0.01, 0.03))

    async def tls_handshake(self):
        """TLS handshake"""
        await asyncio.sleep(random.uniform(0.02, 0.05))

    @auth.auth_check
    async def handle(self, request: models.Request):
        """Обработка запроса"""
        logger = context_logger.get_logger()
        user = request.user

        start_tcp = time.time()
        await self.tcp_handshake()
        tcp_time = time.time() - start_tcp
        start_tls = time.time()
        await self.tls_handshake()
        tls_time = time.time() - start_tls
        request.tcp_time = tcp_time
        request.tls_time = tls_time

        if not self.available:
            raise Exception(f"Service {self.name} недоступен")

        await asyncio.sleep(random.uniform(self.base_latency, 2 * self.base_latency))
        if random.random() < self.fail_prob:
            raise Exception(f"{self.name} внутренняя ошибка")

        if request.method == models.HTTPMethod.POST:
            if self.db_cluster:
                try:
                    await self.db_cluster.write(f"key-{request.user.id}", f"value-{request.user.id}")
                except Exception as e:
                    logger.warning(
                        f"Кластер {
                            self.db_cluster.name} недоступен")

        else:
            if self.cache:
                data = await self.cache.get("user:" + str(user.id))
                if not data:
                    if self.db_cluster:
                        await self.db_cluster.read("data to get")
            else:
                if self.db_cluster:
                    await self.db_cluster.read("data to get")

        logger.info(f"✅ {self.name} обработал запрос {user.id}")
        if self.broker:
            msg = models.Message(
                topic="messages",
                payload={
                    "service": self.name,
                    "user_id": request.user.id})
            await self.broker.publish(msg)
        return "ok"

    async def simulate_failure(self):
        """Моделирование недоступности сервиса"""
        logger = context_logger.get_logger()
        while True:
            await asyncio.sleep(random.uniform(15, 40))
            self.available = False
            logger.warning(f"⚠️ {self.name} упал")
            self.metrics_collector.infrastructure["service_failures"] += 1
            await asyncio.sleep(random.uniform(5, 15))
            self.available = True
            logger.info(f"✅ {self.name} восстановился")
