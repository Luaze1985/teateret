"""Tier 2: Boundary Value Analysis & Edge Cases.

Verifies boundary conditions, error handling, adversarial payloads, and system limits:
- Numeric & Currency boundaries (0.0, 0.01, large numbers, negative numbers, NaN/inf).
- Date boundaries (leap years, month rollovers, multi-century dates, corrupt dates).
- File/CSV corruptions (empty files, missing columns, empty labels).
- Adversarial PII injections (emails, Norwegian phone numbers, FNRs, credit card numbers).
- Matching edge cases (identical titles on multiple dates, empty sets, special characters).
- Security & Pipeline boundaries (invalid run IDs, duplicate run IDs, path traversal, unknown source IDs).
"""

from __future__ import annotations

import csv
import math
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

import pytest

from teateret_brief.csv_adapter import (
    CsvMapping,
    MetricMapping,
    _parse_date,
    _parse_number,
    load_aggregated_csv,
)
from teateret_brief.matcher import EventMatcher, PublicEvent
from teateret_brief.models import (
    AnalysisOutput,
    Recommendation,
    SalesObservation,
    SourceSpec,
)
from teateret_brief.pipeline import BriefPipeline, PipelineSettings
from teateret_brief.security import (
    DataPolicyError,
    PathPolicyError,
    RepoPaths,
    SourcePolicy,
    SourcePolicyError,
    assert_aggregated_csv,
    scan_public_artifact,
)
from tests.e2e.conftest import E2ETestFetcher, E2ETestRoles


# ===========================================================================
# 1. Ingestion & Numeric Boundaries (BVA)
# ===========================================================================

class TestTier2NumericBoundaries:
    """Boundary value testing on numerical metrics and currencies."""

    @pytest.mark.parametrize(
        "valid_num,expected",
        [
            ("0", 0.0),
            ("0,00", 0.0),
            ("0.0", 0.0),
            ("0,01", 0.01),
            ("1 000 000 000,00", 1_000_000_000.0),
            ("99999999,99", 99_999_999.99),
        ],
    )
    def test_numeric_valid_boundaries(self, valid_num: str, expected: float):
        """BVA-NUM-1/2/4: Valid numeric boundaries parse correctly."""
        assert _parse_number(valid_num) == pytest.approx(expected, 0.001)

    @pytest.mark.parametrize(
        "invalid_num",
        [
            "-0.01",
            "-1",
            "-18500,00",
            "NaN",
            "nan",
            "inf",
            "-inf",
            "",
            "   ",
            "Utsolgt",
            "N/A",
            "12,34,56",
        ],
    )
    def test_numeric_invalid_boundaries_rejected(self, invalid_num: str):
        """BVA-NUM-3/5/6/7/8: Strict rejection of negatives, non-finite, empty, and non-numeric strings."""
        with pytest.raises(DataPolicyError):
            _parse_number(invalid_num)


# ===========================================================================
# 2. Date Boundaries (BVA)
# ===========================================================================

class TestTier2DateBoundaries:
    """Boundary value testing for calendar dates and leap years."""

    @pytest.mark.parametrize(
        "valid_date_str,expected_date",
        [
            ("2024-02-29", date(2024, 2, 29)),  # Leap year
            ("2028-02-29", date(2028, 2, 29)),  # Future leap year
            ("2025-12-31", date(2025, 12, 31)),  # Year-end
            ("2026-01-01", date(2026, 1, 1)),   # Year-start
            ("1.5.2026", date(2026, 5, 1)),     # Norwegian dot format single digit
            ("01.05.2026", date(2026, 5, 1)),
        ],
    )
    def test_valid_calendar_dates(self, valid_date_str: str, expected_date: date):
        """BVA-DATE-1/3/5/6: Valid leap years and edge boundaries parse correctly."""
        assert _parse_date(valid_date_str) == expected_date

    @pytest.mark.parametrize(
        "invalid_date_str",
        [
            "2026-02-29",  # 2026 is NOT a leap year
            "2026-04-31",  # April has 30 days
            "2026-13-01",  # Invalid month
            "00.00.0000",
            "2026/02/29",
            "invalid-date",
            "2026-00-10",
        ],
    )
    def test_invalid_calendar_dates_rejected(self, invalid_date_str: str):
        """BVA-DATE-2/4/7: Non-leap days, month overflows, and corrupt dates raise DataPolicyError."""
        with pytest.raises(DataPolicyError, match="Ukjent datoformat"):
            _parse_date(invalid_date_str)


