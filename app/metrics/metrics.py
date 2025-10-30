from collections import defaultdict

import numpy as np
from app.models import models
import statistics


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
            "db_times": [],
            "cache_times": [],
            "processing_times": [],
            "network_latencies": [],
        })

    def record(self, request: models.Request):
        """Сбор метрик"""
        duration = request.end_time - request.start_time
        bucket = int(request.end_time)

        if request.success:
            self.successes += 1
            self.response_times.append(duration)
            self.time_buckets[bucket]["success"] += 1
            svc = self.by_service[request.service_name]
            svc["success"] += 1
            svc["response_times"].append(duration)
            svc["tcp_times"].append(request.tcp_time)
            svc["tls_times"].append(request.tls_time)
            svc["db_times"].append(request.db_time)
            svc["cache_times"].append(request.cache_time)
            svc["processing_times"].append(request.processing_time)
            svc["network_latencies"].append(request.network_latency)
        else:
            self.errors += 1
            self.time_buckets[bucket]["error"] += 1
            svc = self.by_service[request.service_name]
            svc["error"] += 1

    def get_rps_series(self):
        """Агрегированная статистика RPS"""
        times = sorted(self.time_buckets.keys())
        rps = [self.time_buckets[t]["success"] +
               self.time_buckets[t]["error"] for t in times]
        errors = [self.time_buckets[t]["error"] for t in times]
        return times, rps, errors

    def get_service_summary(self):
        """Агрегированная статистика по каждому сервису"""
        summary = {}
        for name, data in self.by_service.items():
            summary[name] = {
                "success": data["success"], "error": data["error"], "avg_response": statistics.mean(
                    data["response_times"]) if data["response_times"] else 0, "avg_tcp": statistics.mean(
                    data["tcp_times"]) if data["tcp_times"] else 0, "avg_tls": statistics.mean(
                    data["tls_times"]) if data["tls_times"] else 0, "avg_db": statistics.mean(
                    data["db_times"]) if data["db_times"] else 0, "avg_cache": statistics.mean(
                        data["cache_times"]) if data["cache_times"] else 0, "avg_processing": statistics.mean(
                            data["processing_times"]) if data["processing_times"] else 0, }
        return summary

    def get_latency_stats(self):
        """Возвращает среднее, p95 и p99 времени ответа"""
        if not self.response_times:
            return {"avg": 0, "p95": 0, "p99": 0}

        avg = statistics.mean(self.response_times)
        p95 = np.percentile(self.response_times, 95)
        p99 = np.percentile(self.response_times, 99)
        return {"avg": avg, "p95": p95, "p99": p99}

    def get_tcp_tls_avg(self):
        """Возвращает среднее время на TCP и TLS хендшейки"""
        all_tcp = []
        all_tls = []
        for svc in self.by_service.values():
            all_tcp.extend(svc["tcp_times"])
            all_tls.extend(svc["tls_times"])
        tcp_avg = statistics.mean(all_tcp) if all_tcp else 0
        tls_avg = statistics.mean(all_tls) if all_tls else 0
        return {"tcp_avg": tcp_avg, "tls_avg": tls_avg}
