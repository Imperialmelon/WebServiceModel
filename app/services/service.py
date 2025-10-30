import asyncio
import random
from app.logger import logger as context_logger
from app.store.database import db
from app.store.database.redis import redis
from app.models import models

class Service:
    def __init__(self, name: str, db : db.Database = None, cache : redis.Redis = None, base_latency : float = 0.05, fail_prob : float = 0.05, requires_auth : bool = False):
        self.name = name
        self.db = db
        self.cache = cache
        self.base_latency = base_latency
        self.fail_prob = fail_prob
        self.available = True
        self.requires_auth = requires_auth

    async def tcp_handshake(self):
        await asyncio.sleep(random.uniform(0.01, 0.03))
    
    async def tls_handshake(self):
        await asyncio.sleep(random.uniform(0.02, 0.05))

    async def handle(self, request: models.Request):
        logger = context_logger.get_logger()
        user = request.user

        await self.tcp_handshake()
        await self.tls_handshake()

        if not self.available:
            raise Exception(f"Service {self.name} недоступен")


        if self.requires_auth and not user.authorized:
            raise Exception(f"Пользователь {user.id} не авторизован для {self.name}")

        await asyncio.sleep(random.uniform(self.base_latency, 2 * self.base_latency))
        if random.random() < self.fail_prob:
            raise Exception(f"{self.name} внутренняя ошибка")

        if self.cache:
            data = await self.cache.get("user:" + str(user.id))
            if not data and self.db:
                await self.db.get("data to get")
        elif self.db:
            await self.db.get("data to get")

        logger.debug(f"✅ {self.name} обработал запрос {user.id}")
        return "ok"

    async def simulate_failure(self):
        logger = context_logger.get_logger()
        while True:
            await asyncio.sleep(random.uniform(15, 40))
            self.available = False
            logger.warning(f"⚠️ {self.name} упал")
            await asyncio.sleep(random.uniform(5, 15))
            self.available = True
            logger.info(f"✅ {self.name} восстановился")
