import asyncio
import random
import time
from app.models import models
from app.metrics import metrics


class RabbitMQ:
    """Имитация брокера сообщений с метриками."""

    def __init__(
            self,
            name: str,
            metrics_collector: metrics.MetricsCollector,
            base_latency=0.02):
        self.name = name
        self.metrics = metrics_collector
        self.queues = {}
        self.base_latency = base_latency

    async def publish(self, msg: models.Message):
        start = time.time()
        await asyncio.sleep(random.uniform(self.base_latency, self.base_latency * 2))

        if random.random() < 0.02:
            self.metrics.record_broker_event(success=False)
            raise Exception(f"Broker publish error to {msg.topic}")

        if msg.topic not in self.queues:
            self.queues[msg.topic] = asyncio.Queue()

        msg.payload["timestamp"] = time.time()
        await self.queues[msg.topic].put(msg.payload)

        end = time.time()
        latency = end - start
        self.metrics.record_broker_event(success=True, latency=latency)
        # self.metrics.record_broker_queue_size(msg.topic, self.queues[msg.topic].qsize())

    async def consume(self, topic: str):
        """Получение сообщения из очереди с измерением задержки доставки."""
        if topic not in self.queues:
            return None, 0

        try:
            msg = await asyncio.wait_for(self.queues[topic].get(), timeout=1)

            self.queues[topic].task_done()
            # self.metrics.record_broker_queue_size(topic, self.queues[topic].qsize())

            delay = time.time() - msg["timestamp"]
            # self.metrics.record_broker_event(success=True, latency=delay)

            return msg, delay
        except asyncio.TimeoutError:
            return None, 0
