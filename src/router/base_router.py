"""Base router definitions and request/decision data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.carbon_tracker.base_tracker import BaseCarbonTracker


@dataclass
class InvocationRequest:
    """Represents an incoming serverless function invocation request."""
    request_id: str
    timestamp_sec: float
    client_region: str
    function_name: str = "default-function"
    payload_kb: float = 64.0
    memory_mb: int = 256
    estimated_duration_ms: float = 100.0
    sla_deadline_ms: float = 250.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """Represents the outcome of a routing decision."""
    request_id: str
    selected_region: str
    policy: str
    estimated_latency_ms: float
    estimated_carbon_intensity: float
    estimated_cost_usd: float
    sla_satisfied: bool
    candidate_scores: Dict[str, float] = field(default_factory=dict)
    decision_notes: str = ""


class BaseRouter(ABC):
    """Abstract interface for serverless request routing algorithms."""

    def __init__(
        self,
        config: Dict[str, Any],
        carbon_tracker: BaseCarbonTracker,
    ):
        self.config = config
        self.carbon_tracker = carbon_tracker
        self.regions_config = config.get("regions", {})
        self.latency_matrix = config.get("latency_matrix_ms", {})
        self.policy_name = "base"

    def estimate_network_rtt(self, client_region: str, cloud_region: str) -> float:
        """Estimates Round-Trip Time (RTT) in milliseconds between client and cloud region."""
        client_latencies = self.latency_matrix.get(client_region, {})
        if cloud_region in client_latencies:
            return float(client_latencies[cloud_region])
        # Fallback default cross-continent network latency if unmapped
        return 150.0

    def estimate_total_latency(self, request: InvocationRequest, cloud_region: str) -> float:
        """Estimates total latency: Network RTT + Function Execution Duration."""
        rtt = self.estimate_network_rtt(request.client_region, cloud_region)
        return rtt + request.estimated_duration_ms

    def estimate_invocation_cost(self, request: InvocationRequest, cloud_region: str) -> float:
        """Estimates operational cloud cost in USD for the serverless invocation."""
        reg_info = self.regions_config.get(cloud_region, {})
        cost_per_gb_sec = float(reg_info.get("compute_cost_per_gb_sec", 0.0000166667))
        inv_cost_per_m = float(reg_info.get("invocation_cost_per_million", 0.20))

        # Memory in GB * Duration in Seconds
        gb = request.memory_mb / 1024.0
        seconds = request.estimated_duration_ms / 1000.0
        compute_cost = gb * seconds * cost_per_gb_sec
        request_cost = inv_cost_per_m / 1_000_000.0
        return compute_cost + request_cost

    @abstractmethod
    def route(self, request: InvocationRequest) -> RoutingDecision:
        """Makes an intelligent routing decision for the incoming invocation request."""
        pass
