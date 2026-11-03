"""Execution results and data structures for serverless simulation."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    """Contains full end-to-end telemetry for an executed invocation."""
    request_id: str
    policy: str
    client_region: str
    selected_region: str
    function_name: str

    # Timing metrics (ms)
    network_rtt_ms: float
    cold_start_delay_ms: float
    execution_duration_ms: float
    total_latency_ms: float
    sla_deadline_ms: float
    sla_violated: bool
    is_cold_start: bool

    # Environmental & Financial metrics
    carbon_intensity: float       # gCO2eq/kWh
    energy_kwh: float             # Total energy consumed
    carbon_emissions_g: float     # Total grams of CO2 emitted
    cost_usd: float               # Monetary cost incurred

    # Explanations
    decision_notes: str = ""

