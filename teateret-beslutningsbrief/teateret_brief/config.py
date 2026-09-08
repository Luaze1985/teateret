from __future__ import annotations

from pathlib import Path

import yaml

from .csv_adapter import CsvMapping
from .models import SourceSpec
from .pipeline import PipelineSettings


def _load_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Konfigurasjonen må være et objekt: {path.name}")
    return payload


def load_sources(path: Path) -> tuple[list[SourceSpec], dict[str, str]]:
    payload = _load_yaml(path)
    sources = [SourceSpec.model_validate(item) for item in payload.get("sources", [])]
    source_ids = [source.id for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Kilde-ID-er må være unike.")
    fixtures = payload.get("fixtures", {})
    if not isinstance(fixtures, dict):
        raise ValueError("fixtures må være et objekt med source_id og relativ filsti.")
    return sources, {str(key): str(value) for key, value in fixtures.items()}


def load_csv_mapping(path: Path) -> CsvMapping:
    return CsvMapping.model_validate(_load_yaml(path))


def load_runtime_settings(path: Path) -> PipelineSettings:
    return PipelineSettings.model_validate(_load_yaml(path))


def load_google_places_config(path: Path):
    from .google_places import GooglePlacesConfig, PlaceConfig

    payload = _load_yaml(path).get("google_places", {})
    places = [
        PlaceConfig(
            place_id=p["place_id"],
            name=p["name"],
            role=p.get("role", "primary"),
            enabled=p.get("enabled", True),
        )
        for p in payload.get("places", [])
    ]
    return GooglePlacesConfig(
        places=places,
        sentiment_topics=payload.get(
            "sentiment_topics", ["mat", "service", "lyd", "atmosfære", "pris"]
        ),
        max_reviews_per_place=payload.get("max_reviews_per_place", 20),
        language=payload.get("language", "no"),
    )


def load_google_trends_config(path: Path):
    from .google_trends import GoogleTrendsConfig

    payload = _load_yaml(path).get("google_trends", {})
    return GoogleTrendsConfig(
        keywords=payload.get("keywords", []),
        geo=payload.get("geo", "NO-42"),
        timeframe=payload.get("timeframe", "today 3-m"),
        max_keywords_per_call=payload.get("max_keywords_per_call", 5),
    )
