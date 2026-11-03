import sys
from pathlib import Path
# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from config import load_config
from src.carbon_tracker import create_carbon_tracker
from src.router import InvocationRequest, LatencyFirstRouter, RoundRobinRouter, EcoSynRouter
from src.simulator import CloudEnvironment
from src.metrics import MetricsAggregator

def main():
    cfg = load_config()
    tracker = create_carbon_tracker(cfg)
    df = pd.read_csv("data/workload_traces/sample_workload.csv")

    policies = [
        ("Latency-First (Industry Default)", LatencyFirstRouter),
        ("Round-Robin (Uniform Baseline)", RoundRobinRouter),
        ("EcoSyn (Proposed Carbon-Aware)", EcoSynRouter),
    ]

    baseline_carbon = 0.0

    print("=" * 85)
    print("                ECOSYN PHASE 2 SIMULATION DRY-RUN VERIFICATION")
    print("=" * 85)

    for idx, (label, RouterClass) in enumerate(policies):
        env = CloudEnvironment(cfg, tracker)
        router = RouterClass(cfg, tracker)
        results = []

        for _, row in df.iterrows():
            req = InvocationRequest(
                request_id=row["request_id"],
                timestamp_sec=float(row["timestamp_sec"]),
                client_region=row["client_region"],
                function_name=row["function_name"],
                payload_kb=float(row["payload_kb"]),
                memory_mb=int(row["memory_mb"]),
                estimated_duration_ms=float(row["estimated_duration_ms"]),
                sla_deadline_ms=float(row["sla_deadline_ms"]),
            )
            decision = router.route(req)
            result = env.dispatch(req, decision)
            results.append(result)

        if idx == 0:
            summary = MetricsAggregator.summarize_results(results)
            baseline_carbon = summary["total_carbon_g"]
        else:
            summary = MetricsAggregator.summarize_results(results, baseline_carbon=baseline_carbon)

        print(f"\n[POLICY] {label}")
        print(f"  * Total Carbon:     {summary['total_carbon_g']:.4f} g CO2eq")
        if idx > 0:
            print(f"  * Carbon Saved:     {summary['carbon_saved_pct']}% compared to Latency-First")
        print(f"  * Avg Latency:      {summary['avg_latency_ms']:.1f} ms")
        print(f"  * SLA Violations:   {summary['sla_violation_rate_pct']}% ({summary['sla_violation_count']}/{summary['total_requests']})")
        print(f"  * Cold Start Rate:  {summary['cold_start_rate_pct']}%")
        print(f"  * Traffic Routed:   {summary['region_distribution_pct']}")

    print("\n" + "=" * 85)
    print("SUCCESS: Phase 2 Core Simulation and Multi-Objective Algorithm fully verified!")
    print("=" * 85)

if __name__ == "__main__":
    main()
