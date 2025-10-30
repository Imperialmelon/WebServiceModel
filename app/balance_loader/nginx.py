import random
from app.services import service

class Nginx:
    def __init__(self):
        self.instances : dict[str, list[service.Service]]= {}

    def add_instances(self, service_name : str, service_instances : list[service.Service]):
        self.instances[service_name] = service_instances

    def get_instance(self, service_name : str) -> service.Service:
        available = [instance for instance in self.instances.get(service_name, []) if instance.available]
        if not available:
            raise Exception(f"Все экземпляры {service_name} недоступны")
        return random.choice(available)