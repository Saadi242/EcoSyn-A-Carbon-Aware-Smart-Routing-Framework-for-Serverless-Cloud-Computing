"""EcoSyn: Carbon-Aware Smart Router for Serverless Cloud Workloads."""

from typing import Any, Dict, List, Optional

from src.carbon_tracker.base_tracker import BaseCarbonTracker
from src.router.base_router import BaseRouter, InvocationRequest, RoutingDecision


class EcoSynRouter(BaseRouter):
    """Intelligent Multi-Objective Carbon-Aware Router for Serverless Computing.

    Features a two-stage decision process:
      Stage 1 (QoS/SLA Guardrail): Prunes cloud regions whose projected total latency
                                  exceeds the request SLA deadline.
      Stage 2 (Pareto Optimization): Normalizes carbon, latency, and cost dimensions
                                     and chooses the optimal candidate minimizing the
                                     weighted objective function.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        carbon_tracker: BaseCarbonTracker,
        carbon_weight: Optional[float] = None,
        latency_weight: Optional[float] = None,
        cost_weight: Optional[float] = None,
    ):
        super().__init__(config, carbon_tracker)
        self.policy_name = "ecosyn"
        self.available_regions: List[str] = sorted(list(self.regions_config.keys()))

        # Configure weights
        defaults = config.get("routing_defaults", {}).get("weights", {})
        self.w_c = carbon_weight if carbon_weight is not None else float(defaults.get("carbon", 0.50))
        self.w_l = latency_weight if latency_weight is not None else float(defaults.get("latency", 0.35))
        self.w_p = cost_weight if cost_weight is not None else float(defaults.get("cost", 0.15))

        # Normalize weights so sum equals 1.0
        total_w = self.w_c + self.w_l + self.w_p
        if total_w > 0:
            self.w_c /= total_w
            self.w_l /= total_w
            self.w_p /= total_w
        else:
            self.w_c, self.w_l, self.w_p = 0.50, 0.35, 0.15

    def set_weights(self, carbon: float, latency: float, cost: float) -> None:
        """Dynamically adjusts the multi-objective weights at runtime."""
        total = carbon + latency + cost
        if total > 0:
            self.w_c = carbon / total
            self.w_l = latency / total
            self.w_p = cost / total

    def _normalize(self, val: float, min_val: float, max_val: float) -> float:
        """Applies min-max scaling to project values into [0.0, 1.0]."""
        if max_val - min_val <= 1e-9:
            return 0.0
        return max(0.0, min(1.0, (val - min_val) / (max_val - min_val)))

    def route(self, request: InvocationRequest) -> RoutingDecision:
        if not self.available_regions:
            raise RuntimeError("No cloud regions configured in EcoSynRouter.")

        # Stage 0: Gather raw metrics for all regions
        raw_metrics: Dict[str, Dict[str, float]] = {}
        for region in self.available_regions:
            lat = self.estimate_total_latency(request, region)
            carb = self.carbon_tracker.get_carbon_intensity(region, request.timestamp_sec)
            cst = self.estimate_invocation_cost(request, region)
            raw_metrics[region] = {
                "latency": lat,
                "carbon": carb,
                "cost": cst,
            }

        # Stage 1: QoS / SLA Guardrail Filter
        eligible_regions = [
            r for r, m in raw_metrics.items()
            if m["latency"] <= request.sla_deadline_ms
        ]

        # Safety Fallback: If SLA is too tight and no region qualifies,
        # choose the region with absolute lowest latency to minimize SLA breach severity.
        if not eligible_regions:
            fastest_region = min(raw_metrics.keys(), key=lambda r: raw_metrics[r]["latency"])
            fastest_metrics = raw_metrics[fastest_region]
            return RoutingDecision(
                request_id=request.request_id,
                selected_region=fastest_region,
                policy=self.policy_name,
                estimated_latency_ms=fastest_metrics["latency"],
                estimated_carbon_intensity=fastest_metrics["carbon"],
                estimated_cost_usd=fastest_metrics["cost"],
                sla_satisfied=False,
                candidate_scores={r: m["latency"] for r, m in raw_metrics.items()},
                decision_notes="SLA fallback: all candidate regions exceed SLA; selected fastest path.",
            )

        # Stage 2: Min-Max Normalization over eligible regions
        min_carb = min(raw_metrics[r]["carbon"] for r in eligible_regions)
        max_carb = max(raw_metrics[r]["carbon"] for r in eligible_regions)

        min_lat = min(raw_metrics[r]["latency"] for r in eligible_regions)
        max_lat = max(raw_metrics[r]["latency"] for r in eligible_regions)

        min_cost = min(raw_metrics[r]["cost"] for r in eligible_regions)
        max_cost = max(raw_metrics[r]["cost"] for r in eligible_regions)

        candidate_scores: Dict[str, float] = {}
        for r in eligible_regions:
            norm_c = self._normalize(raw_metrics[r]["carbon"], min_carb, max_carb)
            norm_l = self._normalize(raw_metrics[r]["latency"], min_lat, max_lat)
            norm_p = self._normalize(raw_metrics[r]["cost"], min_cost, max_cost)

            score = (self.w_c * norm_c) + (self.w_l * norm_l) + (self.w_p * norm_p)
            candidate_scores[r] = round(score, 4)

        # Optimal candidate minimizes the weighted score
        best_region = min(candidate_scores.keys(), key=lambda r: candidate_scores[r])
        best_metrics = raw_metrics[best_region]

        return RoutingDecision(
            request_id=request.request_id,
            selected_region=best_region,
            policy=self.policy_name,
            estimated_latency_ms=best_metrics["latency"],
            estimated_carbon_intensity=best_metrics["carbon"],
            estimated_cost_usd=best_metrics["cost"],
            sla_satisfied=True,
            candidate_scores=candidate_scores,
            decision_notes=(
                f"EcoSyn optimal choice (score: {candidate_scores[best_region]}). "
                f"Eligible regions: {len(eligible_regions)}/{len(self.available_regions)}."
            ),
        )

