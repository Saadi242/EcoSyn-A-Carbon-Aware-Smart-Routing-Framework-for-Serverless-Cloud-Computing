"""Live API Carbon Tracker with in-memory caching and fallback support."""

import time
from typing import Dict, List, Optional
import requests

from src.carbon_tracker.base_tracker import BaseCarbonTracker
from src.carbon_tracker.trace_tracker import TraceCarbonTracker


class ApiCarbonTracker(BaseCarbonTracker):
    """Fetches real-time carbon intensity from live grid APIs (e.g. Electricity Maps).

    Features caching to adhere to API rate limits and automatic fallback to trace
    data or static profiles if network issues occur.
    """

    # Mapping AWS/Cloud region IDs to Electricity Maps zone identifiers
    REGION_ZONE_MAP = {
        "eu-north-1": "SE",       # Sweden
        "us-east-1": "US-MIDW-PJM", # Virginia (PJM grid)
        "us-west-2": "US-NW-PACW", # Oregon
        "ap-south-1": "IN-WE",    # Western India
        "sa-east-1": "BR-CS",     # Brazil Central-South
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_ttl_sec: int = 300,
        fallback_tracker: Optional[BaseCarbonTracker] = None,
        default_regions: Optional[Dict[str, float]] = None,
    ):
        self.api_key = api_key
        self.cache_ttl = cache_ttl_sec
        self.fallback_tracker = fallback_tracker
        self.default_regions = default_regions or {
            "eu-north-1": 28.0,
            "us-east-1": 385.0,
            "ap-south-1": 640.0,
            "sa-east-1": 125.0,
            "us-west-2": 110.0,
        }
        self._cache: Dict[str, float] = {}
        self._last_fetch_time: Dict[str, float] = {}

    def _fetch_from_api(self, region: str) -> Optional[float]:
        """Queries the external API for live grid carbon intensity."""
        if not self.api_key:
            return None

        zone = self.REGION_ZONE_MAP.get(region)
        if not zone:
            return None

        url = f"https://api.electricitymap.org/v3/carbon-intensity/latest?zone={zone}"
        headers = {"auth-token": self.api_key}

        try:
            response = requests.get(url, headers=headers, timeout=4.0)
            if response.status_code == 200:
                data = response.json()
                carbon = data.get("carbonIntensity")
                if carbon is not None:
                    return float(carbon)
        except Exception:
            # Fallback on any network error or timeout
            pass

        return None

    def get_carbon_intensity(self, region: str, timestamp_sec: float = 0.0) -> float:
        now = time.time()
        # Check cache validity
        if region in self._cache and (now - self._last_fetch_time.get(region, 0) < self.cache_ttl):
            return self._cache[region]

        # Attempt live API
        live_val = self._fetch_from_api(region)
        if live_val is not None:
            self._cache[region] = live_val
            self._last_fetch_time[region] = now
            return live_val

        # Fallback to trace tracker if available
        if self.fallback_tracker:
            return self.fallback_tracker.get_carbon_intensity(region, timestamp_sec)

        # Fallback to static profile
        return self.default_regions.get(region, 350.0)

    def get_all_regions_carbon(self, timestamp_sec: float = 0.0) -> Dict[str, float]:
        result = {}
        for region in self.get_tracked_regions():
            result[region] = self.get_carbon_intensity(region, timestamp_sec)
        return result

    def get_tracked_regions(self) -> List[str]:
        if self.fallback_tracker:
            return self.fallback_tracker.get_tracked_regions()
        return sorted(list(self.default_regions.keys()))
