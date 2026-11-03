"""Multi-region serverless cloud simulation environment."""

import random
from typing import Any, Dict, List, Optional

from src.carbon_tracker.base_tracker import BaseCarbonTracker
from src.metrics.carbon_calculator import CarbonCalculator
from src.router.base_router import InvocationRequest, RoutingDecision
from src.simulator.cloud_region import CloudRegion
from src.simulator.function_instance import ExecutionResult


class CloudEnvironment:
    """Simulates a distributed multi-region serverless cloud computing cluster."""

    def __init__(self, config: Dict[str, Any], carbon_tracker: BaseCarbonTracker):
        self.config = config
        self.carbon_tracker = carbon_tracker
        self.latency_matrix = config.get("latency_matrix_ms", {})
        self.regions_config = config.get("regions", {})

        # Instantiate CloudRegion objects
        self.regions: Dict[str, CloudRegion] = {
            r_id: CloudRegion(r_id, r_cfg)
            for r_id, r_cfg in self.regions_config.items()
        }

    def reset(self) -> None:
        """Resets all regional container pools and counters for a fresh benchmark run."""
        for r_id, r_cfg in self.regions_config.items():
            self.regions[r_id] = CloudRegion(r_id, r_cfg)

    def _simulate_network_rtt(self, client_region: str, cloud_region: str) -> float:
        """Simulates realistic network travel time with internet jitter."""
        client_latencies = self.latency_matrix.get(client_region, {})
        base_rtt = client_latencies.get(cloud_region, 150.0)
        # Add random network variance / jitter (+/- 2-5 ms)
        jitter = random.gauss(0, 2.5)
        return max(5.0, base_rtt + jitter)

    def dispatch(
        self,
        request: InvocationRequest,
        decision: RoutingDecision,
    ) -> ExecutionResult:
        """Dispatches an invocation request according to a router's decision."""
        target_region_id = decision.selected_region
        if target_region_id not in self.regions:
            raise KeyError(f"Selected region '{target_region_id}' not found in cloud environment.")

        region = self.regions[target_region_id]

        # 1. Simulate Network RTT
        network_rtt_ms = self._simulate_network_rtt(request.client_region, target_region_id)

        # 2. Simulate Cloud Execution in Target Region
        exec_info = region.execute_function(
            function_name=request.function_name,
            nominal_duration_ms=request.estimated_duration_ms,
            timestamp_sec=request.timestamp_sec,
        )

        exec_duration_ms = exec_info["execution_duration_ms"]
        cold_start_delay_ms = exec_info["cold_start_delay_ms"]
        is_cold_start = exec_info["is_cold_start"]

        # 3. Calculate Total End-to-End Latency
        total_latency_ms = network_rtt_ms + cold_start_delay_ms + exec_duration_ms
        sla_violated = total_latency_ms > request.sla_deadline_ms

        # 4. Carbon & Energy Accounting
        carbon_intensity = self.carbon_tracker.get_carbon_intensity(
            target_region_id,
            request.timestamp_sec,
        )

        total_exec_for_energy = exec_duration_ms + (cold_start_delay_ms * 0.5)
        energy_kwh = CarbonCalculator.calculate_energy_kwh(
            memory_mb=request.memory_mb,
            duration_ms=total_exec_for_energy,
            hardware_active_power_watts=region.active_power_watts,
            pue=region.pue,
        )

        carbon_emissions_g = CarbonCalculator.calculate_carbon_emissions_g(
            energy_kwh=energy_kwh,
            carbon_intensity_g_per_kwh=carbon_intensity,
        )

        # 5. Financial Cost
        cost_usd = CarbonCalculator.calculate_monetary_cost_usd(
            memory_mb=request.memory_mb,
            duration_ms=total_exec_for_energy,
            compute_cost_per_gb_sec=region.compute_cost_per_gb_sec,
            invocation_cost_per_million=region.invocation_cost_per_million,
        )

        return ExecutionResult(
            request_id=request.request_id,
            policy=decision.policy,
            client_region=request.client_region,
            selected_region=target_region_id,
            function_name=request.function_name,
            network_rtt_ms=round(network_rtt_ms, 2),
            cold_start_delay_ms=round(cold_start_delay_ms, 2),
            execution_duration_ms=round(exec_duration_ms, 2),
            total_latency_ms=round(total_latency_ms, 2),
            sla_deadline_ms=request.sla_deadline_ms,
            sla_violated=sla_violated,
            is_cold_start=is_cold_start,
            carbon_intensity=round(carbon_intensity, 2),
            energy_kwh=energy_kwh,
            carbon_emissions_g=round(carbon_emissions_g, 6),
            cost_usd=round(cost_usd, 8),
            decision_notes=decision.decision_notes,
        )

