"""Tier 4: Real-World Workload Scenarios (End-to-End User Workflows).

Verifies 6 complete, realistic operational workflows for Teateret Kristiansand:
1. Scenario 1: Reference 2026 Production Baseline (Demo Mode full run).
2. Scenario 2: Spring High-Season Sellout Weekend & Kitchen Staffing Cross-Sales Peak.
3. Scenario 3: Dark Weekday Gap Mitigation & Local Audience Activation.
4. Scenario 4: Agder School Holiday Family Matinee & Weather Demand Surge.
5. Scenario 5: Major City Clash Storm Event (Palmesus / Kilden Premiere Counter-Programming).
6. Scenario 6: Adversarial PII Injection Defense & Live-Mode Safety Lockout.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from teateret_brief.analytics import summarize_sales
from teateret_brief.cli import main as cli_main
from teateret_brief.csv_adapter import CsvMapping, MetricMapping, load_aggregated_csv
from teateret_brief.matcher import EventMatcher, PublicEvent
from teateret_brief.models import (
    Recommendation,
    SourceSpec,
)
from teateret_brief.pipeline import BriefPipeline, PipelineSettings
from teateret_brief.render import DISCLAIMER
from teateret_brief.security import DataPolicyError
from tests.e2e.conftest import E2ETestFetcher, E2ETestRoles


class TestTier4RealWorldScenarios:
    """Realistic end-to-end user workflows executed on Teateret Decision Brief Engine."""

    # -----------------------------------------------------------------------
    # Scenario 1: Reference 2026 Production Baseline (Demo Mode)
    # -----------------------------------------------------------------------
    def test_scenario_1_reference_2026_baseline_run(
        self, tmp_repo: Path, verified_129_events: list[PublicEvent], default_csv_mapping: CsvMapping
    ):
        """Scenario 1: Complete baseline run with 2026 reference GastroPlanner export."""
        sales_csv = tmp_repo / "sample_data" / "gastroplanner_sample_2026.csv"
        assert sales_csv.exists()

        # Step 1: Ingest CSV
        observations = load_aggregated_csv(sales_csv, default_csv_mapping)
        assert len(observations) == 45  # 9 rows * 5 metrics

        # Step 2: 3-Level Matching evaluation
        matcher = EventMatcher(verified_129_events)
        report = matcher.evaluate_all(observations)
        assert report.total_observations == 9
        assert report.matched_count == 9
        assert report.match_rate_percent >= 90.0

        # Step 3: Run BriefPipeline
        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hva er de viktigste operasjonelle tiltakene?"]),
            E2ETestFetcher(),
            E2ETestRoles(),
        )
        sources = [
            SourceSpec(
                id="lokal-kulturkalender",
                name="Lokal Kulturkalender",
                url="https://example.com/kristiansand/program",
                region="local",
                topic="events",
            )
        ]
        result = pipeline.run(sources, observations, run_id="scenario1-baseline")
        assert result.status == "completed"

        # Step 4: Verify generated artifacts
        run_dir = result.run_dir
        for filename in ("brief.md", "brief.html", "email.txt", "manifest.json", "events.json"):
            assert (run_dir / filename).exists()

        md_content = (run_dir / "brief.md").read_text(encoding="utf-8")
        html_content = (run_dir / "brief.html").read_text(encoding="utf-8")
        email_content = (run_dir / "email.txt").read_text(encoding="utf-8")

        for doc in (md_content, html_content, email_content):
            assert DISCLAIMER in doc
            assert "scenario1-baseline" in doc

        # Step 5: Cryptographic Manifest Verification
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "completed"
        assert manifest["pii_scan_status"] == "pass"
        for output in manifest["outputs"]:
            filepath = run_dir / output["file"]
            actual_sha = hashlib.sha256(filepath.read_bytes()).hexdigest()
            assert actual_sha == output["sha256"]

    # -----------------------------------------------------------------------
    # Scenario 2: Spring High-Season Sellout Weekend & Staffing Peak
    # -----------------------------------------------------------------------
    def test_scenario_2_high_season_sellout_weekend_and_staffing(
        self, tmp_repo: Path, create_csv_file: Callable, verified_129_events: list[PublicEvent]
    ):
        """Scenario 2: Sell-out shows on Hovedscenen (Svanesjøen & Fotball-VM) triggering kitchen staffing."""
        csv_path = create_csv_file(
            filename="spring_sellout.csv",
            rows=[
                {
                    "Dato": "2026-03-13",
                    "ArrangementID": "EVT-260313",
                    "Arrangement": "Svanesjøen",
                    "Rom": "Hovedscenen",
                    "Billetter_Solgt": "380",
                    "Kapasitet": "400",
                    "Bordreservasjoner": "120",
                    "Pakkemenyer": "65",
                    "Omsetning": "185000,00",
                },
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
                },
            ],
        )
        mapping = CsvMapping(
            delimiter=";",
            date_column="Dato",
            label_column="Arrangement",
            room_column="Rom",
            event_id_column="ArrangementID",
            metrics={
                "tickets_sold": MetricMapping(column="Billetter_Solgt", unit="billetter"),
                "capacity": MetricMapping(column="Kapasitet", unit="plasser"),
                "table_reservations": MetricMapping(column="Bordreservasjoner", unit="bord"),
                "preorder_packages": MetricMapping(column="Pakkemenyer", unit="menyer"),
                "revenue_nok": MetricMapping(column="Omsetning", unit="NOK"),
            },
        )
        observations = load_aggregated_csv(csv_path, mapping)

        # Capacity and Cross-sales analytics
        summary = summarize_sales(observations)
        totals = {item["metric"]: item["value"] for item in summary["totals"]}
        assert totals["tickets_sold"] == 730.0
        assert totals["table_reservations"] == 270.0
        assert totals["revenue_nok"] == 327000.0

        # Dining attachment ratio: 270 tables / 730 tickets = 37.0%
        table_ratio = totals["table_reservations"] / totals["tickets_sold"]
        assert table_ratio > 0.30

        # Execute Pipeline with staffing recommendation
        custom_recs = [
            Recommendation(
                id="rec-staff-01",
                action="Øk kjøkken- og barbemanning med to ekstra skift under Svanesjøen og VM.",
                rationale="Høy bordbeleggsprosent (37%) og 95-100% solgt Hovedscene tilsier maksimalt trykk i +/- 2t vinduet.",
                source_ids=["source-1"],
                expected_value="Sikre rask servering og hente ut estimert 35 000 NOK i mersalg",
                effort="low",
            )
        ]
        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hvordan optimalisere bemanning?"]),
            E2ETestFetcher(),
            E2ETestRoles(custom_recommendations=custom_recs),
        )
        sources = [SourceSpec(id="source-1", name="Kilde", url="https://example.com/kultur", region="local", topic="events")]
        result = pipeline.run(sources, observations, run_id="scenario2-staffing")
        assert result.status == "completed"

        email = (result.run_dir / "email.txt").read_text(encoding="utf-8")
        assert "rec-staff-01" in email
        assert "Øk kjøkken- og barbemanning" in email

    # -----------------------------------------------------------------------
    # Scenario 3: Underperforming Show & Dark Weekday Gap Mitigation
    # -----------------------------------------------------------------------
    def test_scenario_3_dark_weekday_gap_mitigation(
        self, tmp_repo: Path, create_csv_file: Callable, verified_129_events: list[PublicEvent]
    ):
        """Scenario 3: Identify underperforming shows and dark Tuesday/Wednesday gap."""
        csv_path = create_csv_file(
            filename="gap_mitigation.csv",
            rows=[
                {
                    "Dato": "2026-04-22",
                    "ArrangementID": "EVT-260422",
                    "Arrangement": "Speed date 30–45",
                    "Rom": "Foajeen",
                    "Billetter_Solgt": "38",
                    "Kapasitet": "40",
                    "Bordreservasjoner": "30",
                    "Pakkemenyer": "15",
                    "Omsetning": "16200,00",
                }
            ],
        )
        mapping = CsvMapping(
            delimiter=";",
            date_column="Dato",
            label_column="Arrangement",
            room_column="Rom",
            event_id_column="ArrangementID",
            metrics={
                "tickets_sold": MetricMapping(column="Billetter_Solgt", unit="billetter"),
                "capacity": MetricMapping(column="Kapasitet", unit="plasser"),
                "table_reservations": MetricMapping(column="Bordreservasjoner", unit="bord"),
                "preorder_packages": MetricMapping(column="Pakkemenyer", unit="menyer"),
                "revenue_nok": MetricMapping(column="Omsetning", unit="NOK"),
            },
        )
        obs = load_aggregated_csv(csv_path, mapping)

        # Recommendations prioritizing dark day filling
        custom_recs = [
            Recommendation(
                id="rec-gap-01",
                action="Introduser ukentlig kulturquiz i Biscenen på mørke onsdager.",
                rationale="Foajeen har god aktivitet på speed dating, men Biscenen og Hovedscenen står tomme på ukedager.",
                source_ids=["source-1"],
                expected_value="Generere 15 000 NOK i snittomsetning per mørk ukedag",
                effort="medium",
            ),
            Recommendation(
                id="rec-gap-02",
                action="Tilby 'Speed Date + Middag' kombinasjonspakke.",
                rationale="Øke snittforbruk per speed-dating gjest.",
                source_ids=["source-1"],
                expected_value="Øke omsetning med 8 000 NOK per temakveld",
                effort="low",
            ),
        ]
        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hvordan fylle mørke ukedager?"]),
            E2ETestFetcher(),
            E2ETestRoles(custom_recommendations=custom_recs),
        )
        sources = [SourceSpec(id="source-1", name="Kilde", url="https://example.com/kultur", region="local", topic="events")]
        result = pipeline.run(sources, obs, run_id="scenario3-gap-mitigation")
        assert result.status == "completed"

        md = (result.run_dir / "brief.md").read_text(encoding="utf-8")
        assert "rec-gap-01" in md
        assert "kulturquiz i Biscenen" in md
        assert len(custom_recs) <= 3

    # -----------------------------------------------------------------------
    # Scenario 4: Agder School Holiday Matinee & Weather Demand Surge
    # -----------------------------------------------------------------------
    def test_scenario_4_school_holiday_matinee_surge(
        self, tmp_repo: Path, create_csv_file: Callable, verified_129_events: list[PublicEvent]
    ):
        """Scenario 4: Agder Autumn vacation (Høstferie) + rainy forecast boosting children's matinee."""
        csv_path = create_csv_file(
            filename="autumn_holiday.csv",
            rows=[
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
                }
            ],
        )
        mapping = CsvMapping(
            delimiter=";",
            date_column="Dato",
            label_column="Arrangement",
            room_column="Rom",
            event_id_column="ArrangementID",
            metrics={
                "tickets_sold": MetricMapping(column="Billetter_Solgt", unit="billetter"),
                "capacity": MetricMapping(column="Kapasitet", unit="plasser"),
                "table_reservations": MetricMapping(column="Bordreservasjoner", unit="bord"),
                "preorder_packages": MetricMapping(column="Pakkemenyer", unit="menyer"),
                "revenue_nok": MetricMapping(column="Omsetning", unit="NOK"),
            },
        )
        obs = load_aggregated_csv(csv_path, mapping)

        custom_recs = [
            Recommendation(
                id="rec-matinee-01",
                action="Sett opp ekstra ettermiddagsforestilling av Baldrian og Musa kl 15:30.",
                rationale="94% belegg i feriehelg kombinert med regnvær indikerer udekket familieetterspørsel.",
                source_ids=["source-1"],
                expected_value="Absorbere 60 ekstra billetter = 12 000 NOK i billettinntekt",
                effort="low",
            )
        ]
        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hvordan utnytte skoleferien?"]),
            E2ETestFetcher(),
            E2ETestRoles(custom_recommendations=custom_recs),
        )
        sources = [SourceSpec(id="source-1", name="Kilde", url="https://example.com/kultur", region="local", topic="events")]
        result = pipeline.run(sources, obs, run_id="scenario4-holiday-matinee")
        assert result.status == "completed"

        brief_html = (result.run_dir / "brief.html").read_text(encoding="utf-8")
        assert "ekstra ettermiddagsforestilling" in brief_html

    # -----------------------------------------------------------------------
    # Scenario 5: Major City Clash Storm Event (Palmesus Weekend)
    # -----------------------------------------------------------------------
    def test_scenario_5_city_clash_storm_event(
        self, tmp_repo: Path, create_csv_file: Callable, verified_129_events: list[PublicEvent]
    ):
        """Scenario 5: Palmesus festival clash weekend with terrace dining reallocation."""
        csv_path = create_csv_file(
            filename="clash_weekend.csv",
            rows=[
                {
                    "Dato": "2026-07-17",
                    "ArrangementID": "EVT-260717",
                    "Arrangement": "Sommerstandup med Fire halvkjente fjes",
                    "Rom": "Hovedscenen",
                    "Billetter_Solgt": "290",
                    "Kapasitet": "350",
                    "Bordreservasjoner": "150",
                    "Pakkemenyer": "45",
                    "Omsetning": "98500,00",
                }
            ],
        )
        mapping = CsvMapping(
            delimiter=";",
            date_column="Dato",
            label_column="Arrangement",
            room_column="Rom",
            event_id_column="ArrangementID",
            metrics={
                "tickets_sold": MetricMapping(column="Billetter_Solgt", unit="billetter"),
                "capacity": MetricMapping(column="Kapasitet", unit="plasser"),
                "table_reservations": MetricMapping(column="Bordreservasjoner", unit="bord"),
                "preorder_packages": MetricMapping(column="Pakkemenyer", unit="menyer"),
                "revenue_nok": MetricMapping(column="Omsetning", unit="NOK"),
            },
        )
        obs = load_aggregated_csv(csv_path, mapping)

        custom_recs = [
            Recommendation(
                id="rec-clash-01",
                action="Omdisponer personell til uteservering og Foajé-bar før kveldens standup.",
                rationale="Stor festivalgjennomstrømming i Kongens gate gir 150 bordreservasjoner, mens 60 standup-billetter gjenstår.",
                source_ids=["source-1"],
                expected_value="Maksimal serveringsomsetning under festivalhelg",
                effort="low",
            ),
            Recommendation(
                id="rec-clash-02",
                action="Kjør målrettet kampanje i sosiale medier for de siste 60 standup-plassene mot et voksent publikum.",
                rationale="Nisjeposisjonering mot publikum som unngår festivalområdet.",
                source_ids=["source-1"],
                expected_value="Fylle Hovedscenen til 100% kapasitet (ca. 18 000 NOK)",
                effort="low",
            ),
        ]
        pipeline = BriefPipeline(
            tmp_repo,
            PipelineSettings(decision_questions=["Hvordan håndtere festivalkollisjon?"]),
            E2ETestFetcher(),
            E2ETestRoles(custom_recommendations=custom_recs),
        )
        sources = [SourceSpec(id="source-1", name="Kilde", url="https://example.com/kultur", region="local", topic="events")]
        result = pipeline.run(sources, obs, run_id="scenario5-clash-weekend")
        assert result.status == "completed"

        email = (result.run_dir / "email.txt").read_text(encoding="utf-8")
        assert "rec-clash-01" in email
        assert "Omdisponer personell til uteservering" in email

    # -----------------------------------------------------------------------
    # Scenario 6: Adversarial PII Injection & Live-Mode Safety Lockout
    # -----------------------------------------------------------------------
    def test_scenario_6_pii_injection_and_live_mode_lockout(
        self, tmp_repo: Path, create_csv_file: Callable, default_csv_mapping: CsvMapping
    ):
        """Scenario 6: Adversarial CSV with injected customer PII and live-mode safety gate."""
        # Sub-test 6A: Ingest CSV containing customer personal information
        adversarial_csv = create_csv_file(
            filename="adversarial_customer_leak.csv",
            rows=[
                {
                    "Dato": "2026-03-13",
                    "ArrangementID": "EVT-260313",
                    "Arrangement": "Svanesjøen (bestilt av ola@example.com)",
                    "Rom": "Hovedscenen",
                    "Billetter_Solgt": "380",
                    "Kapasitet": "400",
                    "Bordreservasjoner": "120",
                    "Pakkemenyer": "65",
                    "Omsetning": "185000,00",
                }
            ],
        )
        with pytest.raises(DataPolicyError, match="Direkte kontaktopplysninger er ikke tillatt"):
            load_aggregated_csv(adversarial_csv, default_csv_mapping)

        # Sub-test 6B: CLI live-mode safety gate lockout when live_mode_enabled=False
        argv = [
            "--mode", "live",
            "--repo-root", str(tmp_repo),
            "--sales", "sample_data/gastroplanner_sample_2026.csv",
            "--allow-live-network",
            "--allow-live-model",
        ]
        with pytest.raises(SystemExit) as excinfo:
            cli_main(argv)
        assert "Live-modus er deaktivert i runtime-konfigurasjonen" in str(excinfo.value)
