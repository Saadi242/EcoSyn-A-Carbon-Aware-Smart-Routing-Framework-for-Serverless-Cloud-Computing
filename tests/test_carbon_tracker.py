"""Unit tests for the Carbon Tracker subsystem."""

import pytest
from pathlib import Path
from config import load_config
from src.carbon_tracker import create_carbon_tracker, TraceCarbonTracker


@pytest.fixture
def config():
    return load_config()


@pytest.fixture
def tracker(config):
    return create_carbon_tracker(config)


def test_tracker_initialization(tracker):
    regions = tracker.get_tracked_regions()
    assert len(regions) >= 4
    assert "eu-north-1" in regions
    assert "us-east-1" in regions


def test_trace_carbon_intensities(tracker):
    # Stockholm (eu-north-1) should have very low emissions (around 20-40)
    stockholm_carb = tracker.get_carbon_intensity("eu-north-1", timestamp_sec=0.0)
    assert 10.0 <= stockholm_carb <= 50.0

    # Mumbai (ap-south-1) should have high coal emissions (around 500-700)
    mumbai_carb = tracker.get_carbon_intensity("ap-south-1", timestamp_sec=0.0)
    assert 500.0 <= mumbai_carb <= 750.0

    # Virginia (us-east-1) should be moderate-to-high
    virginia_carb = tracker.get_carbon_intensity("us-east-1", timestamp_sec=0.0)
    assert 250.0 <= virginia_carb <= 500.0


def test_get_all_regions_carbon(tracker):
    all_carbons = tracker.get_all_regions_carbon(timestamp_sec=3600.0) # Hour 1
    assert isinstance(all_carbons, dict)
    assert "eu-north-1" in all_carbons
    assert "sa-east-1" in all_carbons
    for reg, val in all_carbons.items():
        assert val > 0.0

