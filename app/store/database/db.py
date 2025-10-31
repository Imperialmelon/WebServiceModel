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

    async def simulate_failure(self):
        pass
