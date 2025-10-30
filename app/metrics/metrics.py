from collections import defaultdict
import numpy as np
from app.models import models


class MetricsCollector:
    def __init__(self):
        self.response_times = []
        self.errors = 0
        self.successes = 0
        self.time_buckets = defaultdict(lambda: {"success": 0, "error": 0})
        self.by_service = defaultdict(lambda: {
            "success": 0,
            "error": 0,
            "response_times": [],
            "tcp_times": [],
            "tls_times": [],
        })
        self.by_instance = defaultdict(int)
        self.availability = defaultdict(lambda: {"up": 0, "down": 0})

    def record(self, request: models.Request):
        bucket = int(request.end_time)

        if request.success:
            self.successes += 1
            self.response_times.append(request.duration)
            self.time_buckets[bucket]["success"] += 1
            self.by_service[request.service_name]["success"] += 1
            self.by_service[request.service_name]["response_times"].append(
                request.duration)
        else:
            self.errors += 1
            self.time_buckets[bucket]["error"] += 1
            self.by_service[request.service_name]["error"] += 1

        self.by_instance[request.service_name] += 1

        if hasattr(request, "tcp_time"):
            self.by_service[request.service_name]["tcp_times"].append(
                request.tcp_time)
        if hasattr(request, "tls_time"):
            self.by_service[request.service_name]["tls_times"].append(
                request.tls_time)

    def record_availability(self, service_name: str, is_up: bool):
        if is_up:
            self.availability[service_name]["up"] += 1
        else:
            self.availability[service_name]["down"] += 1

    def get_rps_series(self):
        times = sorted(self.time_buckets.keys())
        rps = [self.time_buckets[t]["success"] +
               self.time_buckets[t]["error"] for t in times]
        errors = [self.time_buckets[t]["error"] for t in times]
        return times, rps, errors

    def get_error_rate(self):
        total = self.errors + self.successes
        return self.errors / total if total else 0

    def get_latency_stats(self):
        if not self.response_times:
            return {"avg": 0, "p95": 0, "p99": 0}
        arr = np.array(self.response_times)
        return {
            "avg": float(np.mean(arr)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
        }

    def get_service_latency(self, service_name):
        times = self.by_service[service_name]["response_times"]
        if not times:
            return 0
        return sum(times) / len(times)

    def get_tcp_tls_avg(self):
        tcp, tls = [], []
        for s in self.by_service.values():
            tcp += s["tcp_times"]
            tls += s["tls_times"]
        return {
            "tcp_avg": sum(tcp) / len(tcp) if tcp else 0,
            "tls_avg": sum(tls) / len(tls) if tls else 0,
        }

    def get_availability_percent(self, service_name):
        stat = self.availability[service_name]
        total = stat["up"] + stat["down"]
        if not total:
            return 100.0
        return stat["up"] / total * 100.0
