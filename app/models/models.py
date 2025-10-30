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
        self.end_time = None
        self.success = None
        self.tcp_time: float = 0.0
        self.tls_time: float = 0.0

    @property
    def duration(self) -> float:
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time
