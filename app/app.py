import asyncio
import random
import time
import matplotlib.pyplot as plt
from .logger import logger as context_logger
from .metrics import metrics
from .store import store
from .services import service
from .services.auth_service import auth_service
from .models import models

class Application:
    def __init__(self):
        self.duration = 60
        self.metrics_collector = metrics.MetricsCollector()
        self.store = store.Store()
        self.auth_service = auth_service.AuthService("AuthService", db = self.redis, base_latency=0.05)
        self.services = [
            self.auth_service,
            service.Service("PaymentService", db=self.postgres, base_latency=0.1, requires_auth=True),
            service.Service("DataService", db=self.postgres, cache=self.redis, base_latency=0.07, requires_auth=True),
            service.Service("PublicInfoService", base_latency=0.03, requires_auth=False)
        ]

    @property
    def postgres(self):
        return self.store.postgres

    @property
    def redis(self):
        return self.store.redis
    
    async def generate_requests(self):
        user_id = 0
        start_time = time.time()
        logger = context_logger.get_logger()

        while time.time() - start_time < self.duration:
            user = models.User(user_id)
            auth_req = models.Request(user, "AuthService")
            try:
                await self.auth_service.handle(auth_req)
                auth_req.success = True
            except Exception:
                auth_req.success = False
            finally:
                auth_req.end_time = time.time()
                self.metrics_collector.record(auth_req)

            service = random.choice(self.services[1:])
            req = models.Request(user, service.name)
            asyncio.create_task(self.process_request(req, service))
            user_id += 1
            await asyncio.sleep(random.uniform(0.05, 0.2))
        logger.info("🚀 Генерация запросов завершена")

    async def process_request(self, request : models.Request, service : service.Service):
        logger = context_logger.get_logger()
        try:
            await service.handle(request)
            request.success = True
        except Exception as e:
            request.success = False
            logger.debug(f"❌ Ошибка при {request.service_name}: {e}")
        finally:
            request.end_time = time.time()
            self.metrics_collector.record(request)
    

    async def run(self):
        logger = context_logger.get_logger()
        asyncio.create_task(self.redis.simulate_failure())
        asyncio.create_task(self.postgres.simulate_failure())
        for s in self.services:
            asyncio.create_task(s.simulate_failure())
        await self.generate_requests()
        logger.info("✅ Симуляция завершена")

    def visualize(self):
        times, rps, errors = self.metrics_collector.get_rps_series()

        plt.figure(figsize=(10, 6))
        plt.subplot(2, 1, 1)
        plt.plot(times, rps, label="RPS")
        plt.plot(times, errors, label="Ошибки", color="red")
        plt.title("Запросы и ошибки во времени")
        plt.xlabel("Время (сек)")
        plt.ylabel("Количество")
        plt.legend()

        plt.subplot(2, 1, 2)
        plt.hist(self.metrics_collector.response_times, bins=20, alpha=0.7)
        plt.title("Распределение времени отклика")
        plt.xlabel("Секунды")
        plt.ylabel("Количество")
        plt.tight_layout()
        plt.show()