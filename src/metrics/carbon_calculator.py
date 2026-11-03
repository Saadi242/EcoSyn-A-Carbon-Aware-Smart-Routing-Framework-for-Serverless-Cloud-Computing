"""Energy consumption and carbon emissions calculator for cloud workloads."""

from typing import Dict, Any


class CarbonCalculator:
    """Calculates active hardware energy, facility overhead (PUE), and carbon footprint."""

    @staticmethod
    def calculate_energy_kwh(
        memory_mb: int,
        duration_ms: float,
        hardware_active_power_watts: float = 16.0,
        pue: float = 1.15,
    ) -> float:
        """Calculates total data center energy in kWh consumed by a function invocation.

        Formula:
          E_active = (P_active * (duration_sec / 3600)) / 1000
          E_total  = E_active * PUE

        Args:
            memory_mb: Allocated function memory (MB).
            duration_ms: Total execution duration in milliseconds.
            hardware_active_power_watts: Active hardware power draw in Watts.
            pue: Power Usage Effectiveness of data center facility.

        Returns:
            float: Energy consumed in kWh.
        """
        duration_sec = duration_ms / 1000.0
        duration_hours = duration_sec / 3600.0

        # Memory scaling factor (relative to 1024 MB baseline)
        memory_scale = max(0.25, memory_mb / 1024.0)
        power_watts = hardware_active_power_watts * (0.7 + 0.3 * memory_scale)

        # Active energy in kilowatt-hours
        active_energy_kwh = (power_watts / 1000.0) * duration_hours

        # Multiply by PUE to account for cooling and data center facility overhead
        total_facility_energy_kwh = active_energy_kwh * pue
        return total_facility_energy_kwh

    @staticmethod
    def calculate_carbon_emissions_g(
        energy_kwh: float,
        carbon_intensity_g_per_kwh: float,
    ) -> float:
        """Calculates greenhouse gas emissions in grams of CO2 equivalent.

        Formula:
          Emissions (gCO2eq) = Energy (kWh) * Carbon Intensity (gCO2eq / kWh)

        Args:
            energy_kwh: Energy in kilowatt-hours.
            carbon_intensity_g_per_kwh: Regional grid emission factor in gCO2eq/kWh.

        Returns:
            float: Carbon emissions in grams of CO2eq.
        """
        return energy_kwh * carbon_intensity_g_per_kwh

    @staticmethod
    def calculate_monetary_cost_usd(
        memory_mb: int,
        duration_ms: float,
        compute_cost_per_gb_sec: float = 0.0000166667,
        invocation_cost_per_million: float = 0.20,
    ) -> float:
        """Calculates monetary cloud operational cost in USD."""
        gb = memory_mb / 1024.0
        sec = duration_ms / 1000.0
        compute_cost = gb * sec * compute_cost_per_gb_sec
        invocation_cost = invocation_cost_per_million / 1_000_000.0
        return compute_cost + invocation_cost

