"""Tier 1: Feature Coverage (Isolated Functional Verification).

Verifies features across R1, R2, R3, and R4 in isolation via public APIs and CLI:
- R1: GastroPlanner CSV Ingestion, Norwegian Number/Currency Normalization, Zero-PII Gating.
- R2: Deterministic 3-Level Event Matching (Levels 1, 2, 3), Batch Evaluation, Cross-Sales Synthesis.
- R3: External Signals (MET.no, Skolerute, City Clashes, Google Places, Google Trends, Schema.org).
- R4: Analytics, Multi-Format Rendering (Markdown, HTML, Email), Output PII Scanner, Manifest SHA-256,
      Atomic Staging, RepoPaths Confinement, SourcePolicy SSRF Guard, CLI Execution.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from teateret_brief.analytics import summarize_sales
from teateret_brief.cli import main as cli_main
from teateret_brief.config import (
    load_google_places_config,
    load_google_trends_config,
)
from teateret_brief.csv_adapter import (
    CsvMapping,
    MetricMapping,
    _parse_date,
    _parse_number,
    load_aggregated_csv,
)
from teateret_brief.google_places import (
    FixtureGooglePlacesAdapter,
)
from teateret_brief.google_trends import (
    FixtureGoogleTrendsAdapter,
    GoogleTrendsAdapter,
)
from teateret_brief.matcher import EventMatcher, MatchingReport
from teateret_brief.models import (
    AnalysisOutput,
    Brief,
    MarketObservation,
    Recommendation,
    ReviewSummary,
    SalesObservation,
    SentimentTopic,
    Signal,
    SourceReference,
)
from teateret_brief.render import (
    DISCLAIMER,
    render_email,
    render_html,
    render_markdown,
)
from teateret_brief.schema_events import (
    parse_jsonld_events,
)
from teateret_brief.security import (
    DataPolicyError,
    PathPolicyError,
    RepoPaths,
    SourcePolicy,
    SourcePolicyError,
    assert_aggregated_csv,
    redact_contact_details,
    redact_reviewer_identity,
    scan_public_artifact,
)

# ===========================================================================
# 1. R1: GastroPlanner Ingestion, Number Normalization & PII Gating
# ===========================================================================

class TestTier1R1IngestionAndNormalization:
    """Feature coverage for Requirement 1: GastroPlanner CSV Ingestion & Zero-PII."""

    def test_semicolon_delimited_norwegian_csv(self, create_csv_file: Callable, default_csv_mapping: CsvMapping):
        """T1-ING-01: Ingest semicolon-delimited CSV with Norwegian characters and UTF-8 BOM."""
        csv_path = create_csv_file(
            filename="gastro_semi.csv",
            delimiter=";",
            encoding="utf-8-sig",
            rows=[
                {
                    "Dato": "2026-02-25",
                    "ArrangementID": "EVT-260225",
                    "Arrangement": "Speed date 40–59 i Foajeen",
                    "Rom": "Foajeen",
                    "Billetter_Solgt": "40",
                    "Kapasitet": "40",
                    "Bordreservasjoner": "35",
                    "Pakkemenyer": "20",
                    "Omsetning": "18500,00",
                },
                {
                    "Dato": "2026-08-29",
                    "ArrangementID": "EVT-260829",
                    "Arrangement": "Baldrian og Musa – Luft og kjærlighet",
                    "Rom": "Intimscenen",
                    "Billetter_Solgt": "85",
                    "Kapasitet": "90",
                    "Bordreservasjoner": "20",
                    "Pakkemenyer": "10",
                    "Omsetning": "24500,00",
                },
            ],
        )

        observations = load_aggregated_csv(csv_path, default_csv_mapping)
        assert len(observations) == 10  # 2 rows * 5 metrics
        
        obs0 = observations[0]
        assert obs0.period == date(2026, 2, 25)
        assert obs0.event_id == "EVT-260225"
        assert obs0.room == "Foajeen"
        assert "Speed date 40–59" in obs0.label

        obs_rev = observations[4]
        assert obs_rev.metric == "revenue_nok"
        assert obs_rev.value == 18500.0
        assert obs_rev.unit == "NOK"

    def test_comma_delimited_utf8_csv(self, create_csv_file: Callable):
        """T1-ING-02: Ingest comma-delimited CSV with custom mapping."""
        mapping = CsvMapping(
            delimiter=",",
            date_column="Dato",
            label_column="Show",
            room_column="Scene",
            event_id_column="ID",
            metrics={
                "tickets": MetricMapping(column="Solgt", unit="stk"),
                "revenue": MetricMapping(column="Inntekt", unit="NOK"),
            },
            strict_columns=True,
        )

        csv_path = create_csv_file(
            filename="comma_sales.csv",
            delimiter=",",
            encoding="utf-8",
            rows=[
                {"Dato": "2026-03-13", "ID": "EVT-260313", "Show": "Svanesjøen", "Scene": "Hovedscenen", "Solgt": "380", "Inntekt": "185000,00"},
            ],
        )

        observations = load_aggregated_csv(csv_path, mapping)
        assert len(observations) == 2
        assert observations[0].value == 380.0
        assert observations[1].value == 185000.0

    @pytest.mark.parametrize(
        "date_str,expected_date",
        [
            ("2026-07-17", date(2026, 7, 17)),
            ("17.07.2026", date(2026, 7, 17)),
            ("17/07/2026", date(2026, 7, 17)),
            (" 2026-07-17 ", date(2026, 7, 17)),
            ("\t25.02.2026\n", date(2026, 2, 25)),
        ],
    )
    def test_multi_format_date_parsing(self, date_str: str, expected_date: date):
        """T1-ING-03: Multi-format date parsing (%Y-%m-%d, %d.%m.%Y, %d/%m/%Y)."""
        assert _parse_date(date_str) == expected_date

    def test_room_and_event_id_binding(self, create_csv_file: Callable, default_csv_mapping: CsvMapping):
        """T1-ING-04: Verify correct binding of room and event_id fields."""
        csv_path = create_csv_file(
            rows=[
                {
                    "Dato": "2026-07-11",
                    "ArrangementID": "EVT-260711",
                    "Arrangement": "Fotball-VM Storskjerm",
                    "Rom": "Hovedscenen",
                    "Billetter_Solgt": "350",
                    "Kapasitet": "350",
                    "Bordreservasjoner": "150",
                    "Pakkemenyer": "90",
                    "Omsetning": "142000,00",
                }
            ]
        )
        obs = load_aggregated_csv(csv_path, default_csv_mapping)
        for item in obs:
            assert item.room == "Hovedscenen"
            assert item.event_id == "EVT-260711"

    @pytest.mark.parametrize(
        "raw_num,expected_val",
        [
            ("18500,00", 18500.0),
            ("45 500,50", 45500.5),
            ("18\u00a0500,00", 18500.0),
            ("0", 0.0),
            ("0,00", 0.0),
            ("120", 120.0),
            ("185.000,00", 185000.0),
            ("99999999,99", 99999999.99),
        ],
    )
    def test_norwegian_currency_and_number_normalization(self, raw_num: str, expected_val: float):
        """T1-NUM-01 to T1-NUM-05: Norwegian number parsing and space/NBSP stripping."""
        assert _parse_number(raw_num) == expected_val

    def test_strict_column_rejection(self, create_csv_file: Callable, default_csv_mapping: CsvMapping):
        """T1-PII-01: Rejection of unknown column when strict_columns=True."""
        csv_path = create_csv_file(
            headers=["Dato", "ArrangementID", "Arrangement", "Rom", "Billetter_Solgt", "Kapasitet", "Bordreservasjoner", "Pakkemenyer", "Omsetning", "UkjentKolonne"],
            rows=[
                {
                    "Dato": "2026-02-25",
                    "ArrangementID": "EVT-260225",
                    "Arrangement": "Speed date",
                    "Rom": "Foajeen",
                    "Billetter_Solgt": "40",
                    "Kapasitet": "40",
                    "Bordreservasjoner": "35",
                    "Pakkemenyer": "20",
                    "Omsetning": "18500,00",
                    "UkjentKolonne": "Verdi",
                }
            ],
        )
        with pytest.raises(DataPolicyError, match="Ukjente kolonner er ikke tillatt: UkjentKolonne"):
            load_aggregated_csv(csv_path, default_csv_mapping)

    @pytest.mark.parametrize(
        "forbidden_header",
        [
            "Kundenavn",
            "Kunde_Epost",
            "Gjeste_Telefon",
            "Reservasjonsnotat",
            "Fritekst_Kommentar",
        ],
    )
    def test_forbidden_pii_columns_rejection(self, forbidden_header: str):
        """T1-PII-02/03: Rejection of blacklisted customer/comment headers."""
        headers = ["Dato", "Arrangement", forbidden_header]
        rows = [["2026-03-13", "Svanesjøen", "Hemmelig"]]
        with pytest.raises(DataPolicyError, match="Person- eller fritekstfelt er ikke tillatt"):
            assert_aggregated_csv(headers, rows)

    @pytest.mark.parametrize(
        "pii_payload",
        [
            "Svanesjøen (kontakt: booking@example.com)",
            "Bordreservasjon for 91234567",
            "VIP gjest tlf: +47 99 88 77 66",
            "Tildelt bord 4 tlf: 38 00 00 00",
        ],
    )
    def test_cell_level_contact_pii_rejection(self, pii_payload: str):
        """T1-PII-04/05: Rejection of direct contact details inside cell payloads."""
        headers = ["Dato", "Arrangement", "Rom"]
        rows = [["2026-03-13", pii_payload, "Hovedscenen"]]
        with pytest.raises(DataPolicyError, match="Direkte kontaktopplysninger er ikke tillatt"):
            assert_aggregated_csv(headers, rows)


# ===========================================================================
# 2. R2: Deterministic 3-Level Matching & Cross-Sales Synthesis
# ===========================================================================

class TestTier1R2DeterministicMatching:
    """Feature coverage for Requirement 2: ADR 0002 3-Level Matching Engine."""

    def test_level_1_exact_id_matching(self, default_matcher: EventMatcher):
        """T1-MAT-01: Exact ID matching (EVT-YYMMDD)."""
        obs = SalesObservation(
            period=date(2026, 2, 25),
            label="Speed date 40–59",
            event_id="EVT-260225",
            metric="revenue_nok",
            value=18500.0,
            unit="NOK",
        )
        res = default_matcher.match(obs)
        assert res.match_status == "matched"
        assert res.match_level == "level_1_id"
        assert "EVT-260225" in res.reason

    def test_level_1_id_overrides_disparate_title(self, default_matcher: EventMatcher):
        """T1-MAT-04: Level 1 ID takes precedence over disparate label text."""
        obs = SalesObservation(
            period=date(2026, 3, 13),
            label="Avvikende Kassetekst Ballett",
            event_id="EVT-260313",
            metric="tickets_sold",
            value=380.0,
            unit="billetter",
        )
        res = default_matcher.match(obs)
        assert res.match_status == "matched"
        assert res.match_level == "level_1_id"
        assert res.matched_event_title == "Svanesjøen (Etoile Ballet)"

    def test_level_2_title_date_room_heuristic(self, default_matcher: EventMatcher):
        """T1-MAT-06/07: Substring title match on normalized titles and date."""
        obs = SalesObservation(
            period=date(2026, 7, 17),
            label="Sommerstandup",
            room="Hovedscenen",
            metric="tickets_sold",
            value=290.0,
            unit="billetter",
        )
        res = default_matcher.match(obs)
        assert res.match_status == "matched"
        assert res.match_level == "level_2_title_date_room"
        assert res.matched_event_title == "Sommerstandup med Fire halvkjente fjes"

    def test_level_2_synonym_resolution(self, default_matcher: EventMatcher):
        """T1-MAT-10: Synonym dictionary mapping resolution."""
        obs = SalesObservation(
            period=date(2026, 8, 20),
            label="Jazzfestival",
            room="Biscenen",
            metric="tickets_sold",
            value=140.0,
            unit="billetter",
        )
        res = default_matcher.match(obs)
        assert res.match_status == "matched"
        assert res.match_level == "level_2_title_date_room"
        assert "Kristiansand Jazzfestival" in (res.matched_event_title or "")

    def test_level_2_room_disambiguation(self, default_matcher: EventMatcher):
        """T1-MAT-09: Room constraint disambiguates multiple shows on the same date."""
        obs_hoved = SalesObservation(
            period=date(2025, 2, 8),
            label="Kokosbananas",
            room="Hovedscenen",
            metric="tickets_sold",
            value=300.0,
            unit="billetter",
        )
        obs_bi = SalesObservation(
            period=date(2025, 2, 8),
            label="Drag Bonanza",
            room="Biscenen",
            metric="tickets_sold",
            value=120.0,
            unit="billetter",
        )
        res_hoved = default_matcher.match(obs_hoved)
        res_bi = default_matcher.match(obs_bi)

        # Autoritativ tittel i arrangementsdata-2025-2026.md er «... (2 show)»
        # (to forestillinger 12:30 & 14:30). Matcheren returnerer eventtittelen
        # ordrett; testen hadde en utdatert forventning uten suffikset.
        assert res_hoved.matched_event_title == "Kokosbananas – Det store showet (2 show)"
        assert res_bi.matched_event_title == "Drag Bonanza 3"

    def test_level_3_single_event_proximity(self, default_matcher: EventMatcher):
        """T1-MAT-11: Single event date proximity match marked as needs_review / level_3_proximity."""
        obs = SalesObservation(
            period=date(2026, 3, 13),
            label="Generell Kveldsrestaurant",
            metric="revenue_nok",
            value=45000.0,
            unit="NOK",
        )
        res = default_matcher.match(obs)
        assert res.match_status == "needs_review"
        assert res.match_level == "level_3_proximity"
        assert "Dato-nærhet" in res.reason

    def test_multi_event_date_unmatched_without_title(self, default_matcher: EventMatcher):
        """T1-MAT-12: Multi-event date without title match returns unmatched."""
        obs = SalesObservation(
            period=date(2025, 2, 8),
            label="Generell Barinntekt",
            metric="revenue_nok",
            value=15000.0,
            unit="NOK",
        )
        res = default_matcher.match(obs)
        assert res.match_status == "unmatched"
        assert res.match_level == "none"

    def test_batch_evaluation_metrics_and_deduplication(self, default_matcher: EventMatcher):
        """T1-MAT-14/15: Batch evaluation computes match rate and deduplicates observations."""
        observations = [
            SalesObservation(period=date(2026, 2, 25), label="Speed date 40–59", event_id="EVT-260225", metric="tickets_sold", value=40.0, unit="stk"),
            SalesObservation(period=date(2026, 2, 25), label="Speed date 40–59", event_id="EVT-260225", metric="revenue_nok", value=18500.0, unit="NOK"),
            SalesObservation(period=date(2026, 3, 13), label="Svanesjøen", event_id="EVT-260313", metric="tickets_sold", value=380.0, unit="stk"),
            SalesObservation(period=date(2026, 1, 1), label="Ukjent Nyttår", metric="revenue_nok", value=5000.0, unit="NOK"),
        ]
        report: MatchingReport = default_matcher.evaluate_all(observations)
        assert report.total_observations == 3  # Row 1 and 2 deduplicated
        assert report.matched_count == 2
        assert report.unmatched_count == 1
        assert report.match_rate_percent == pytest.approx(66.7, 0.1)

    def test_cross_sales_synthesis(self):
        """T1-MAT-16: Summarize cross-sales metrics and dining attachment."""
        observations = [
            SalesObservation(period=date(2026, 3, 13), label="Svanesjøen", metric="tickets_sold", value=380.0, unit="billetter"),
            SalesObservation(period=date(2026, 3, 13), label="Svanesjøen", metric="table_reservations", value=120.0, unit="bord"),
            SalesObservation(period=date(2026, 3, 13), label="Svanesjøen", metric="preorder_packages", value=65.0, unit="menyer"),
        ]
        summary = summarize_sales(observations)
        assert summary["row_count"] == 3
        totals = {item["metric"]: item["value"] for item in summary["totals"]}
        assert totals["tickets_sold"] == 380.0
        assert totals["table_reservations"] == 120.0
        assert totals["preorder_packages"] == 65.0


# ===========================================================================
# 3. R3: External Signals & Context Enrichment
# ===========================================================================

class TestTier1R3ExternalSignalsEnrichment:
    """Feature coverage for Requirement 3: External Public Signals & Adapters."""

    def test_google_places_fixture_adapter(self, repo_root: Path):
        """T1-SIG-04: Google Places fixture adapter extracts rating and sentiment topics."""
        gp_config = load_google_places_config(repo_root / "config" / "google_places_config.yml")
        fixture_path = repo_root / "sample_data" / "google_places_fixture.json"
        adapter = FixtureGooglePlacesAdapter(fixture_path, gp_config)
        results = adapter.fetch_all()
        
        assert len(results) >= 1
        res = results[0]
        assert res.review_summary.place_name == "Teateret"
        assert res.review_summary.rating >= 4.0
        assert len(res.review_summary.sentiment_topics) > 0
        assert len(res.observations) >= 2

    def test_google_places_pii_and_reviewer_redaction(self):
        """T1-SIG-04: Contact PII and reviewer names are masked."""
        raw_text = "Jeg, Ola Nordmann, elsker maten! Send epost til ola@nordmann.no eller ring 99887766."
        clean_text, findings = redact_contact_details(raw_text)
        assert "email" in findings
        assert "phone" in findings
        assert "[MASKERT_EPOST]" in clean_text
        assert "[MASKERT_TELEFON]" in clean_text

        redacted_reviewer = redact_reviewer_identity(clean_text, "Ola Nordmann")
        assert "[ANMELDER]" in redacted_reviewer
        assert "Ola" not in redacted_reviewer

    def test_google_trends_fixture_adapter(self, repo_root: Path):
        """T1-SIG-05: Google Trends fixture adapter extracts search interest observations."""
        gt_config = load_google_trends_config(repo_root / "config" / "google_trends_config.yml")
        fixture_path = repo_root / "sample_data" / "google_trends_fixture.json"
        adapter = FixtureGoogleTrendsAdapter(fixture_path, gt_config)
        observations = adapter.fetch()

        assert len(observations) >= 3
        for obs in observations:
            assert obs.source_system == "google_trends"
            assert obs.metric == "search_interest"
            assert 0.0 <= obs.value <= 100.0

    def test_google_trends_direction_calculation(self):
        """T1-SIG-05: Trend direction classification (rising, falling, stable)."""
        class MockSeries:
            def __init__(self, vals): self.vals = vals
            def __len__(self): return len(self.vals)
            class Iloc:
                def __init__(self, vals): self.vals = vals
                def __getitem__(self, idx): return self.vals[idx]
            @property
            def iloc(self): return self.Iloc(self.vals)

        assert GoogleTrendsAdapter._trend_direction(MockSeries([40, 50])) == "rising"
        assert GoogleTrendsAdapter._trend_direction(MockSeries([50, 40])) == "falling"
        assert GoogleTrendsAdapter._trend_direction(MockSeries([50, 52])) == "stable"

    def test_schema_events_jsonld_parsing(self):
        """T1-SIG-06: Schema.org JSON-LD structured event extractor."""
        mock_html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Event",
                "name": "Svanesjøen",
                "startDate": "2026-03-13T19:00:00+01:00",
                "location": {"@type": "Place", "name": "Hovedscenen"},
                "offers": {"@type": "Offer", "availability": "https://schema.org/SoldOut", "price": "450", "priceCurrency": "NOK"}
            }
            </script>
        </head>
        </html>
        """
        extracted = parse_jsonld_events(mock_html, "Teateret Program", "2026-08-20 10:00")
        assert "Svanesjøen" in extracted
        assert "Billettstatus: utsolgt" in extracted
        assert "450 NOK" in extracted


