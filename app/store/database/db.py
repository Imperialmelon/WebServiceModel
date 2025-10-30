class Database:
    def __init__(
            self,
            name: str,
            latency: float,
            fail_prob: float,
            available: bool):
        self.name = name
        self.latency = latency
        self.fail_prob = fail_prob
        self.available = True

    async def get(self, *args):
        pass

    async def simulate_failure(self):
        pass
