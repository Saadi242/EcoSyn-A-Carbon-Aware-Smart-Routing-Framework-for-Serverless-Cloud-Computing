"""Offline Historical Trace Replay Carbon Tracker for EcoSyn."""

from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from src.carbon_tracker.base_tracker import BaseCarbonTracker


class TraceCarbonTracker(BaseCarbonTracker):
    """Replays pre-recorded or synthetic 24-hour grid carbon traces from CSV."""

    def __init__(self, trace_csv_path: str | Path, fallback_regions: Optional[Dict[str, float]] = None):
        """Initializes the TraceCarbonTracker.

        Args:
            trace_csv_path: Path to the CSV file containing hourly carbon traces.
            fallback_regions: Optional default carbon intensities if region is missing.
        """
        self.csv_path = Path(trace_csv_path)
        self.fallback_regions = fallback_regions or {}

        if not self.csv_path.exists():
            raise FileNotFoundError(f"Carbon trace file not found at: {self.csv_path}")

        self.df = pd.read_csv(self.csv_path)
        if "hour" not in self.df.columns:
            raise ValueError(f"Trace CSV must contain an 'hour' column. Found: {self.df.columns.tolist()}")

        self.df.set_index("hour", inplace=True)
        self.tracked_regions = [col for col in self.df.columns]

    def _get_hour_index(self, timestamp_sec: float) -> int:
        """Converts timestamp in seconds to a 24-hour index (0 to 23)."""
        return int((timestamp_sec / 3600.0) % 24)

    def get_carbon_intensity(self, region: str, timestamp_sec: float = 0.0) -> float:
        """Retrieves carbon intensity for a specific region at simulation timestamp."""
        hour = self._get_hour_index(timestamp_sec)
        if region in self.df.columns:
            if hour in self.df.index:
                return float(self.df.loc[hour, region])
            return float(self.df[region].iloc[0])
        elif region in self.fallback_regions:
            return float(self.fallback_regions[region])
        else:
            raise KeyError(f"Region '{region}' not found in trace data or fallbacks.")

    def get_all_regions_carbon(self, timestamp_sec: float = 0.0) -> Dict[str, float]:
        """Retrieves carbon intensity across all tracked regions at simulation timestamp."""
        hour = self._get_hour_index(timestamp_sec)
        result = {}
        for region in self.tracked_regions:
            if hour in self.df.index:
                result[region] = float(self.df.loc[hour, region])
            else:
                result[region] = float(self.df[region].iloc[0])

        for region, fallback_val in self.fallback_regions.items():
            if region not in result:
                result[region] = float(fallback_val)

        return result

    def get_tracked_regions(self) -> List[str]:
        """Returns the list of available regions."""
        all_regions = set(self.tracked_regions) | set(self.fallback_regions.keys())
        return sorted(list(all_regions))
