"""SQLAlchemy Database Models for EcoSyn telemetry and benchmarking."""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class InvocationLog(Base):
    """Stores detailed telemetry for each routed serverless function invocation."""
    __tablename__ = "invocation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    router_policy = Column(String(32), index=True, nullable=False)
    client_region = Column(String(32), nullable=False)
    selected_region = Column(String(32), nullable=False)
    function_name = Column(String(64), default="default-function")

    # Latency metrics (ms)
    network_rtt_ms = Column(Float, nullable=False)
    execution_duration_ms = Column(Float, nullable=False)
    total_latency_ms = Column(Float, nullable=False)
    sla_deadline_ms = Column(Float, nullable=False)
    sla_violated = Column(Boolean, default=False, nullable=False)

    # Carbon & energy metrics
    carbon_intensity = Column(Float, nullable=False) # gCO2eq/kWh
    energy_kwh = Column(Float, nullable=False)
    carbon_emissions_g = Column(Float, nullable=False) # Total grams of CO2

    # Financial cost (USD)
    cost_usd = Column(Float, nullable=False)

    # Additional notes / metadata
    decision_notes = Column(Text, default="")


class BenchmarkRun(Base):
    """Stores aggregated summary metrics for benchmark evaluation runs."""
    __tablename__ = "benchmark_runs"

    run_id = Column(String(64), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    policy_name = Column(String(32), nullable=False)
    total_requests = Column(Integer, nullable=False)
    avg_latency_ms = Column(Float, nullable=False)
    p95_latency_ms = Column(Float, nullable=False)
    sla_violation_rate_pct = Column(Float, nullable=False)
    total_carbon_g = Column(Float, nullable=False)
    carbon_saved_pct = Column(Float, default=0.0)
    total_cost_usd = Column(Float, nullable=False)
