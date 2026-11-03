"""Baseline 2: Greedy Latency-First Router."""

from typing import Any, Dict, List

from src.carbon_tracker.base_tracker import BaseCarbonTracker
from src.router.base_router import BaseRouter, InvocationRequest, RoutingDecision


class LatencyFirstRouter(BaseRouter):
    """Routes incoming serverless invocations strictly to the region with lowest network latency.

    This represents current industry standard routing (e.g. GeoDNS / Route 53 Latency-based Routing).
    While it minimizes client response time, it is completely blind to power grid carbon intensity.
    """

    def __init__(self, config: Dict[str, Any], carbon_tracker: BaseCarbonTracker):
        super().__init__(config, carbon_tracker)
        self.policy_name = "latency_first"
        self.available_regions: List[str] = sorted(list(self.regions_config.keys()))

    def route(self, request: InvocationRequest) -> RoutingDecision:
        if not self.available_regions:
            raise RuntimeError("No cloud regions configured in LatencyFirstRouter.")

        best_region = None
        min_latency = float("inf")
        candidate_latencies = {}

        for region in self.available_regions:
            lat = self.estimate_total_latency(request, region)
            candidate_latencies[region] = lat
            if lat < min_latency:
                min_latency = lat
                best_region = region

        selected_region = best_region or self.available_regions[0]
        carbon = self.carbon_tracker.get_carbon_intensity(selected_region, request.timestamp_sec)
        cost = self.estimate_invocation_cost(request, selected_region)
        sla_satisfied = min_latency <= request.sla_deadline_ms

        return RoutingDecision(
            request_id=request.request_id,
            selected_region=selected_region,
            policy=self.policy_name,
            estimated_latency_ms=min_latency,
            estimated_carbon_intensity=carbon,
            estimated_cost_usd=cost,
            sla_satisfied=sla_satisfied,
            candidate_scores=candidate_latencies,
            decision_notes="Selected region with absolute minimum latency",
        )
