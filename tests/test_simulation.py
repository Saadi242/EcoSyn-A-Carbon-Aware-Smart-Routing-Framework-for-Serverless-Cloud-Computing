"""Unit tests for the Serverless Cloud Simulation Environment."""

import pytest
from config import load_config
from src.carbon_tracker import create_carbon_tracker
from src.router import InvocationRequest, EcoSynRouter
from src.simulator import CloudEnvironment
from src.metrics import CarbonCalculator, MetricsAggregator


@pytest.fixture
def config():
    return load_config()


@pytest.fixture
def tracker(config):
    return create_carbon_tracker(config)


def test_simulation_dispatch(config, tracker):
    env = CloudEnvironment(config, tracker)
    router = EcoSynRouter(config, tracker)

    req = InvocationRequest(
        request_id="sim-req-1",
        timestamp_sec=10.0,
        client_region="client-europe",
        estimated_duration_ms=60.0,
        sla_deadline_ms=250.0,
    )

    decision = router.route(req)
    result = env.dispatch(req, decision)

    assert result.request_id == "sim-req-1"
    assert result.total_latency_ms > 0.0
    assert result.carbon_emissions_g > 0.0
    assert result.cost_usd > 0.0
    assert isinstance(result.is_cold_start, bool)


def test_metrics_aggregation(config, tracker):
    env = CloudEnvironment(config, tracker)
    router = EcoSynRouter(config, tracker)

    results = []
    for i in range(10):
        req = InvocationRequest(
            request_id=f"sim-batch-{i}",
            timestamp_sec=float(i * 10),
            client_region="client-europe",
            estimated_duration_ms=50.0,
            sla_deadline_ms=250.0,
        )
        dec = router.route(req)
        res = env.dispatch(req, dec)
        results.append(res)

    summary = MetricsAggregator.summarize_results(results, baseline_carbon=0.05)
    assert summary["total_requests"] == 10
    assert summary["total_carbon_g"] > 0.0
    assert summary["avg_latency_ms"] > 0.0
    assert "region_distribution_pct" in summary

