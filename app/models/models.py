import time


class User:
    def __init__(self, user_id: int):
        self.id = user_id
        self.authorized = False


class Request:
    def __init__(self, user: User, service_name: str):
        self.user: User = user
        self.service_name: str = service_name
        self.start_time: float = time.time()
        self.end_time: float | None = None
        self.success: bool | None = None

        self.tcp_time: float = 0.0
        self.tls_time: float = 0.0

        self.db_time: float = 0.0
        self.cache_time: float = 0.0
        self.processing_time: float = 0.0
        self.network_latency: float = 0.0

    @property
    def duration(self) -> float:
        """Общее время обработки запроса"""
        return (self.end_time or time.time()) - self.start_time


class Message:
    def __init__(self, topic: str, payload: dict):
        self.topic = topic
        self.payload = payload
        self.timestamp = time.time()