# ===========================================================================
# 3. CSV File Corruptions & Ingestion Edge Cases
# ===========================================================================

class TestTier2CsvCorruptions:
    """Boundary testing for corrupt or malformed CSV inputs."""

    def test_empty_csv_file_raises_error(self, tmp_path: Path, default_csv_mapping: CsvMapping):
        """BVA-CSV-1: Empty CSV file (0 bytes) raises DataPolicyError for missing headers."""
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("", encoding="utf-8")
        with pytest.raises(DataPolicyError, match="Påkrevde kolonner mangler"):
            load_aggregated_csv(empty_file, default_csv_mapping)

    def test_empty_label_in_row_raises_error(self, create_csv_file: Callable, default_csv_mapping: CsvMapping):
        """BVA-CSV-2: CSV row with whitespace or empty label raises DataPolicyError."""
        csv_path = create_csv_file(
            rows=[
                {
                    "Dato": "2026-02-25",
                    "ArrangementID": "EVT-260225",
                    "Arrangement": "   ",  # Empty whitespace label
                    "Rom": "Foajeen",
                    "Billetter_Solgt": "40",
                    "Kapasitet": "40",
                    "Bordreservasjoner": "35",
                    "Pakkemenyer": "20",
                    "Omsetning": "18500,00",
                }
            ]
        )
        with pytest.raises(DataPolicyError, match="Arrangement/etikett kan ikke være tom"):
            load_aggregated_csv(csv_path, default_csv_mapping)

    def test_missing_required_column_raises_error(self, create_csv_file: Callable, default_csv_mapping: CsvMapping):
        """BVA-CSV-3: CSV missing declared date or metric column raises DataPolicyError."""
        csv_path = create_csv_file(
            headers=["Dato", "Arrangement", "Rom", "Billetter_Solgt"],  # Missing Omsetning, Kapasitet, etc.
            rows=[
                {"Dato": "2026-02-25", "Arrangement": "Speed date", "Rom": "Foajeen", "Billetter_Solgt": "40"}
            ],
        )
        with pytest.raises(DataPolicyError, match="Påkrevde kolonner mangler"):
            load_aggregated_csv(csv_path, default_csv_mapping)


# ===========================================================================
# 4. Adversarial PII Injection Payloads
# ===========================================================================

class TestTier2AdversarialPII:
    """Adversarial security testing for personal identifiable information (PII) leakage."""

    @pytest.mark.parametrize(
        "malicious_label",
        [
            "Standup kveld (kontakt: ole.hansen@example.com)",
            "Musikal info send til post-krs@teateret-test.no",
            "Show for 91234567 ring før ankomst",
            "Konsert booking +47 987 65 432",
            "Viseaften tlf: 38 12 34 56",
            "Artist personnummer: 01029012345",  # 11-digit Norwegian FNR
            "Kortbetaling ref: 4532 0150 1234 5678",  # 16-digit credit card
        ],
    )
    def test_adversarial_pii_in_cell_payloads(self, malicious_label: str):
        """ADV-PII-1 to ADV-PII-5: Cell-level PII scanner blocks emails, phones, FNRs, and CCs."""
        headers = ["Dato", "Arrangement", "Rom"]
        rows = [["2026-03-13", malicious_label, "Hovedscenen"]]
        with pytest.raises(DataPolicyError):
            assert_aggregated_csv(headers, rows)

    @pytest.mark.parametrize(
        "forbidden_column",
        [
            "kunde",
            "kundenavn",
            "guest_name",
            "kunde_epost",
            "telefon",
            "mobilnummer",
            "adresse",
            "kommentar",
            "reservasjonsnotat",
        ],
    )
    def test_adversarial_forbidden_column_injection(self, forbidden_column: str):
        """ADV-PII-6: Ingestion header validator rejects all forbidden PII column variants."""
        headers = ["Dato", "Arrangement", forbidden_column]
        rows = [["2026-03-13", "Svanesjøen", "Verdi"]]
        with pytest.raises(DataPolicyError, match="Person- eller fritekstfelt er ikke tillatt"):
            assert_aggregated_csv(headers, rows)


