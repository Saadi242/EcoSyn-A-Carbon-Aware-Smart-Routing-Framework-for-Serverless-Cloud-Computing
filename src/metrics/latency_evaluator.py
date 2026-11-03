"""Latency and SLA compliance evaluation utilities."""

from typing import List, Dict, Any
import numpy as np


class LatencyEvaluator:
    """Evaluates latency distributions and SLA compliance metrics."""

    @staticmethod
    def evaluate(latencies_ms: List[float], sla_deadline_ms: float = 250.0) -> Dict[str, float]:
        """Computes statistical summary of latency and SLA breach percentages."""
        if not latencies_ms:
            return {
                "mean_ms": 0.0,
                "median_ms": 0.0,
                "p90_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "sla_violation_rate_pct": 0.0,
            }

        arr = np.array(latencies_ms)
        violations = np.sum(arr > sla_deadline_ms)
        violation_rate = (violations / len(arr)) * 100.0

        return {
            "mean_ms": round(float(np.mean(arr)), 2),
            "median_ms": round(float(np.median(arr)), 2),
            "p90_ms": round(float(np.percentile(arr, 90)), 2),
            "p95_ms": round(float(np.percentile(arr, 95)), 2),
            "p99_ms": round(float(np.percentile(arr, 99)), 2),
            "min_ms": round(float(np.min(arr)), 2),
            "max_ms": round(float(np.max(arr)), 2),
            "sla_violation_rate_pct": round(float(violation_rate), 2),
        }

