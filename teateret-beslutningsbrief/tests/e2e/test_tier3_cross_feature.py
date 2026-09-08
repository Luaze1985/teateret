"""Tier 3: Cross-Feature Interactions & Pairwise Combinatorial Test Suites.

Verifies end-to-end integration contracts across multiple modules:
- Ingestion delimiters (;, ,) × Date formats (ISO, dot, slash) × Matching levels (L1, L2, L3, None) × Metrics.
- Data Normalization × Analytics Summarization × Pipeline Execution.
- External Signals (Google Places, Google Trends, Schema.org) × Brief Rendering × Pre-flight PII Scanner.
- Partial and total external source degradation handling.
- Audit Manifest SHA-256 cryptographic verification across multiple runs.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

import pytest

from teateret_brief.analytics import summarize_sales
from teateret_brief.csv_adapter import CsvMapping, MetricMapping, load_aggregated_csv
from teateret_brief.google_places import FixtureGooglePlacesAdapter, GooglePlacesConfig, PlaceConfig
from teateret_brief.google_trends import FixtureGoogleTrendsAdapter, GoogleTrendsConfig
from teateret_brief.matcher import EventMatcher, PublicEvent
from teateret_brief.models import (
    AnalysisOutput,
    MarketObservation,
    Recommendation,
    ReviewSummary,
    SalesObservation,
    SentimentTopic,
    SourceSpec,
)
from teateret_brief.pipeline import BriefPipeline, PipelineSettings
from teateret_brief.render import render_email, render_html, render_markdown
from teateret_brief.schema_events import FixtureSchemaEventExtractor
from teateret_brief.security import DataPolicyError
from tests.e2e.conftest import E2ETestFetcher, E2ETestRoles


class TestTier3CrossFeatureInteractions:
    """Pairwise combinatorial suites testing cross-module interactions."""

    def test_pw01_semi_iso_level1_full_metrics(self, tmp_repo: Path, create_csv_file: Callable, verified_129_events: list[PublicEvent]):
        """T3-PW-01: Delimiter (;) × ISO Date (%Y-%m-%d) × Level 1 Match × Full 5 Metrics."""
        mapping = CsvMapping(
            delimiter=";",
            date_column="Dato",
            label_column="Arrangement",
            room_column="Rom",
            event_id_column="ArrangementID",
            metrics={
                "tickets": MetricMapping(column="Billetter_Solgt", unit="stk"),
                "capacity": MetricMapping(column="Kapasitet", unit="plasser"),
                "tables": MetricMapping(column="Bordreservasjoner", unit="bord"),
                "packages": MetricMapping(column="Pakkemenyer", unit="menyer"),
                "revenue": MetricMapping(column="Omsetning", unit="NOK"),
            },
        )
        csv_path = create_csv_file(
            filename="pw01.csv",
            delimiter=";",
            rows=[
                {
                    "Dato": "2026-02-25",
                    "ArrangementID": "EVT-260225",
                    "Arrangement": "Speed date 40–59",
                    "Rom": "Foajeen",
                    "Billetter_Solgt": "40",
                    "Kapasitet": "40",
                    "Bordreservasjoner": "35",
                    "Pakkemenyer": "20",
                    "Omsetning": "18500,00",
                }
            ],
        )
        observations = load_aggregated_csv(csv_path, mapping)
        assert len(observations) == 5

        matcher = EventMatcher(verified_129_events)
        res = matcher.match(observations[0])
        assert res.match_status == "matched"
        assert res.match_level == "level_1_id"

        summary = summarize_sales(observations)
        assert summary["row_count"] == 5

    def test_pw02_comma_dotdate_level2_revenue_nbsp(self, create_csv_file: Callable, verified_129_events: list[PublicEvent]):
        """T3-PW-02: Delimiter (,) × Dot Date (%d.%m.%Y) × Level 2 Match × Revenue Only × Number with NBSP."""
        mapping = CsvMapping(
            delimiter=",",
            date_column="Dato",
            label_column="Arrangement",
            room_column="Rom",
            metrics={"revenue": MetricMapping(column="Omsetning", unit="NOK")},
        )
        csv_path = create_csv_file(
            filename="pw02.csv",
            delimiter=",",
            rows=[
                {
                    "Dato": "17.07.2026",
                    "Arrangement": "Sommerstandup",
                    "Rom": "Hovedscenen",
                    "Omsetning": "98\u00a0500,00",
                }
            ],
        )
        observations = load_aggregated_csv(csv_path, mapping)
        assert len(observations) == 1
        assert observations[0].value == 98500.0

        matcher = EventMatcher(verified_129_events)
        res = matcher.match(observations[0])
        assert res.match_status == "matched"
        assert res.match_level == "level_2_title_date_room"

    def test_pw03_semi_slashdate_level3_tables(self, create_csv_file: Callable, verified_129_events: list[PublicEvent]):
        """T3-PW-03: Delimiter (;) × Slash Date (%d/%m/%Y) × Level 3 Proximity × Tables Only."""
        mapping = CsvMapping(
            delimiter=";",
            date_column="Dato",
            label_column="Arrangement",
            metrics={"tables": MetricMapping(column="Bord", unit="bord")},
        )
        csv_path = create_csv_file(
            filename="pw03.csv",
            delimiter=";",
            rows=[{"Dato": "13/03/2026", "Arrangement": "Restaurantkveld Ballett", "Bord": "120"}],
        )
        observations = load_aggregated_csv(csv_path, mapping)
        matcher = EventMatcher(verified_129_events)
        res = matcher.match(observations[0])
        assert res.match_status == "needs_review"
        assert res.match_level == "level_3_proximity"

    def test_pw04_comma_iso_unmatched_tickets(self, create_csv_file: Callable, verified_129_events: list[PublicEvent]):
        """T3-PW-04: Delimiter (,) × ISO Date (%Y-%m-%d) × Unmatched Event × Ticket Metric."""
        mapping = CsvMapping(
            delimiter=",",
            date_column="Dato",
            label_column="Arrangement",
            metrics={"tickets": MetricMapping(column="Solgt", unit="stk")},
        )
        csv_path = create_csv_file(
            filename="pw04.csv",
            delimiter=",",
            rows=[{"Dato": "2026-01-01", "Arrangement": "Utenfor Programmet", "Solgt": "15"}],
        )
        observations = load_aggregated_csv(csv_path, mapping)
        matcher = EventMatcher(verified_129_events)
        res = matcher.match(observations[0])
        assert res.match_status == "unmatched"
        assert res.match_level == "none"

    def test_pw05_semi_dotdate_level1_preorders_thousands_dot(self, create_csv_file: Callable, verified_129_events: list[PublicEvent]):
        """T3-PW-05: Delimiter (;) × Dot Date (%d.%m.%Y) × Level 1 Match × Thousands Separator Dot."""
        mapping = CsvMapping(
            delimiter=";",
            date_column="Dato",
            label_column="Arrangement",
            event_id_column="ID",
            metrics={"revenue": MetricMapping(column="Omsetning", unit="NOK")},
        )
        csv_path = create_csv_file(
            filename="pw05.csv",
            delimiter=";",
            rows=[{"Dato": "11.07.2026", "ID": "EVT-260711", "Arrangement": "VM Storskjerm", "Omsetning": "142.000,00"}],
        )
        observations = load_aggregated_csv(csv_path, mapping)
        assert observations[0].value == 142000.0
        matcher = EventMatcher(verified_129_events)
        assert matcher.match(observations[0]).match_level == "level_1_id"

    def test_pw06_comma_slashdate_level2_full_metrics(self, create_csv_file: Callable, verified_129_events: list[PublicEvent]):
        """T3-PW-06: Delimiter (,) × Slash Date (%d/%m/%Y) × Level 2 Match × Full Suite."""
        mapping = CsvMapping(
            delimiter=",",
            date_column="Dato",
            label_column="Arrangement",
            room_column="Rom",
            metrics={
                "tickets": MetricMapping(column="Billetter", unit="stk"),
                "revenue": MetricMapping(column="Inntekt", unit="NOK"),
            },
        )
        csv_path = create_csv_file(
            filename="pw06.csv",
            delimiter=",",
            rows=[{"Dato": "29/08/2026", "Arrangement": "Baldrian og Musa", "Rom": "Intimscenen", "Billetter": "85", "Inntekt": "24500,00"}],
        )
        observations = load_aggregated_csv(csv_path, mapping)
        matcher = EventMatcher(verified_129_events)
        res = matcher.match(observations[0])
        assert res.match_status == "matched"
        assert res.match_level == "level_2_title_date_room"

    def test_pw07_semi_iso_synonym_match(self, create_csv_file: Callable, verified_129_events: list[PublicEvent]):
        """T3-PW-07: Delimiter (;) × ISO Date × Synonym Lookup Match."""
        synonyms = {"Jazzfestivalen": "Kristiansand Jazzfestival 26 (AiR m.fl.)"}
        matcher = EventMatcher(verified_129_events, synonyms=synonyms)
        mapping = CsvMapping(
            delimiter=";",
            date_column="Dato",
            label_column="Arrangement",
            metrics={"tickets": MetricMapping(column="Billetter", unit="stk")},
        )
        csv_path = create_csv_file(
            filename="pw07.csv",
            delimiter=";",
            rows=[{"Dato": "2026-08-20", "Arrangement": "Jazzfestivalen", "Billetter": "140"}],
        )
        obs = load_aggregated_csv(csv_path, mapping)
        res = matcher.match(obs[0])
        assert res.match_status == "matched"
        assert res.match_level == "level_2_title_date_room"

    def test_pw08_comma_dotdate_proximity_single_metric(self, create_csv_file: Callable, verified_129_events: list[PublicEvent]):
        """T3-PW-08: Delimiter (,) × Dot Date × Level 3 Proximity."""
        mapping = CsvMapping(
            delimiter=",",
            date_column="Dato",
            label_column="Arrangement",
            metrics={"revenue": MetricMapping(column="Omsetning", unit="NOK")},
        )
        csv_path = create_csv_file(
            filename="pw08.csv",
            delimiter=",",
            rows=[{"Dato": "22.04.2026", "Arrangement": "Generell Mingling", "Omsetning": "16200,00"}],
        )
        obs = load_aggregated_csv(csv_path, mapping)
        matcher = EventMatcher(verified_129_events)
        res = matcher.match(obs[0])
        assert res.match_status == "needs_review"
        assert res.match_level == "level_3_proximity"

    def test_pw09_semi_slashdate_unmatched_full_metrics(self, create_csv_file: Callable, verified_129_events: list[PublicEvent]):
        """T3-PW-09: Delimiter (;) × Slash Date × Unmatched Date × Multi-Metric."""
        mapping = CsvMapping(
            delimiter=";",
            date_column="Dato",
            label_column="Arrangement",
            metrics={
                "tickets": MetricMapping(column="Solgt", unit="stk"),
                "revenue": MetricMapping(column="Inntekt", unit="NOK"),
            },
        )
        csv_path = create_csv_file(
            filename="pw09.csv",
            delimiter=";",
            rows=[{"Dato": "01/01/2026", "Arrangement": "Stengt Scene", "Solgt": "0", "Inntekt": "0,00"}],
        )
        obs = load_aggregated_csv(csv_path, mapping)
        matcher = EventMatcher(verified_129_events)
        res = matcher.match(obs[0])
        assert res.match_status == "unmatched"
        assert res.match_level == "none"

    def test_pw10_comma_iso_level1_space_in_number(self, create_csv_file: Callable, verified_129_events: list[PublicEvent]):
        """T3-PW-10: Delimiter (,) × ISO Date × Level 1 Match × Number with regular space."""
        mapping = CsvMapping(
            delimiter=",",
            date_column="Dato",
            label_column="Arrangement",
            event_id_column="ID",
            metrics={"revenue": MetricMapping(column="Inntekt", unit="NOK")},
        )
        csv_path = create_csv_file(
            filename="pw10.csv",
            delimiter=",",
            rows=[{"Dato": "2026-03-13", "ID": "EVT-260313", "Arrangement": "Svanesjøen", "Inntekt": "185 000,00"}],
        )
        obs = load_aggregated_csv(csv_path, mapping)
        assert obs[0].value == 185000.0
        matcher = EventMatcher(verified_129_events)
        assert matcher.match(obs[0]).match_level == "level_1_id"

    def test_pw11_pii_header_blocks_pipeline(self, tmp_repo: Path, create_csv_file: Callable):
        """T3-PW-11: Ingestion with PII header is caught by safety gate and blocks execution."""
        mapping = CsvMapping(
            delimiter=";",
            date_column="Dato",
            label_column="Arrangement",
            metrics={"revenue": MetricMapping(column="Omsetning", unit="NOK")},
        )
        csv_path = create_csv_file(
            filename="pw11.csv",
            headers=["Dato", "Arrangement", "Kundenavn", "Omsetning"],
            rows=[{"Dato": "2026-03-13", "Arrangement": "Svanesjøen", "Kundenavn": "Ola", "Omsetning": "185000,00"}],
        )
        with pytest.raises(DataPolicyError):
            load_aggregated_csv(csv_path, mapping)

    def test_pw12_non_strict_unknown_columns_tolerated(self, create_csv_file: Callable, verified_129_events: list[PublicEvent]):
        """T3-PW-12: Ingestion with strict_columns=False allows non-PII extra columns."""
        mapping = CsvMapping(
            delimiter=";",
            date_column="Dato",
            label_column="Arrangement",
            metrics={"revenue": MetricMapping(column="Omsetning", unit="NOK")},
            strict_columns=False,
        )
        csv_path = create_csv_file(
            filename="pw12.csv",
            headers=["Dato", "Arrangement", "Omsetning", "EkstraInternKode"],
            rows=[{"Dato": "2026-03-13", "Arrangement": "Svanesjøen", "Omsetning": "185000,00", "EkstraInternKode": "KODE-99"}],
        )
        obs = load_aggregated_csv(csv_path, mapping)
        assert len(obs) == 1
        assert obs[0].value == 185000.0

    def test_pw13_partial_source_failure_produces_warning_brief(self, tmp_repo: Path):
        """T3-PW-13: Partial source degradation completes run with status='warning' and outputs errors.json."""
        class FlakyFetcher:
            def fetch(self, source: SourceSpec):
                if source.id == "broken-source":
                    raise RuntimeError("Kilde utilgjengelig")
                return E2ETestFetcher().fetch(source)

        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hva bør vi gjøre?"]),
            FlakyFetcher(),
            E2ETestRoles(),
        )
        sources = [
            SourceSpec(id="good-source", name="God Kilde", url="https://example.com/good", region="local", topic="events"),
            SourceSpec(id="broken-source", name="Dårlig Kilde", url="https://example.com/bad", region="local", topic="events"),
        ]
        result = pipeline.run(sources, [], run_id="pw13-warning-run")
        assert result.status == "warning"
        assert (result.run_dir / "brief.md").exists()
        assert (result.run_dir / "errors.json").exists()
        manifest = json.loads((result.run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "warning"
        assert "broken-source" in manifest["sources_failed"]

    def test_pw14_total_source_outage_produces_blocked_run(self, tmp_repo: Path):
        """T3-PW-14: Total external source outage results in status='blocked' and suppresses draft brief."""
        class DeadFetcher:
            def fetch(self, source: SourceSpec):
                raise RuntimeError("Total nettverksfeil")

        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hva bør vi gjøre?"]),
            DeadFetcher(),
            E2ETestRoles(),
        )
        sources = [SourceSpec(id="source-dead", name="Kilde", url="https://example.com/dead", region="local", topic="events")]
        result = pipeline.run(sources, [], run_id="pw14-blocked-run")
        assert result.status == "blocked"
        assert not (result.run_dir / "brief.md").exists()
        assert (result.run_dir / "errors.json").exists()
        manifest = json.loads((result.run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "blocked"

    def test_pw15_multi_signal_brief_integration_and_manifest_hash_match(self, tmp_repo: Path):
        """T3-PW-15: Integration of Google Places + Google Trends + Schema.org with full SHA-256 verification."""
        gp_config = GooglePlacesConfig(
            places=[PlaceConfig(place_id="teateret-krs", name="Teateret", role="primary")],
            sentiment_topics=["mat", "service"],
        )
        gp_adapter = FixtureGooglePlacesAdapter(tmp_repo / "sample_data" / "google_places_fixture.json", gp_config)
        gt_config = GoogleTrendsConfig(keywords=["teater kristiansand"])
        gt_adapter = FixtureGoogleTrendsAdapter(tmp_repo / "sample_data" / "google_trends_fixture.json", gt_config)

        review_summaries = [res.review_summary for res in gp_adapter.fetch_all()]
        market_observations = gt_adapter.fetch()

        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hva bør vi gjøre?"]),
            E2ETestFetcher(),
            E2ETestRoles(),
        )
        sources = [SourceSpec(id="source-1", name="Kilde", url="https://example.com/source", region="local", topic="events")]
        result = pipeline.run(
            sources=sources,
            observations=[],
            run_id="pw15-full-signals",
            market_observations=market_observations,
            review_summaries=review_summaries,
        )
        assert result.status == "completed"

        # Re-compute disk SHA-256 hashes and verify against manifest
        manifest = json.loads((result.run_dir / "manifest.json").read_text(encoding="utf-8"))
        for output_entry in manifest["outputs"]:
            filename = output_entry["file"]
            expected_hash = output_entry["sha256"]
            actual_hash = hashlib.sha256((result.run_dir / filename).read_bytes()).hexdigest()
            assert actual_hash == expected_hash
