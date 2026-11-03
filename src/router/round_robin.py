"""Baseline 1: Standard Round-Robin Router."""

from typing import Any, Dict, List

from src.carbon_tracker.base_tracker import BaseCarbonTracker
from src.router.base_router import BaseRouter, InvocationRequest, RoutingDecision


class RoundRobinRouter(BaseRouter):
    """Distributes incoming serverless requests uniformly across regions using modulo indexing.

    This represents the conventional load-balancing heuristic that is agnostic to both
    network latency and power grid carbon emissions.
    """

    def __init__(self, config: Dict[str, Any], carbon_tracker: BaseCarbonTracker):
        super().__init__(config, carbon_tracker)
        self.policy_name = "round_robin"
        self.available_regions: List[str] = sorted(list(self.regions_config.keys()))
        self._index = 0

    def route(self, request: InvocationRequest) -> RoutingDecision:
        if not self.available_regions:
            raise RuntimeError("No cloud regions configured in RoundRobinRouter.")

        # Modulo selection
        selected_region = self.available_regions[self._index % len(self.available_regions)]
        self._index += 1

        latency = self.estimate_total_latency(request, selected_region)
        carbon = self.carbon_tracker.get_carbon_intensity(selected_region, request.timestamp_sec)
        cost = self.estimate_invocation_cost(request, selected_region)
        sla_satisfied = latency <= request.sla_deadline_ms

        return RoutingDecision(
            request_id=request.request_id,
            selected_region=selected_region,
            policy=self.policy_name,
            estimated_latency_ms=latency,
            estimated_carbon_intensity=carbon,
            estimated_cost_usd=cost,
            sla_satisfied=sla_satisfied,
            decision_notes=f"Round-robin turn {self._index - 1}",
        )