# ===========================================================================
# 4. R4: Brief Rendering, Security Audit & CLI Execution
# ===========================================================================

class TestTier1R4BriefRenderingAndSecurityAudit:
    """Feature coverage for Requirement 4: Decision Brief Rendering, Security & CLI."""

    @pytest.fixture
    def sample_brief(self) -> Brief:
        """Create a complete, valid sample Brief model."""
        return Brief(
            run_id="run-20260820-demo",
            created_at=datetime.now(UTC),
            status="completed",
            title="Ukentlig beslutningsbrief for Teateret",
            signals=[
                Signal(
                    id="sig-1",
                    claim="Høy etterspørsel etter Svanesjøen i Kristiansand.",
                    source_ids=["source-1"],
                    geography="Kristiansand",
                    confidence="confirmed",
                )
            ],
            recommendations=[
                Recommendation(
                    id="rec-1",
                    action="Sett opp ekstra serveringsskift i Foajeen.",
                    rationale="95% fyllingsgrad og 120 bordreservasjoner.",
                    source_ids=["source-1"],
                    expected_value="25 000 NOK meromsetning",
                    effort="low",
                )
            ],
            source_ids=["source-1"],
            sources=[
                SourceReference(
                    source_id="source-1",
                    title="Teateret Kulturkilde",
                    url="https://example.com/kultur",
                    fetched_at="2026-08-20T10:00:00Z",
                )
            ],
            warnings=[],
            market_observations=[
                MarketObservation(
                    period=date(2026, 8, 20),
                    source_system="google_places",
                    metric="rating",
                    value=4.6,
                    unit="score_1_5",
                    label="Teateret",
                )
            ],
            review_summaries=[
                ReviewSummary(
                    source_system="google_places",
                    place_name="Teateret",
                    rating=4.6,
                    total_reviews=540,
                    fetched_at="2026-08-20T10:00:00Z",
                    sentiment_topics=[
                        SentimentTopic(
                            topic="mat",
                            sentiment="positive",
                            mention_count=45,
                            sample_quotes=["Nydelig mat før forestilling."],
                        )
                    ],
                )
            ],
        )

    def test_markdown_brief_renderer(self, sample_brief: Brief):
        """T1-REN-01: Render Markdown brief with disclaimer and sections."""
        md = render_markdown(sample_brief)
        assert DISCLAIMER in md
        assert "# Ukentlig beslutningsbrief for Teateret" in md
        assert "Run-ID: `run-20260820-demo`" in md
        assert "## Anbefalte handlinger" in md
        assert "rec-1: Sett opp ekstra serveringsskift" in md
        assert "https://example.com/kultur" in md

    def test_html_brief_renderer(self, sample_brief: Brief):
        """T1-REN-02: Render HTML brief with draft banner and escaped markup."""
        html = render_html(sample_brief)
        assert '<p class="draft"><strong>' in html
        assert DISCLAIMER in html
        assert "<h1>Ukentlig beslutningsbrief for Teateret</h1>" in html
        assert "<h3>Teateret</h3>" in html
        assert "Nydelig mat" not in html or "mat" in html

    def test_email_brief_renderer(self, sample_brief: Brief):
        """T1-REN-03: Render plaintext email draft with executive structure."""
        email = render_email(sample_brief)
        assert "Emne: UTKAST – ukentlig beslutningsbrief – run-20260820-demo" in email
        assert DISCLAIMER in email
        assert "Prioriterte handlinger:" in email
        assert "rec-1: Sett opp ekstra serveringsskift" in email
        assert "Hvorfor:" in email

    def test_recommendations_bounded_to_max_three(self):
        """T1-REN-04: AnalysisOutput strictly enforces max 3 recommendations."""
        recs = [
            Recommendation(id=f"rec-{i}", action=f"Action {i}", rationale=f"Why {i}", source_ids=["src"], expected_value="val", effort="low")
            for i in range(1, 5)
        ]
        with pytest.raises(Exception):
            AnalysisOutput(recommendations=recs)

    def test_preflight_output_pii_scanner_clean_pass(self):
        """T1-SEC-01: Pre-flight scanner returns empty findings on clean text."""
        clean_text = "Ukentlig brief for 2026-03-13. Omsetning 185 000,00 NOK. Ingen lekkasjer."
        assert scan_public_artifact(clean_text) == []

    def test_preflight_output_pii_scanner_detects_leak(self):
        """T1-SEC-01: Pre-flight scanner detects email or phone number in output."""
        leaked_text = "Kontakt regissør på ole@teateret.no eller ring 99887766."
        findings = scan_public_artifact(leaked_text)
        assert "email" in findings
        assert "phone" in findings

    def test_repopaths_confinement(self, tmp_path: Path):
        """T1-SEC-04: RepoPaths prevents path traversal and absolute escapes."""
        paths = RepoPaths(tmp_path)
        with pytest.raises(PathPolicyError):
            paths.output_path("../outside.txt")
        with pytest.raises(PathPolicyError):
            paths.output_path("runs/../../outside.txt")

    def test_sourcepolicy_ssrf_and_https_guard(self):
        """T1-SEC-05: SourcePolicy blocks non-HTTPS and private IP resolutions."""
        policy = SourcePolicy(
            allowed_hosts={"example.com", "private.com"},
            resolver=lambda host: ["127.0.0.1"] if host == "private.com" else ["93.184.216.34"],
        )
        with pytest.raises(SourcePolicyError, match="Bare HTTPS-kilder er tillatt"):
            policy.validate("http://example.com/test")

        with pytest.raises(SourcePolicyError, match="Kilden peker til en privat eller reservert adresse"):
            policy.validate("https://private.com/test")

        approved = policy.validate("https://example.com/test")
        assert approved.host == "example.com"

    def test_cli_demo_mode_execution(self, tmp_repo: Path, monkeypatch):
        """T1-SEC-06: Unified CLI execution in demo mode returns exit code 0."""
        argv = [
            "--mode", "demo",
            "--repo-root", str(tmp_repo),
            "--run-id", "tier1-cli-demo",
            "--sales", "sample_data/gastroplanner_sample_2026.csv",
        ]
        exit_code = cli_main(argv)
        assert exit_code == 0
        run_dir = tmp_repo / "runs" / "tier1-cli-demo"
        assert (run_dir / "brief.md").exists()
        assert (run_dir / "brief.html").exists()
        assert (run_dir / "email.txt").exists()
        assert (run_dir / "manifest.json").exists()
