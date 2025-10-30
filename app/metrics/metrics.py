from collections import defaultdict
from app.models import models


class MetricsCollector:
    def __init__(self):
        self.response_times = []
        self.errors = 0
        self.successes = 0
        self.time_buckets = defaultdict(lambda: {"success": 0, "error": 0})
        self.by_service = defaultdict(lambda: {
            "success": 0, "error": 0, "response_times": []
        })

    def record(self, request: models.Request):
        duration = request.end_time - request.start_time
        bucket = int(request.end_time)
        if request.success:
            self.successes += 1
            self.response_times.append(duration)
            self.time_buckets[bucket]["success"] += 1
            self.by_service[request.service_name]["success"] += 1
            self.by_service[request.service_name]["response_times"].append(duration)
        else:
            self.errors += 1
            self.time_buckets[bucket]["error"] += 1
            self.by_service[request.service_name]["error"] += 1

    def get_rps_series(self):
        times = sorted(self.time_buckets.keys())
        rps = [self.time_buckets[t]["success"] + self.time_buckets[t]["error"] for t in times]
        errors = [self.time_buckets[t]["error"] for t in times]
        return times, rps, errors