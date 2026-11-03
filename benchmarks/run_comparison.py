"""Automated Head-to-Head Comparative Benchmark Suite for EcoSyn.

Simulates 1,000+ serverless requests across multiple policies:
  1. Latency-First (Industry Standard Geo-DNS / Route 53)
  2. Round-Robin (Uniform Distribution Heuristic)
  3. EcoSyn (Balanced Multi-Objective: 50% Carbon, 35% Latency, 15% Cost)
  4. EcoSyn (Aggressive Green: 80% Carbon, 15% Latency, 5% Cost)
"""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from config import load_config
from src.carbon_tracker import create_carbon_tracker
from src.router import (
    InvocationRequest,
    LatencyFirstRouter,
    RoundRobinRouter,
    EcoSynRouter,
)
from src.simulator import CloudEnvironment
from src.metrics import MetricsAggregator
from src.storage import DatabaseManager


def generate_synthetic_workload(
    num_requests: int = 1000,
    sla_ms: float = 250.0,
    seed: int = 42,
) -> List[InvocationRequest]:
    """Generates a realistic, reproducible serverless invocation workload trace."""
    random.seed(seed)
    client_regions = [
        "client-europe",
        "client-north-america",
        "client-asia",
        "client-south-america",
    ]
    # Regional client traffic distribution
    client_weights = [0.35, 0.35, 0.20, 0.10]

    function_profiles = [
        {"name": "auth-service", "mem": 128, "duration": 40.0, "payload": 16.0},
        {"name": "user-profile", "mem": 256, "duration": 60.0, "payload": 32.0},
        {"name": "image-resizer", "mem": 512, "duration": 140.0, "payload": 256.0},
        {"name": "data-aggregator", "mem": 1024, "duration": 220.0, "payload": 512.0},
        {"name": "payment-process", "mem": 512, "duration": 110.0, "payload": 64.0},
        {"name": "notification-dispatcher", "mem": 128, "duration": 30.0, "payload": 8.0},
    ]

    requests: List[InvocationRequest] = []
    current_time_sec = 0.0

    for i in range(num_requests):
        # Poisson inter-arrival time with bursty traffic spikes
        inter_arrival = random.expovariate(2.5) # Average 2.5 requests per second
        current_time_sec += inter_arrival

        client = random.choices(client_regions, weights=client_weights, k=1)[0]
        fn = random.choice(function_profiles)

        # Realistic duration jitter (+/- 10%)
        duration_jitter = random.uniform(0.9, 1.1)
        duration = fn["duration"] * duration_jitter

        req = InvocationRequest(
            request_id=f"req-{i+1:05d}",
            timestamp_sec=current_time_sec,
            client_region=client,
            function_name=fn["name"],
            payload_kb=fn["payload"],
            memory_mb=fn["mem"],
            estimated_duration_ms=round(duration, 1),
            sla_deadline_ms=sla_ms,
        )
        requests.append(req)

    return requests


