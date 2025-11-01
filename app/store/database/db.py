import asyncio
import random
from typing import Any
from app.metrics import metrics


class Database:
    def __init__(
            self,
            name: str,
            metrics_collector: metrics.MetricsCollector,
            latency: float,
            fail_prob: float,
            available: bool):
        self.name = name
        self.metrics_collector = metrics_collector
        self.latency = latency
        self.fail_prob = fail_prob
        self.available = True

    async def get(self, *args):
        pass

    async def put(self, key: str, value: Any):
        if not self.available:
            raise Exception(f"{self.name} недоступен")
        await asyncio.sleep(random.uniform(self.latency, 2 * self.latency))
        if random.random() < self.fail_prob:
            raise Exception(f"{self.name} ошибка при put({key, value})")

    async def simulate_failure(self):
        pass