# ===========================================================================
# 5. Matching & Disambiguation Boundaries
# ===========================================================================

class TestTier2MatchingBoundaries:
    """Corner cases and boundaries for the 3-level event matcher."""

    def test_identical_titles_on_different_dates(self, default_matcher: EventMatcher):
        """T2-MAT-01: Recurring titles (e.g. ImproTorsdag) match the correct specific date."""
        obs_jan16 = SalesObservation(
            period=date(2025, 1, 16),
            label="ImproTorsdag",
            room="Intimscenen",
            metric="tickets_sold",
            value=60.0,
            unit="billetter",
        )
        res = default_matcher.match(obs_jan16)
        assert res.match_status == "matched"
        assert res.period == date(2025, 1, 16)

    def test_matching_with_empty_observations_list(self, default_matcher: EventMatcher):
        """T2-MAT-02: evaluate_all handles empty observation list without zero-division."""
        report = default_matcher.evaluate_all([])
        assert report.total_observations == 0
        assert report.matched_count == 0
        assert report.match_rate_percent == 0.0
        assert report.results == []

    def test_title_with_all_norwegian_special_characters(self, default_matcher: EventMatcher):
        """T2-MAT-03: Titles with æ, ø, å, &, and dashes normalize cleanly."""
        custom_event = PublicEvent(
            event_id="EVT-SPECIAL",
            date=date(2026, 6, 1),
            title="Åse & Øystein på Blåbærtur i Æresgalleriet",
            room="Intimscenen",
        )
        matcher = EventMatcher([custom_event])
        obs = SalesObservation(
            period=date(2026, 6, 1),
            label="åse og øystein på blåbærtur i æresgalleriet",
            metric="tickets_sold",
            value=45.0,
            unit="billetter",
        )
        res = matcher.match(obs)
        assert res.match_status in ("matched", "needs_review")

    def test_extreme_title_lengths(self):
        """T2-MAT-04: Matcher handles short and exceptionally long event titles."""
        short_event = PublicEvent(event_id="EVT-S", date=date(2026, 5, 1), title="X", room="Biscenen")
        long_title = "En Ekstremt Lang Tittel " * 15
        long_event = PublicEvent(event_id="EVT-L", date=date(2026, 5, 2), title=long_title.strip(), room="Hovedscenen")

        matcher = EventMatcher([short_event, long_event])
        obs_short = SalesObservation(period=date(2026, 5, 1), label="X", metric="tickets_sold", value=10.0, unit="stk")
        obs_long = SalesObservation(period=date(2026, 5, 2), label=long_title[:50], metric="tickets_sold", value=100.0, unit="stk")

        assert matcher.match(obs_short).match_status == "matched"
        assert matcher.match(obs_long).match_status == "matched"


# ===========================================================================
# 6. Pipeline, Staging & Security Boundaries
# ===========================================================================

