import asyncio
import random
import time
import matplotlib.pyplot as plt
from .logger import logger as context_logger
from .metrics import metrics
from .services import service
from .services.auth_service import auth_service
from app.store.database.postgres import postgres
from app.store.database.redis import redis
from app.balance_loader import nginx
from .models import models


class Application:
    def __init__(self):
        self.duration = 15
        self.metrics_collector = metrics.MetricsCollector()
        self.auth_service = auth_service.AuthService(
            "AuthService", db=redis.Redis(
                name="AuthRedis"), base_latency=0.05)
        self.load_balancer = nginx.Nginx()

        payment_instances = [
            service.Service(
                "PaymentService",
                db=postgres.PostgresDB(name=f"PaymentPostgres{i}"),
                base_latency=0.1,
                requires_auth=True
            ) for i in range(3)
        ]
        data_instances = [
            service.Service(
                "DataService",
                db=postgres.PostgresDB(name=f"DataPostgres{i}"),
                cache=redis.Redis(name=f"CacheRedis{i}"),
                base_latency=0.07,
                requires_auth=True
            ) for i in range(2)
        ]
        public_instances = [
            service.Service(
                "PublicInfoService",
                db=postgres.PostgresDB(name=f"PublicPostgres{i}"),
                base_latency=0.03,
                requires_auth=False
            ) for i in range(2)
        ]

        weights = [7, 3]

        self.load_balancer.add_instances(
            "PaymentService", payment_instances, weights)
        self.load_balancer.add_instances(
            "DataService", data_instances, weights)
        self.load_balancer.add_instances(
            "PublicInfoService", public_instances, weights)

        self.services = [self.auth_service] + \
            payment_instances + data_instances + public_instances
        self.resources = []
        for s in self.services:
            if hasattr(s, 'db') and s.db is not None:
                self.resources.append(s.db)
            if hasattr(s, 'cache') and s.cache is not None:
                self.resources.append(s.cache)

    async def generate_requests(self):
        """Генерация запросов"""
        users = []
        user_id = 0
        start_time = time.time()
        logger = context_logger.get_logger()

        while time.time() - start_time < self.duration:
            if random.random() <= 0.5 and users:
                user = random.choice(users)
            else:
                user = models.User(user_id)
                users.append(user)
            auth_req = models.Request(user, "AuthService")
            try:
                await self.auth_service.handle(auth_req)
                auth_req.success = True
            except Exception:
                auth_req.success = False
            finally:
                auth_req.end_time = time.time()
                self.metrics_collector.record(auth_req)

            service_name = random.choice(
                ["PaymentService", "DataService", "PublicInfoService"])
            try:
                service_instance = self.load_balancer.get_instance(
                    service_name)
            except Exception as e:
                logger.error(str(e))

            req = models.Request(user, service_instance.name)
            asyncio.create_task(self.process_request(req, service_instance))
            user_id += 1
            await asyncio.sleep(random.uniform(0.05, 0.2))
        logger.info("Генерация запросов завершена")

    async def process_request(
            self,
            request: models.Request,
            service: service.Service):
        """Обработка запросов"""
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
        """Запуск приложения"""
        logger = context_logger.get_logger()
        for r in self.resources:
            asyncio.create_task(r.simulate_failure())
        for s in self.services:
            asyncio.create_task(s.simulate_failure())
        await self.generate_requests()
        logger.info("✅ Симуляция завершена")
        summary = self.metrics_collector.get_service_summary()
        logger.info("📊 Итоги по сервисам:")
        for name, stats in summary.items():
            logger.info(
                f"{name}: OK={stats['success']} ERR={stats['error']} "
                f"RT={stats['avg_response']:.3f}s "
                f"DB={stats['avg_db']:.3f}s CACHE={stats['avg_cache']:.3f}s "
                f"TCP={stats['avg_tcp']:.3f}s TLS={stats['avg_tls']:.3f}s"
            )

    def visualize(self):
        """Визуализация"""
        times, rps, errors = self.metrics_collector.get_rps_series()
        lat_stats = self.metrics_collector.get_latency_stats()
        tcp_tls = self.metrics_collector.get_tcp_tls_avg()

        plt.figure(figsize=(12, 8))

        plt.subplot(3, 1, 1)
        plt.plot(times, rps, label="RPS")
        plt.plot(times, errors, label="Ошибки", color="red")
        plt.title("Запросы и ошибки во времени")
        plt.legend()

        plt.subplot(3, 1, 2)
        plt.hist(self.metrics_collector.response_times, bins=20, alpha=0.7)
        plt.title(
            f"Latency avg={
                lat_stats['avg']:.3f}s  p95={
                lat_stats['p95']:.3f}s  p99={
                lat_stats['p99']:.3f}s")

        plt.subplot(3, 1, 3)
        plt.bar(["TCP avg", "TLS avg"], [tcp_tls["tcp_avg"],
                tcp_tls["tls_avg"]], color=["blue", "orange"])
        plt.title("Среднее время TCP / TLS соединений")

        plt.tight_layout()
        plt.show()
