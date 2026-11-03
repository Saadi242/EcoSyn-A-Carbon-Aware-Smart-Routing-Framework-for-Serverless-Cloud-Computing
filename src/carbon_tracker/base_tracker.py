"""Abstract Base Class for Carbon Intensity Trackers in EcoSyn."""

from abc import ABC, abstractmethod
from typing import Dict, List


class BaseCarbonTracker(ABC):
    """Abstract interface for querying cloud data center carbon intensities (gCO2eq / kWh)."""

    @abstractmethod
    def get_carbon_intensity(self, region: str, timestamp_sec: float = 0.0) -> float:
        """Retrieves the carbon intensity for a specific cloud region.

        Args:
            region: Cloud region identifier (e.g. 'eu-north-1', 'us-east-1').
            timestamp_sec: Simulation time elapsed in seconds.

        Returns:
            float: Grid carbon intensity in gCO2eq/kWh.
        """
        pass

    @abstractmethod
    def get_all_regions_carbon(self, timestamp_sec: float = 0.0) -> Dict[str, float]:
        """Retrieves carbon intensity for all tracked cloud regions at the given timestamp.

        Args:
            timestamp_sec: Simulation time elapsed in seconds.

        Returns:
            Dict[str, float]: Mapping of region ID to carbon intensity.
        """
        pass

    @abstractmethod
    def get_tracked_regions(self) -> List[str]:
        """Returns the list of cloud regions supported by this tracker."""
        pass
