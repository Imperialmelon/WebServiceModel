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
from app.store import cluster
from app.balance_loader import nginx
from app.broker import rabbitmq
from .models import models


class Application:
    def __init__(self):
        self.duration = 50
        self.metrics_collector = metrics.MetricsCollector()
        self.load_balancer = nginx.Nginx()
        self.broker = rabbitmq.RabbitMQ(
            "RabbitMQ", metrics_collector=self.metrics_collector)

        auth_cluster = cluster.DBCluster(
            name="AuthCluster",
            master=redis.Redis(
                name="AuthRedisMaster",
                metrics_collector=self.metrics_collector),
            replicas=[
                redis.Redis(
                    name="AuthRedisReplica1",
                    metrics_collector=self.metrics_collector),
                redis.Redis(
                    name="AuthRedisReplica2",
                    metrics_collector=self.metrics_collector),
            ])

        self.auth_service = auth_service.AuthService(
            name="AuthService",
            db_cluster=auth_cluster,
            base_latency=0.05,
            metrics_collector=self.metrics_collector
        )

        notification_cluster = cluster.DBCluster(
            name="NotificationCluster",
            master=postgres.PostgresDB(
                name="NotifMaster",
                metrics_collector=self.metrics_collector),
            replicas=[
                postgres.PostgresDB(
                    name="NotifReplica1",
                    metrics_collector=self.metrics_collector)])

        self.notification_service = service.Service(
            name="NotificationService",
            db_cluster=notification_cluster,
            base_latency=0.05,
            broker=self.broker,
            metrics_collector=self.metrics_collector
        )

        self.load_balancer.add_instances(
            "NotificationService", [
                self.notification_service], [1])

        payment_instances = [
            service.Service(
                name=f"PaymentService-{i}",
                db_cluster=cluster.DBCluster(
                    name=f"PaymentCluster-{i}",
                    master=postgres.PostgresDB(
                        name=f"PaymentMaster-{i}",
                        metrics_collector=self.metrics_collector),
                    replicas=[
                        postgres.PostgresDB(
                            name=f"PaymentReplica-{i}-1",
                            metrics_collector=self.metrics_collector),
                        postgres.PostgresDB(
                            name=f"PaymentReplica-{i}-2",
                            metrics_collector=self.metrics_collector)]),
                base_latency=0.1,
                requires_auth=True,
                broker=self.broker,
                metrics_collector=self.metrics_collector) for i in range(3)]

        data_instances = [
            service.Service(
                name=f"DataService-{i}",
                db_cluster=cluster.DBCluster(
                    name=f"DataCluster-{i}",
                    master=postgres.PostgresDB(
                        name=f"DataMaster-{i}",
                        metrics_collector=self.metrics_collector),
                    replicas=[
                        postgres.PostgresDB(
                            name=f"DataReplica-{i}-1",
                            metrics_collector=self.metrics_collector)]),
                cache=redis.Redis(
                    name=f"CacheRedis-{i}",
                    metrics_collector=self.metrics_collector),
                base_latency=0.07,
                requires_auth=True,
                broker=self.broker,
                metrics_collector=self.metrics_collector) for i in range(2)]

        public_instances = [
            service.Service(
                name=f"PublicInfoService-{i}",
                db_cluster=cluster.DBCluster(
                    name=f"PublicCluster-{i}",
                    master=postgres.PostgresDB(
                        name=f"PublicMaster-{i}",
                        metrics_collector=self.metrics_collector),
                    replicas=[
                        postgres.PostgresDB(
                            name=f"PublicReplica-{i}-1",
                            metrics_collector=self.metrics_collector)]),
                base_latency=0.03,
                requires_auth=False,
                metrics_collector=self.metrics_collector) for i in range(2)]

        weights = [7, 3]
        self.load_balancer.add_instances(
            "PaymentService", payment_instances, weights)
        self.load_balancer.add_instances(
            "DataService", data_instances, weights)
        self.load_balancer.add_instances(
            "PublicInfoService", public_instances, weights)

        self.services = [self.auth_service, self.notification_service] + \
            payment_instances + data_instances + public_instances

        self.resources = []
        for s in self.services:
            if s.db_cluster:
                self.resources.append(s.db_cluster.master)
                self.resources.extend(s.db_cluster.replicas)
            if s.cache:
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
            auth_req = models.Request(
                user, "AuthService", models.HTTPMethod.POST)
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

            method = models.HTTPMethod.GET if random.random() <= 0.5 else models.HTTPMethod.POST
            req = models.Request(user, service_instance.name, method)
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
        self.metrics_collector.record_load_start(service.name)
        try:
            await service.handle(request)
            request.success = True

        except Exception as e:
            request.success = False
            logger.debug(f"❌ Ошибка при {request.service_name}: {e}")
        finally:
            request.end_time = time.time()
            self.metrics_collector.record_load_end(service.name)
            self.metrics_collector.record(request)

    async def consume_notifications(self):
        logger = context_logger.get_logger()
        while True:
            try:
                msg, delay = await self.broker.consume("messages")
                logger.info(
                    f"🔔 Уведомление: user={
                        msg['user_id']} delay={
                        delay:.3f}s, service={
                        msg["service"]}")
            except BaseException:
                pass
            await asyncio.sleep(0.05)

    async def run(self):
        """Запуск приложения"""
        logger = context_logger.get_logger()
        for r in self.resources:
            asyncio.create_task(r.simulate_failure())
        for s in self.services:
            asyncio.create_task(s.simulate_failure())
        for s in self.services:
            if hasattr(s, "db_cluster") and s.db_cluster:
                asyncio.create_task(s.db_cluster.monitor_master(interval=5.0))

        consume_task = asyncio.create_task(self.consume_notifications())
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
        consume_task.cancel()

    def visualize(self):
        """Визуализация всех метрик"""
        times, rps, errors = self.metrics_collector.get_rps_series()
        lat_stats = self.metrics_collector.get_latency_stats()
        tcp_tls = self.metrics_collector.get_tcp_tls_avg()
        broker_stats = self.metrics_collector.get_broker_stats()
        avg_load = self.metrics_collector.get_avg_load()
        infra = self.metrics_collector.infrastructure

        plt.figure(figsize=(14, 12))

        plt.subplot(4, 2, 1)
        plt.plot(times, rps, label="RPS")
        plt.plot(times, errors, label="Ошибки", color="red")
        plt.title("Запросы и ошибки во времени")
        plt.legend()

        plt.subplot(4, 2, 2)
        plt.hist(self.metrics_collector.response_times, bins=20, alpha=0.7)
        plt.title(
            f"Latency avg={lat_stats['avg']:.3f}s | "
            f"p95={lat_stats['p95']:.3f}s | p99={lat_stats['p99']:.3f}s"
        )

        plt.subplot(4, 2, 3)
        plt.bar(["TCP avg", "TLS avg"],
                [tcp_tls["tcp_avg"], tcp_tls["tls_avg"]],
                color=["blue", "orange"])
        plt.title("Среднее время TCP / TLS соединений")

        plt.subplot(4, 2, 4)
        if avg_load:
            names = list(avg_load.keys())
            loads = [avg_load[n] for n in names]
            plt.bar(names, loads, color="teal")
            plt.xticks(rotation=30, ha='right')
            plt.title("Средняя нагрузка на сервисы (запросов в секунду)")
        else:
            plt.text(
                0.5,
                0.5,
                "Нет данных по нагрузке",
                ha='center',
                va='center')

        plt.subplot(4, 2, 5)
        if infra:
            plt.bar(infra.keys(), infra.values(), color="red")
            plt.title("Инфраструктурные сбои (DB, Cache, Service, Network)")
            plt.ylabel("Количество ошибок")
        else:
            plt.text(
                0.5,
                0.5,
                "Нет инфраструктурных ошибок",
                ha='center',
                va='center')

        plt.subplot(4, 2, 6)
        if self.metrics_collector.broker_metrics["latencies"]:
            plt.hist(
                self.metrics_collector.broker_metrics["latencies"],
                bins=20,
                alpha=0.7,
                color="purple")
            plt.title(
                f"Брокер сообщений — задержки доставки "
                f"(avg={broker_stats['avg_latency']:.3f}s, "
                f"p95={broker_stats['p95_latency']:.3f}s)"
            )
            plt.xlabel("Задержка (сек)")
            plt.ylabel("Сообщений")
        else:
            plt.text(
                0.5,
                0.5,
                "Нет данных по задержкам брокера",
                ha='center',
                va='center')

        plt.subplot(4, 2, 7)
        plt.pie(
            [self.metrics_collector.successes, self.metrics_collector.errors],
            labels=["Успех", "Ошибка"],
            autopct="%1.1f%%",
            colors=["green", "red"]
        )
        plt.title("Доля успешных и неуспешных запросов")

        plt.subplot(4, 2, 8)
        summary = self.metrics_collector.get_service_summary()
        if summary:
            names = list(summary.keys())
            avgs = [summary[n]["avg_response"] for n in names]
            plt.bar(names, avgs, color="skyblue")
            plt.xticks(rotation=30, ha='right')
            plt.title("Среднее время отклика по сервисам")
            plt.ylabel("секунды")
        else:
            plt.text(
                0.5,
                0.5,
                "Нет данных по сервисам",
                ha='center',
                va='center')

        plt.tight_layout()
        plt.show()
