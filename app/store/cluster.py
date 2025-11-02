import asyncio
import random
import time
from typing import Any
from app.store.database import db
from app.logger import logger as context_logger


class DBCluster:
    """Имитация кластера баз данных с master-slave репликацией."""

    def __init__(self,
                 name: str,
                 master: db.Database,
                 replicas: list[db.Database],
                 replication_delay: float = 0.1):
        self.name = name
        self.master = master
        self.replicas = replicas
        self.replication_delay = replication_delay
        self.failed_masters = []
        self.current_master = master
        self.failover_in_progress = False

    async def replicate(self, key: str, value: Any):
        """Имитация задержки репликации данных на слейвы."""
        await asyncio.sleep(self.replication_delay)
        logger = context_logger.get_logger()
        for replica in self.replicas:
            if replica.available:
                try:
                    await replica.put(key, value)
                except Exception as e:
                    logger.error(e)

        
        logger.info(f"🔄 Репликация ключа '{key}' завершена")

    async def write(self, key: str, value: str):
        """Запись в master и репликация."""
        if not self.current_master.available:
            await self.failover()
        await self.current_master.put(key, value)
        asyncio.create_task(self.replicate(key, value))

    async def read(self, key: str):
        """Чтение — чаще из реплики, иногда из master."""
        if random.random() < 0.7 and self.replicas:
            replica = random.choice(self.replicas)
            if replica.available:
                return await replica.get(key)
        return await self.current_master.get(key)

    async def failover(self):
        """Переключение на новую master-ноду."""
        if self.failover_in_progress:
            return

        logger = context_logger.get_logger()
        self.failover_in_progress = True
        logger.warning(
            f"⚠️ Master {
                self.current_master.name} недоступен. Инициируем failover")

        available_replicas = [
            replica for replica in self.replicas if replica.available]
        if not available_replicas:
            logger.error("❌ Нет доступных реплик для failover!")
            self.failover_in_progress = False
            raise Exception("Все узлы БД недоступны")

        new_master = random.choice(available_replicas)
        self.replicas.remove(new_master)
        self.replicas.append(self.current_master)
        self.failed_masters.append(self.current_master)
        self.current_master = new_master

        logger.info(f"✅ Реплика {new_master.name} стала новым master")
        self.failover_in_progress = False

    async def monitor_master(self, interval: float = 5.0):
        """Фоновый мониторинг master и автоматический failover."""
        logger = context_logger.get_logger()
        while True:
            await asyncio.sleep(interval)
            if not self.current_master.available:
                try:
                    await self.failover()
                except Exception:
                    logger.warning(f"Кластер {self.name} полностью недоступен")

            recovered = [m for m in self.failed_masters if m.available]
            if recovered:
                old_master = recovered.pop()
                logger.info(
                    f"🔁 Старый мастер {
                        old_master.name} снова доступен — выполняет роль реплики")
                self.failed_masters.remove(old_master)
                self.replicas.append(old_master)
