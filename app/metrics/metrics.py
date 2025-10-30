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

        self.broker_metrics = {
            "messages_sent": 0,
            "messages_failed": 0,
            "latencies": [],
            "queue_sizes": []
        }

        self.infrastructure = {
            "db_failures": 0,
            "cache_failures": 0,
            "service_failures": 0,
        }

        self.load_stats = defaultdict(lambda: {"active": 0, "total": 0})

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

    def record_load_start(self, service_name: str):
        self.load_stats[service_name]["active"] += 1
        self.load_stats[service_name]["total"] += 1

    def record_load_end(self, service_name: str):
        self.load_stats[service_name]["active"] = max(
            0, self.load_stats[service_name]["active"] - 1)

    def get_avg_load(self):
        r = {s: data["total"] / max(1, len(self.time_buckets))
             for s, data in self.load_stats.items()}
        return {
            s: data["total"] / max(1, len(self.time_buckets))
            for s, data in self.load_stats.items()
        }

    def record_broker_event(self, success: bool, latency: float = 0):
        if success:
            self.broker_metrics["messages_sent"] += 1
            self.broker_metrics["latencies"].append(latency)
        else:
            self.broker_metrics["messages_failed"] += 1

    def record_broker_queue_size(self, topic: str, size: int):
        self.broker_metrics["queue_sizes"][topic] = size

    def get_broker_stats(self):
        lat = self.broker_metrics["latencies"]
        avg = statistics.mean(lat) if lat else 0
        p95 = np.percentile(lat, 95) if lat else 0
        return {
            "avg_latency": avg,
            "p95_latency": p95,
            "messages_sent": self.broker_metrics["messages_sent"],
            "messages_failed": self.broker_metrics["messages_failed"],
            "avg_queue_size": statistics.mean(
                self.broker_metrics["queue_sizes"].values()) if self.broker_metrics["queue_sizes"] else 0}
