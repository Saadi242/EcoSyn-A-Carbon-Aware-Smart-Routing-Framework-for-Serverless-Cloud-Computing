"""Carbon tracker module initialization and factory."""

from pathlib import Path
from typing import Any, Dict

from src.carbon_tracker.base_tracker import BaseCarbonTracker
from src.carbon_tracker.trace_tracker import TraceCarbonTracker
from src.carbon_tracker.api_tracker import ApiCarbonTracker


def create_carbon_tracker(config: Dict[str, Any]) -> BaseCarbonTracker:
    """Factory function to instantiate the configured carbon tracker."""
    tracker_cfg = config.get("carbon_tracker", {})
    mode = tracker_cfg.get("mode", "trace")
    trace_path = tracker_cfg.get("trace_file", "data/carbon_traces/sample_carbon_traces.csv")

    # Extract default regional fallback values from config
    regions_cfg = config.get("regions", {})
    fallback_regions = {r: float(data.get("base_carbon_intensity", 300.0)) for r, data in regions_cfg.items()}

    # Initialize Trace Tracker
    trace_tracker = TraceCarbonTracker(trace_csv_path=trace_path, fallback_regions=fallback_regions)

    if mode == "trace":
        return trace_tracker

    elif mode in ["api", "hybrid"]:
        api_cfg = tracker_cfg.get("api", {})
        api_key = api_cfg.get("api_key", "")
        ttl = api_cfg.get("cache_ttl_seconds", 300)
        return ApiCarbonTracker(
            api_key=api_key,
            cache_ttl_sec=ttl,
            fallback_tracker=trace_tracker,
            default_regions=fallback_regions,
        )

    else:
        return trace_tracker


__all__ = [
    "BaseCarbonTracker",
    "TraceCarbonTracker",
    "ApiCarbonTracker",
    "create_carbon_tracker",
]
