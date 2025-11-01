import asyncio
import random
from typing import Any
from app.logger import logger as context_logger
from app.metrics import metrics
from ..db import Database


class Redis(Database):
    def __init__(
            self,
            metrics_collector: metrics.MetricsCollector,
            name="Redis",
            latency=0.01,
            fail_prob=0.02):
        super().__init__(name, metrics_collector, latency, fail_prob, True)

    async def get(self, key) -> str | None:
        """Моделирование получение данных"""
        if not self.available:
            raise Exception(f"{self.name} недоступен")
        await asyncio.sleep(random.uniform(self.latency, 2 * self.latency))
        if random.random() < self.fail_prob:
            raise Exception(f"{self.name} ошибка при get({key})")
        hit = random.random() < 0.8
        return "cached_value" if hit else None

    async def simulate_failure(self):
        """Моделирование недоступности бд"""
        logger = context_logger.get_logger()
        while True:
            await asyncio.sleep(random.uniform(20, 40))
            self.available = False
            if "cache" in self.name.lower():
                self.metrics_collector.infrastructure["cache_failures"] += 1
            else:
                self.metrics_collector.infrastructure["db_failures"] += 1
            logger.warning(f"⚠️ {self.name} недоступен")
            await asyncio.sleep(random.uniform(5, 15))
            self.available = True
            logger.info(f"✅ {self.name} восстановлен")
