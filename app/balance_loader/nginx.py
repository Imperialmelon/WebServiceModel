import random
from itertools import cycle
from app.services import service


class Nginx:
    def __init__(self):
        self.instances: dict[str, list[tuple[service.Service, int]]] = {}

    def add_instances(self,
                      service_name: str,
                      service_instances: list[service.Service],
                      weights: list[int] = None):
        """Добавление инстанса сервиса"""
        if not weights:
            weights = [1] * len(service_instances)
        self.instances[service_name] = list(
            zip(service_instances, cycle(weights)))

    def get_instance(self, service_name: str) -> service.Service:
        """Получение инстанса сервиса"""
        available = [
            (instance, weight) for instance, weight in self.instances.get(
                service_name, []) if instance.available]
        if not available:
            raise Exception(f"Все экземпляры {service_name} недоступны")

        total_weight = sum(w for _, w in available)
        r = random.uniform(0, total_weight)
        upto = 0
        for s, w in available:
            if upto + w >= r:
                return s
            upto += w
        return available[-1][0]
