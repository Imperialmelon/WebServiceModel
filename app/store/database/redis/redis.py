import asyncio
import random
from app.logger import logger as context_logger
from ..db import Database


class Redis(Database):
    def __init__(self, name="Redis", latency=0.01, fail_prob=0.02):
        super().__init__(name, latency, fail_prob, True)

    async def get(self, key) -> str | None:
        if not self.available:
            raise Exception(f"{self.name} недоступен")
        await asyncio.sleep(random.uniform(self.latency, 2 * self.latency))
        if random.random() < self.fail_prob:
            raise Exception(f"{self.name} ошибка при get({key})")
        hit = random.random() < 0.8
        return "cached_value" if hit else None

    async def simulate_failure(self):
        logger = context_logger.get_logger()
        while True:
            await asyncio.sleep(random.uniform(20, 40))
            self.available = False
            logger.warning(f"⚠️ {self.name} недоступен")
            await asyncio.sleep(random.uniform(5, 15))
            self.available = True
            logger.info(f"✅ {self.name} восстановлен")
