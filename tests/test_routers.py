"""Unit tests for the Routing Algorithms (Round-Robin, Latency-First, and EcoSyn)."""

import pytest
from config import load_config
from src.carbon_tracker import create_carbon_tracker
from src.router import (
    InvocationRequest,
    RoundRobinRouter,
    LatencyFirstRouter,
    EcoSynRouter,
)


@pytest.fixture
def config():
    return load_config()


@pytest.fixture
def tracker(config):
    return create_carbon_tracker(config)


def test_round_robin_cycling(config, tracker):
    router = RoundRobinRouter(config, tracker)
    regions_count = len(router.available_regions)
    req = InvocationRequest(
        request_id="test-rr",
        timestamp_sec=0.0,
        client_region="client-europe",
        estimated_duration_ms=50.0,
        sla_deadline_ms=300.0,
    )

    selected = []
    for _ in range(regions_count * 2):
        dec = router.route(req)
        selected.append(dec.selected_region)

    # Verify cyclic repetition
    assert selected[:regions_count] == selected[regions_count:]


def test_latency_first_routing(config, tracker):
    router = LatencyFirstRouter(config, tracker)

    # European client should be routed to closest data center (eu-north-1)
    req_eu = InvocationRequest(
        request_id="test-lat-eu",
        timestamp_sec=0.0,
        client_region="client-europe",
        estimated_duration_ms=50.0,
        sla_deadline_ms=300.0,
    )
    dec_eu = router.route(req_eu)
    assert dec_eu.selected_region == "eu-north-1"

    # North American client should be routed to us-east-1 (lowest RTT in matrix)
    req_us = InvocationRequest(
        request_id="test-lat-us",
        timestamp_sec=0.0,
        client_region="client-north-america",
        estimated_duration_ms=50.0,
        sla_deadline_ms=300.0,
    )
    dec_us = router.route(req_us)
    assert dec_us.selected_region == "us-east-1"


def test_ecosyn_carbon_awareness(config, tracker):
    # Set heavy carbon priority
    router = EcoSynRouter(config, tracker, carbon_weight=0.85, latency_weight=0.10, cost_weight=0.05)

    # A North American client with a generous SLA (e.g. 350ms)
    # Even though us-east-1 is physically closest, EcoSyn should reroute to a much cleaner
    # region (e.g. eu-north-1 or us-west-2) without violating the 350ms SLA.
    req = InvocationRequest(
        request_id="test-eco-1",
        timestamp_sec=0.0,
        client_region="client-north-america",
        estimated_duration_ms=50.0,
        sla_deadline_ms=350.0,
    )

    dec = router.route(req)
    # us-east-1 has ~385 gCO2, while us-west-2 has ~110 gCO2 and eu-north-1 has ~25 gCO2.
    # EcoSyn should NOT pick us-east-1 when carbon weight is 85% and SLA is generous.
    assert dec.selected_region in ["eu-north-1", "us-west-2"]
    assert dec.sla_satisfied is True


def test_ecosyn_sla_guardrail_enforcement(config, tracker):
    # Even with high carbon weight, if SLA is very tight (e.g. 90ms),
    # EcoSyn MUST NOT route cross-Atlantic to Stockholm (RTT is ~110ms + 50ms = 160ms).
    # It must respect the SLA guardrail.
    router = EcoSynRouter(config, tracker, carbon_weight=0.85, latency_weight=0.10, cost_weight=0.05)

    req_tight = InvocationRequest(
        request_id="test-eco-tight",
        timestamp_sec=0.0,
        client_region="client-north-america",
        estimated_duration_ms=40.0,
        sla_deadline_ms=80.0, # Tight deadline: 25ms RTT + 40ms = 65ms (only us-east-1 qualifies)
    )

    dec_tight = router.route(req_tight)
    assert dec_tight.selected_region == "us-east-1"
    assert dec_tight.sla_satisfied is True

