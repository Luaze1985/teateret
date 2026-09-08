from __future__ import annotations

import pytest
from datetime import date
from pathlib import Path

from teateret_brief.google_trends import (
    GoogleTrendsAdapter,
    FixtureGoogleTrendsAdapter,
    GoogleTrendsConfig
)
from teateret_brief.models import MarketObservation

class MockSeries:
    def __init__(self, values):
        self._values = values
    
    def __len__(self):
        return len(self._values)
    
    @property
    def iloc(self):
        return self._values


@pytest.fixture
def config():
    return GoogleTrendsConfig(keywords=["test"])

@pytest.fixture
def fixture_path():
    return Path(__file__).parent.parent / "sample_data" / "google_trends_fixture.json"

def test_fixture_adapter_returns_valid_observations(fixture_path, config):
    adapter = FixtureGoogleTrendsAdapter(fixture_path, config)
    observations = adapter.fetch()
    
    assert len(observations) > 0
    assert all(isinstance(obs, MarketObservation) for obs in observations)

def test_fixture_observation_count_matches_keywords(fixture_path, config):
    adapter = FixtureGoogleTrendsAdapter(fixture_path, config)
    observations = adapter.fetch()
    
    assert len(observations) == 5

def test_fixture_values_in_range(fixture_path, config):
    adapter = FixtureGoogleTrendsAdapter(fixture_path, config)
    observations = adapter.fetch()
    
    for obs in observations:
        assert 0 <= obs.value <= 100

def test_fixture_geography_is_agder(fixture_path, config):
    adapter = FixtureGoogleTrendsAdapter(fixture_path, config)
    observations = adapter.fetch()
    
    for obs in observations:
        assert obs.geography == "agder"

def test_fixture_source_system(fixture_path, config):
    adapter = FixtureGoogleTrendsAdapter(fixture_path, config)
    observations = adapter.fetch()
    
    for obs in observations:
        assert obs.source_system == "google_trends"

def test_trend_direction_rising():
    series = MockSeries([10.0, 10.0, 12.0])  # +20%
    assert GoogleTrendsAdapter._trend_direction(series) == "rising"

def test_trend_direction_falling():
    series = MockSeries([10.0, 10.0, 8.0])  # -20%
    assert GoogleTrendsAdapter._trend_direction(series) == "falling"

def test_trend_direction_stable():
    series = MockSeries([10.0, 10.0, 11.0])  # +10%
    assert GoogleTrendsAdapter._trend_direction(series) == "stable"
    
def test_trend_direction_zero_to_positive():
    series = MockSeries([0.0, 0.0, 5.0])
    assert GoogleTrendsAdapter._trend_direction(series) == "rising"

def test_missing_fixture_raises(config):
    missing_path = Path("nonexistent.json")
    with pytest.raises(FileNotFoundError):
        FixtureGoogleTrendsAdapter(missing_path, config)

def test_config_defaults():
    cfg = GoogleTrendsConfig(keywords=["test"])
    assert cfg.geo == "NO-42"
    assert cfg.timeframe == "today 3-m"
    assert cfg.max_keywords_per_call == 5
