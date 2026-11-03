"""Metrics aggregator for comparative evaluation of routing policies."""

from collections import Counter
from typing import Dict, List, Any
import numpy as np

from src.simulator.function_instance import ExecutionResult
from src.metrics.latency_evaluator import LatencyEvaluator


class MetricsAggregator:
    """Aggregates and compares performance telemetry across multiple routing policies."""

    @staticmethod
    def summarize_results(results: List[ExecutionResult], baseline_carbon: float = 0.0) -> Dict[str, Any]:
        """Summarizes a batch of execution results for a specific policy."""
        if not results:
            return {}

        policy_name = results[0].policy
        total_requests = len(results)

        latencies = [r.total_latency_ms for r in results]
        lat_stats = LatencyEvaluator.evaluate(
            latencies,
            sla_deadline_ms=results[0].sla_deadline_ms,
        )

        total_carbon_g = sum(r.carbon_emissions_g for r in results)
        total_energy_kwh = sum(r.energy_kwh for r in results)
        total_cost_usd = sum(r.cost_usd for r in results)
        cold_starts = sum(1 for r in results if r.is_cold_start)
        sla_violations = sum(1 for r in results if r.sla_violated)

        # Regional distribution
        region_counts = Counter(r.selected_region for r in results)
        region_distribution_pct = {
            r: round((cnt / total_requests) * 100.0, 1)
            for r, cnt in region_counts.items()
        }

        # Carbon reduction compared to baseline
        carbon_saved_pct = 0.0
        if baseline_carbon > 1e-9:
            carbon_saved_pct = round(((baseline_carbon - total_carbon_g) / baseline_carbon) * 100.0, 2)

        return {
            "policy": policy_name,
            "total_requests": total_requests,
            "total_carbon_g": round(total_carbon_g, 4),
            "carbon_saved_pct": carbon_saved_pct,
            "total_energy_kwh": round(total_energy_kwh, 6),
            "total_cost_usd": round(total_cost_usd, 6),
            "avg_latency_ms": lat_stats["mean_ms"],
            "median_latency_ms": lat_stats["median_ms"],
            "p95_latency_ms": lat_stats["p95_ms"],
            "sla_violation_count": sla_violations,
            "sla_violation_rate_pct": round((sla_violations / total_requests) * 100.0, 2),
            "cold_start_count": cold_starts,
            "cold_start_rate_pct": round((cold_starts / total_requests) * 100.0, 2),
            "region_distribution_pct": region_distribution_pct,
        }

