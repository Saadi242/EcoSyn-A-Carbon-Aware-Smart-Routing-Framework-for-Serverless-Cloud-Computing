"""Data center cloud region simulation model."""

import random
from typing import Any, Dict, List, Optional


class CloudRegion:
    """Models a physical/logical cloud data center region executing serverless functions."""

    def __init__(self, region_id: str, config: Dict[str, Any]):
        self.region_id = region_id
        self.name = config.get("name", region_id)
        self.country = config.get("country", "Unknown")
        self.pue = float(config.get("pue", 1.15))
        self.base_carbon = float(config.get("base_carbon_intensity", 300.0))
        self.active_power_watts = float(config.get("hardware_active_power_watts", 16.0))
        self.compute_cost_per_gb_sec = float(config.get("compute_cost_per_gb_sec", 0.0000166667))
        self.invocation_cost_per_million = float(config.get("invocation_cost_per_million", 0.20))

        # Serverless Container Warm Pool: dict mapping function_name -> list of last_used_timestamps
        self.warm_pool: Dict[str, List[float]] = {}
        self.container_keep_alive_sec = 600.0 # 10 minutes warm idle window

        # Statistics
        self.total_invocations = 0
        self.total_cold_starts = 0

    def execute_function(
        self,
        function_name: str,
        nominal_duration_ms: float,
        timestamp_sec: float,
        concurrency_limit: int = 100,
    ) -> Dict[str, Any]:
        """Simulates container selection, cold/warm start latency, and execution duration.

        Returns:
            Dict containing execution duration, cold start delay, and cold start flag.
        """
        self.total_invocations += 1

        # Clean expired warm instances
        if function_name in self.warm_pool:
            self.warm_pool[function_name] = [
                t for t in self.warm_pool[function_name]
                if (timestamp_sec - t) <= self.container_keep_alive_sec
            ]
        else:
            self.warm_pool[function_name] = []

        is_cold_start = False
        cold_start_delay_ms = 0.0

        if self.warm_pool[function_name]:
            # Reuse warm container
            self.warm_pool[function_name].pop()
            is_cold_start = False
        else:
            # Cold start initialization delay (120ms to 240ms)
            is_cold_start = True
            self.total_cold_starts += 1
            cold_start_delay_ms = random.uniform(120.0, 240.0)

        # Execution duration with realistic +/- 5% variance
        duration_jitter = random.gauss(0, nominal_duration_ms * 0.05)
        actual_exec_ms = max(10.0, nominal_duration_ms + duration_jitter)

        # Record container completion for future warm reuse
        completion_time = timestamp_sec + ((actual_exec_ms + cold_start_delay_ms) / 1000.0)
        self.warm_pool[function_name].append(completion_time)

        return {
            "execution_duration_ms": actual_exec_ms,
            "cold_start_delay_ms": cold_start_delay_ms,
            "is_cold_start": is_cold_start,
        }

