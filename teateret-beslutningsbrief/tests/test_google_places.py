import json
import os
from pathlib import Path
import pytest

from teateret_brief.google_places import (
    GooglePlacesAdapter,
    FixtureGooglePlacesAdapter,
    GooglePlacesConfig,
    PlaceConfig,
)
from teateret_brief.security import DataPolicyError, redact_reviewer_identity


@pytest.fixture
def config():
    return GooglePlacesConfig(
        places=[PlaceConfig(place_id="test_id", name="Teateret Kristiansand")],
        sentiment_topics=["mat", "service", "lyd", "atmosfære", "pris"],
        max_reviews_per_place=20,
    )


@pytest.fixture
def fixture_path():
    return Path(__file__).parent.parent / "sample_data" / "google_places_fixture.json"


def test_fixture_adapter_returns_valid_result(fixture_path, config):
    adapter = FixtureGooglePlacesAdapter(fixture_path, config)
    results = adapter.fetch_all()
    assert len(results) == 1
    res = results[0]
    assert res.review_summary.place_name == "Teateret Kristiansand"


def test_fixture_review_summary_fields(fixture_path, config):
    adapter = FixtureGooglePlacesAdapter(fixture_path, config)
    res = adapter.fetch(config.places[0])
    
    assert res.review_summary.rating == 4.6
    assert res.review_summary.total_reviews == 847
    
    topics = {t.topic: t for t in res.review_summary.sentiment_topics}
    assert "mat" in topics
    assert topics["mat"].sentiment == "positive"
    assert topics["mat"].mention_count == 12


def test_fixture_observations_valid(fixture_path, config):
    adapter = FixtureGooglePlacesAdapter(fixture_path, config)
    res = adapter.fetch(config.places[0])
    
    obs_metrics = {obs.metric: obs for obs in res.observations}
    assert "rating" in obs_metrics
    assert obs_metrics["rating"].value == 4.6
    assert "review_count" in obs_metrics
    assert obs_metrics["review_count"].value == 847.0


def test_pii_redaction_in_reviews(config):
    # Setup mock data for live adapter test
    mock_data = {
        "rating": 4.0,
        "userRatingCount": 10,
        "reviews": [
            {
                "text": "Min epost er nordmann@example.com og maten var god.",
                "authorAttribution": {"displayName": "Ola Nordmann"}
            }
        ]
    }
    
    os.environ["GOOGLE_PLACES_API_KEY"] = "dummy_key"
    adapter = GooglePlacesAdapter(config)
    res = adapter._parse_response(mock_data, config.places[0])
    
    topics = {t.topic: t for t in res.review_summary.sentiment_topics}
    mat_quotes = topics["mat"].sample_quotes
    assert len(mat_quotes) == 1
    assert "MASKERT_EPOST" in mat_quotes[0]
    assert "nordmann@example.com" not in mat_quotes[0]
    # In addition, "Ola Nordmann" components might be redacted but the text didn't contain "Ola" itself, 
    # except we should test that the redact_reviewer_identity does its job separately.


def test_api_key_not_in_output():
    # If the key were output, it would be a problem. We just verify the adapter 
    # doesn't leak it in standard string representation.
    os.environ["GOOGLE_PLACES_API_KEY"] = "secret_key_123"
    # Create adapter, ensure the string doesn't contain the key
    adapter = GooglePlacesAdapter(
        GooglePlacesConfig(
            places=[PlaceConfig(place_id="1", name="1")], 
            sentiment_topics=[]
        )
    )
    assert "secret_key_123" not in str(adapter)


def test_review_limit_enforced(config):
    # Test that we slice correctly up to max_reviews, but if the API
    # returns more than max_reviews, we slice it BEFORE checking limit.
    # Actually _parse_response explicitly slices and then asserts.
    os.environ["GOOGLE_PLACES_API_KEY"] = "dummy_key"
    
    # We should configure max_reviews to 2, pass 3, and ensure it slices to 2
    # So it won't raise, unless we pass something that bypasses slicing.
    # The assert_review_limit is mostly a guard rail. Let's test it directly.
    from teateret_brief.security import assert_review_limit
    with pytest.raises(DataPolicyError):
        assert_review_limit(25, 20)
    
    assert_review_limit(20, 20)  # should not raise


def test_redact_reviewer_identity():
    text = "Kari Nordmann var her. Maten var god Kari! Nordmann."
    res = redact_reviewer_identity(text, "Kari Nordmann")
    assert "Kari" not in res
    assert "Nordmann" not in res
    assert "[ANMELDER]" in res


def test_missing_api_key_raises(config):
    if "GOOGLE_PLACES_API_KEY" in os.environ:
        del os.environ["GOOGLE_PLACES_API_KEY"]
        
    with pytest.raises(ValueError, match="ikke satt"):
        GooglePlacesAdapter(config)