def run_benchmark(
    num_requests: int = 1000,
    sla_ms: float = 250.0,
    seed: int = 42,
    persist_to_db: bool = True,
) -> Dict[str, Any]:
    """Executes the full comparative benchmark across all algorithms."""
    config = load_config()
    tracker = create_carbon_tracker(config)
    db_mgr = DatabaseManager(config) if persist_to_db else None

    # Generate identical workload
    workload = generate_synthetic_workload(num_requests=num_requests, sla_ms=sla_ms, seed=seed)

    policies = [
        ("Latency-First", LatencyFirstRouter(config, tracker)),
        ("Round-Robin", RoundRobinRouter(config, tracker)),
        ("EcoSyn-Balanced", EcoSynRouter(config, tracker, carbon_weight=0.50, latency_weight=0.35, cost_weight=0.15)),
        ("EcoSyn-Green", EcoSynRouter(config, tracker, carbon_weight=0.80, latency_weight=0.15, cost_weight=0.05)),
    ]

    all_summaries: List[Dict[str, Any]] = []
    all_raw_results: List[Dict[str, Any]] = []
    baseline_carbon = 0.0

    print("=" * 90)
    print(f"        ECOSYN BENCHMARK SUITE: RUNNING {num_requests} INVOCATIONS (SLA: {sla_ms} ms)")
    print("=" * 90)

    for idx, (policy_name, router) in enumerate(policies):
        # Reset cloud environment to ensure fair warm-pool starting conditions
        env = CloudEnvironment(config, tracker)
        results = []
        db_records = []

        for req in workload:
            decision = router.route(req)
            result = env.dispatch(req, decision)
            results.append(result)

            if persist_to_db:
                db_records.append({
                    "request_id": result.request_id,
                    "router_policy": policy_name,
                    "client_region": result.client_region,
                    "selected_region": result.selected_region,
                    "function_name": result.function_name,
                    "network_rtt_ms": result.network_rtt_ms,
                    "execution_duration_ms": result.execution_duration_ms,
                    "total_latency_ms": result.total_latency_ms,
                    "sla_deadline_ms": result.sla_deadline_ms,
                    "sla_violated": result.sla_violated,
                    "carbon_intensity": result.carbon_intensity,
                    "energy_kwh": result.energy_kwh,
                    "carbon_emissions_g": result.carbon_emissions_g,
                    "cost_usd": result.cost_usd,
                    "decision_notes": result.decision_notes,
                })

            all_raw_results.append({
                "policy": policy_name,
                "request_id": result.request_id,
                "client_region": result.client_region,
                "selected_region": result.selected_region,
                "latency_ms": result.total_latency_ms,
                "sla_violated": result.sla_violated,
                "carbon_g": result.carbon_emissions_g,
                "energy_kwh": result.energy_kwh,
                "cost_usd": result.cost_usd,
            })

        # Save to DB
        if persist_to_db and db_mgr and db_records:
            db_mgr.log_batch(db_records)

        # Summarize
        if idx == 0:
            summary = MetricsAggregator.summarize_results(results)
            baseline_carbon = summary["total_carbon_g"]
        else:
            summary = MetricsAggregator.summarize_results(results, baseline_carbon=baseline_carbon)

        summary["policy_label"] = policy_name
        all_summaries.append(summary)

        print(f"\n[POLICY] {policy_name}")
        print(f"  * Total Carbon:     {summary['total_carbon_g']:.4f} g CO2eq")
        if idx > 0:
            print(f"  * Carbon Saved:     {summary['carbon_saved_pct']}% vs Latency-First")
        print(f"  * Avg Latency:      {summary['avg_latency_ms']:.1f} ms (p95: {summary['p95_latency_ms']:.1f} ms)")
        print(f"  * SLA Violations:   {summary['sla_violation_rate_pct']}% ({summary['sla_violation_count']}/{num_requests})")
        print(f"  * Cold Start Rate:  {summary['cold_start_rate_pct']}%")
        print(f"  * Traffic Shares:   {summary['region_distribution_pct']}")

    print("\n" + "=" * 90)

    # Save summary and raw outputs
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary_json_path = reports_dir / "benchmark_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)

    summary_df = pd.DataFrame(all_summaries)
    summary_csv_path = reports_dir / "benchmark_summary.csv"
    summary_df.to_csv(summary_csv_path, index=False)

    raw_df = pd.DataFrame(all_raw_results)
    raw_csv_path = reports_dir / "benchmark_raw_results.csv"
    raw_df.to_csv(raw_csv_path, index=False)

    print(f"Summary results exported to: {summary_csv_path}")
    print(f"Raw invocation results exported to: {raw_csv_path}")

    return {
        "summaries": all_summaries,
        "summary_csv": str(summary_csv_path),
        "raw_csv": str(raw_csv_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EcoSyn Head-to-Head Comparative Benchmark Suite")
    parser.add_argument("--requests", type=int, default=1000, help="Number of invocation requests (default: 1000)")
    parser.add_argument("--sla", type=float, default=250.0, help="SLA deadline in milliseconds (default: 250.0)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--no-db", action="store_true", help="Disable logging to SQLite database")

    args = parser.parse_args()
    run_benchmark(
        num_requests=args.requests,
        sla_ms=args.sla,
        seed=args.seed,
        persist_to_db=not args.no_db,
    )