class TestTier2PipelineSecurityBoundaries:
    """Security boundaries and fault handling in BriefPipeline."""

    @pytest.mark.parametrize(
        "invalid_run_id",
        [
            ".",
            "..",
            "-start",
            "end-",
            "run id with spaces",
            "run@special#char",
            "/absolute/path",
            "../../escape",
        ],
    )
    def test_invalid_run_id_rejected_before_staging(self, tmp_repo: Path, mock_fetcher: E2ETestFetcher, mock_roles: E2ETestRoles, invalid_run_id: str):
        """T2-SEC-01: Invalid run IDs are strictly rejected before staging directory creation."""
        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hva bør vi gjøre?"]),
            mock_fetcher,
            mock_roles,
        )
        with pytest.raises(ValueError, match="Ugyldig run-ID"):
            pipeline.run([], [], run_id=invalid_run_id)

    def test_duplicate_run_id_raises_file_exists_error(self, tmp_repo: Path, mock_fetcher: E2ETestFetcher, mock_roles: E2ETestRoles):
        """T2-SEC-02: Executing pipeline with an existing run_id raises FileExistsError."""
        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hva bør vi gjøre?"]),
            mock_fetcher,
            mock_roles,
        )
        sources = [
            SourceSpec(
                id="source-1",
                name="Test Source",
                url="https://example.com/test",
                region="local",
                topic="events",
            )
        ]
        res1 = pipeline.run(sources, [], run_id="dup-run-id")
        assert res1.status == "completed"

        with pytest.raises(FileExistsError, match="Run finnes allerede: dup-run-id"):
            pipeline.run(sources, [], run_id="dup-run-id")

    def test_unknown_source_id_in_recommendations_blocks_run(self, tmp_repo: Path, mock_fetcher: E2ETestFetcher):
        """T2-SEC-03: Recommendations referencing non-existent source IDs cause safe blocked run."""
        class MaliciousRoles(E2ETestRoles):
            def analyze(self, signals, observations, decision_questions, **kwargs):
                return AnalysisOutput(
                    recommendations=[
                        Recommendation(
                            id="rec-unverified",
                            action="Handling basert på fabrikert kilde.",
                            rationale="Ukjent opphav.",
                            source_ids=["non-existent-source-id"],
                            expected_value="Ingen",
                            effort="low",
                        )
                    ]
                )

        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hva bør vi gjøre?"]),
            mock_fetcher,
            MaliciousRoles(),
        )
        sources = [
            SourceSpec(
                id="source-1",
                name="Valid Source",
                url="https://example.com/test",
                region="local",
                topic="events",
            )
        ]
        result = pipeline.run(sources, [], run_id="unknown-source-test")
        assert result.status == "blocked"
        assert not (result.run_dir / "brief.md").exists()
        assert (result.run_dir / "errors.json").exists()

    def test_preflight_pii_scanner_blocks_brief_with_phone_leak(self, tmp_repo: Path, mock_fetcher: E2ETestFetcher):
        """T2-SEC-04: Pipeline blocks brief and records error if generated output contains PII phone."""
        class LeakingRoles(E2ETestRoles):
            def analyze(self, signals, observations, decision_questions, **kwargs):
                return AnalysisOutput(
                    recommendations=[
                        Recommendation(
                            id="rec-leak",
                            action="Ring prosjektleder på 99887766 for assistanse.",
                            rationale="Telefonkontakt nødvendig.",
                            source_ids=["source-1"],
                            expected_value="Test",
                            effort="low",
                        )
                    ]
                )

        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hva bør vi gjøre?"]),
            mock_fetcher,
            LeakingRoles(),
        )
        sources = [
            SourceSpec(
                id="source-1",
                name="Valid Source",
                url="https://example.com/test",
                region="local",
                topic="events",
            )
        ]
        result = pipeline.run(sources, [], run_id="pii-leak-test")
        assert result.status == "blocked"
        assert not (result.run_dir / "brief.md").exists()
        errors = (result.run_dir / "errors.json").read_text(encoding="utf-8")
        assert "99887766" not in errors  # Sanitized error trace
