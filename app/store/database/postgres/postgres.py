import asyncio
import random
from app.logger import logger as context_logger
from ..db import Database



class PostgresDB(Database):
    def __init__(self, name : str = "Postgres", latency : float = 0.15, fail_prob : float = 0.03):
        super().__init__(name, latency, fail_prob, True)

    async def get(self, sql: str) -> dict:
        if not self.available:
            raise Exception(f"{self.name} недоступен")
        await asyncio.sleep(random.uniform(self.latency, 2 * self.latency))
        if random.random() < self.fail_prob:
            raise Exception(f"{self.name} ошибка при запросе")
        return {"result": "some_data"}

    async def simulate_failure(self):
        logger = context_logger.get_logger()
        while True:
            await asyncio.sleep(random.uniform(30, 50))
            self.available = False
            logger.error(f"💥 {self.name} упал")
            await asyncio.sleep(random.uniform(10, 20))
            self.available = True
            logger.info(f"✅ {self.name} восстановлен")