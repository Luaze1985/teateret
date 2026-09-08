"""Adversarial stress tests for CSV adapter and models."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from teateret_brief.config import load_csv_mapping
from teateret_brief.csv_adapter import (
    ROOM_ALIASES,
    CsvMapping,
    _detect_delimiter,
    _parse_date,
    _parse_number,
    load_aggregated_csv,
    normalize_room,
)
from teateret_brief.models import (
    AnalysisOutput,
    MarketObservation,
    ReaderOutput,
    Recommendation,
    ReviewSummary,
    SalesObservation,
    SentimentTopic,
    Signal,
)
from teateret_brief.security import DataPolicyError


class CsvAdapterStressTests(unittest.TestCase):
    """Stress tests covering extreme delimiters, Norwegian number formats, dates, and PII gates."""

    def test_delimiter_variations_and_sniffer(self):
        """Test semicolon, comma, tab, and auto sniffing with complex fields."""
        delims = [
            (";", "Dato;Arrangement;Billetter;Omsetning\n2026-08-20;Konsert med Band, Kor og Solist;150;18500,00\n"),
            (",", 'Dato,Arrangement,Billetter,Omsetning\n2026-08-20,"Konsert med Band; Kor og Solist",150,"18500,00"\n'),
            ("\t", "Dato\tArrangement\tBilletter\tOmsetning\n2026-08-20\tKonsert med Band, Kor; Solist\t150\t18500,00\n"),
        ]
        for explicit_delim, content in delims:
            for conf_delim in (explicit_delim, "auto"):
                with self.subTest(explicit_delim=explicit_delim, conf_delim=conf_delim), tempfile.TemporaryDirectory() as tmp:
                    csv_path = Path(tmp) / "delim.csv"
                    csv_path.write_text(content, encoding="utf-8")
                    mapping = CsvMapping.model_validate(
                        {
                            "delimiter": conf_delim,
                            "date_column": "Dato",
                            "label_column": "Arrangement",
                            "metrics": {
                                "tickets": {"column": "Billetter", "unit": "stk"},
                                "revenue": {"column": "Omsetning", "unit": "NOK"},
                            },
                        }
                    )
                    obs = load_aggregated_csv(csv_path, mapping)
                    self.assertEqual(len(obs), 2)
                    self.assertEqual(obs[0].value, 150.0)
                    self.assertEqual(obs[1].value, 18500.0)

    def test_fallback_sniffer_when_empty_or_no_match(self):
        """Test fallback behavior for delimiter detection."""
        self.assertEqual(_detect_delimiter("", "auto"), ";")
        self.assertEqual(_detect_delimiter("SingleHeaderOnly", "auto"), ";")
        self.assertEqual(_detect_delimiter("A\tB\tC", "auto"), "\t")
        self.assertEqual(_detect_delimiter("A,B,C", "auto"), ",")
        self.assertEqual(_detect_delimiter("A;B;C", "auto"), ";")

    def test_norwegian_thousand_separator_dot_and_decimals(self):
        """Test dot thousand separator, comma decimals, and plain floats."""
        cases = [
            ("1.200", 1200.0),
            ("185.000", 185000.0),
            ("1.200.000", 1200000.0),
            ("1.200.000,50", 1200000.50),
            ("1.234.567.890", 1234567890.0),
            ("1.234.567.890,75", 1234567890.75),
            ("0.50", 0.50),
            ("0.5", 0.5),
            ("50", 50.0),
            ("12,5", 12.5),
            ("12,50", 12.5),
            ("12.5", 12.5),
            ("12.50", 12.5),
            ("0", 0.0),
            (0, 0.0),
            (150, 150.0),
            (12.5, 12.5),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertAlmostEqual(_parse_number(raw), expected, places=5)

    def test_whitespace_nbsp_and_currency_tokens(self):
        """Test non-breaking spaces, currency tokens, and blank/dash values."""
        cases = [
            ("45 500,50", 45500.5),
            ("45\u00a0500,50", 45500.5),
            ("45\u202f500,50", 45500.5),
            ("kr 18 500,00", 18500.0),
            ("kr. 18 500,00", 18500.0),
            ("18500,-", 18500.0),
            ("18500.-", 18500.0),
            ("18500 NOK", 18500.0),
            ("NOK 18500", 18500.0),
            ("kr 185.000 NOK", 185000.0),
            ("Kr 185.000,-", 185000.0),
            ("-", 0.0),
            ("–", 0.0),
            ("—", 0.0),
            ("null", 0.0),
            ("None", 0.0),
            (None, 0.0),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertAlmostEqual(_parse_number(raw), expected, places=5)

        # Tomt/kun-mellomrom og «N/A»/«n/a» avvises nå (streng validering, jf.
        # stabiliseringsrunde 002 / R1). Bindestreker og null/None beholdes som 0.
        for invalid in ("", " ", "N/A", "n/a"):
            with self.subTest(raw=invalid):
                with self.assertRaises(DataPolicyError):
                    _parse_number(invalid)

    def test_invalid_numbers_rejected(self):
        """Negative values, NaN, Inf, and non-numeric strings must raise DataPolicyError."""
        invalid_cases = [
            "-1",
            "-100.50",
            "-18500,00",
            -5.0,
            -1,
            "NaN",
            "nan",
            "inf",
            "-inf",
            "+infinity",
            float("nan"),
            float("inf"),
            float("-inf"),
            "abc",
            "kr abc",
            "12.34.56",
        ]
        for invalid in invalid_cases:
            with self.subTest(invalid=invalid):
                with self.assertRaises(DataPolicyError):
                    _parse_number(invalid)

    def test_date_parsing_valid_and_invalid(self):
        """Test valid ISO/Norwegian formats and invalid calendar dates."""
        valid_dates = [
            ("2026-02-25", date(2026, 2, 25)),
            ("25.02.2026", date(2026, 2, 25)),
            ("25/02/2026", date(2026, 2, 25)),
            ("2026-02-25 19:30:00", date(2026, 2, 25)),
            ("2026-02-25T19:30:00", date(2026, 2, 25)),
            ("2026-02-25T19:30:00+01:00", date(2026, 2, 25)),
            ("25.02.2026 19:30", date(2026, 2, 25)),
            ("25/02/2026 19:30:00", date(2026, 2, 25)),
            ("2024-02-29", date(2024, 2, 29)),  # Leap year
        ]
        for raw, expected in valid_dates:
            with self.subTest(raw=raw):
                self.assertEqual(_parse_date(raw), expected)

        invalid_dates = [
            "2026-02-31",  # Invalid day in Feb
            "2026-02-29",  # 2026 is not a leap year
            "31.04.2026",  # April has 30 days
            "2026-13-01",  # Invalid month
            "2026-00-01",  # Invalid month
            "not-a-date",
            "",
            "2026/02/25",  # Unsupported format
        ]
        for invalid in invalid_dates:
            with self.subTest(invalid=invalid):
                with self.assertRaises(DataPolicyError):
                    _parse_date(invalid)

    def test_room_normalization_comprehensive(self):
        """Test canonical rooms, all aliases, compound rooms, and fallback."""
        for alias, canonical in ROOM_ALIASES.items():
            with self.subTest(alias=alias):
                self.assertEqual(normalize_room(alias), canonical)

        # Compound rooms
        self.assertEqual(
            normalize_room("Hovedsalen / Black Box"),
            "Hovedscenen / Biscenen",
        )
        self.assertEqual(
            normalize_room("Foajé / Restauranten"),
            "Foajeen / Restauranten",
        )
        # Unknown custom room is preserved trimmed
        self.assertEqual(normalize_room("Bakgården"), "Bakgården")
        # Empty/None
        self.assertIsNone(normalize_room(None))
        self.assertIsNone(normalize_room(""))
        self.assertIsNone(normalize_room("   "))

    def test_missing_and_unknown_columns(self):
        """Test strict vs non-strict column handling."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "sales.csv"
            csv_path.write_text(
                "Dato;Arrangement;Billetter\n2026-08-20;Konsert;150\n",
                encoding="utf-8",
            )
            # Missing column
            mapping_missing = CsvMapping.model_validate(
                {
                    "delimiter": ";",
                    "date_column": "Dato",
                    "label_column": "Arrangement",
                    "metrics": {
                        "tickets": {"column": "Billetter", "unit": "stk"},
                        "revenue": {"column": "ManglerKolonne", "unit": "NOK"},
                    },
                }
            )
            with self.assertRaises(DataPolicyError):
                load_aggregated_csv(csv_path, mapping_missing)

            # Unknown column in strict mode
            csv_extra = Path(tmp) / "sales_extra.csv"
            csv_extra.write_text(
                "Dato;Arrangement;Billetter;UkjentKolonne\n2026-08-20;Konsert;150;test\n",
                encoding="utf-8",
            )
            mapping_strict = CsvMapping.model_validate(
                {
                    "delimiter": ";",
                    "strict_columns": True,
                    "date_column": "Dato",
                    "label_column": "Arrangement",
                    "metrics": {
                        "tickets": {"column": "Billetter", "unit": "stk"},
                    },
                }
            )
            with self.assertRaises(DataPolicyError):
                load_aggregated_csv(csv_extra, mapping_strict)

            # Non-strict mode allows extra column
            mapping_loose = CsvMapping.model_validate(
                {
                    "delimiter": ";",
                    "strict_columns": False,
                    "date_column": "Dato",
                    "label_column": "Arrangement",
                    "metrics": {
                        "tickets": {"column": "Billetter", "unit": "stk"},
                    },
                }
            )
            obs = load_aggregated_csv(csv_extra, mapping_loose)
            self.assertEqual(len(obs), 1)

    def test_pii_in_csv_values_blocked(self):
        """Test that email, phone numbers, or credit card numbers in cell values are blocked."""
        pii_rows = [
            ("Ola Nordmann", "Dato;Arrangement;Billetter\n2026-08-20;ola.nordmann@example.com;150\n"),
            ("Telefon", "Dato;Arrangement;Billetter\n2026-08-20;Konsert tlf 91234567;150\n"),
        ]
        mapping = CsvMapping.model_validate(
            {
                "delimiter": ";",
                "date_column": "Dato",
                "label_column": "Arrangement",
                "metrics": {
                    "tickets": {"column": "Billetter", "unit": "stk"},
                },
            }
        )
        for label, content in pii_rows:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                csv_path = Path(tmp) / "pii.csv"
                csv_path.write_text(content, encoding="utf-8")
                with self.assertRaises(DataPolicyError):
                    load_aggregated_csv(csv_path, mapping)

    def test_empty_label_rejected(self):
        """Empty event label must raise DataPolicyError."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "empty_label.csv"
            csv_path.write_text(
                "Dato;Arrangement;Billetter\n2026-08-20;   ;150\n",
                encoding="utf-8",
            )
            mapping = CsvMapping.model_validate(
                {
                    "delimiter": ";",
                    "date_column": "Dato",
                    "label_column": "Arrangement",
                    "metrics": {
                        "tickets": {"column": "Billetter", "unit": "stk"},
                    },
                }
            )
            with self.assertRaises(DataPolicyError):
                load_aggregated_csv(csv_path, mapping)

    def test_reference_dataset_gastroplanner_sample_2026(self):
        """Full validation of the 45-observation reference dataset."""
        mapping_path = Path("config/gastroplanner_mapping.example.yml")
        csv_path = Path("sample_data/gastroplanner_sample_2026.csv")
        self.assertTrue(mapping_path.exists(), "Mapping file not found")
        self.assertTrue(csv_path.exists(), "Sample CSV not found")

        mapping = load_csv_mapping(mapping_path)
        observations = load_aggregated_csv(csv_path, mapping)

        self.assertEqual(len(observations), 45)
        for obs in observations:
            self.assertIsInstance(obs, SalesObservation)
            self.assertGreaterEqual(obs.value, 0.0)
            self.assertEqual(obs.source_system, "GastroPlanner")
            self.assertEqual(obs.match_status, "matched")
            self.assertIn(obs.room, {"Foajeen", "Hovedscenen", "Biscenen", "Intimscenen"})
            self.assertTrue(obs.event_id.startswith("EVT-26"))
            self.assertTrue(len(obs.label) > 0)
            self.assertIn(obs.unit, {"billetter", "plasser", "bord", "pakker", "NOK"})


class ModelsStressTests(unittest.TestCase):
    """Stress tests for Pydantic models in models.py."""

    def test_sales_observation_validation(self):
        """Test field constraints on SalesObservation."""
        obs = SalesObservation(
            period=date(2026, 8, 20),
            label="Test Event",
            metric="revenue_nok",
            value=1000.0,
            unit="NOK",
        )
        self.assertEqual(obs.source_system, "GastroPlanner")
        self.assertEqual(obs.match_status, "matched")
        self.assertIsNone(obs.room)
        self.assertIsNone(obs.event_id)

    def test_market_observation_validation(self):
        """Test MarketObservation source systems and fields."""
        m_obs = MarketObservation(
            period=date(2026, 8, 20),
            source_system="google_trends",
            metric="search_interest",
            value=75.0,
            unit="index",
            label="Teateret",
            geography="local",
            detail={"term": "konsert kristiansand"},
        )
        self.assertEqual(m_obs.source_system, "google_trends")
        self.assertEqual(m_obs.value, 75.0)

    def test_review_summary_rating_bounds(self):
        """Test rating bounds [1.0, 5.0] on ReviewSummary."""
        rev = ReviewSummary(
            source_system="google_places",
            place_name="Teateret",
            rating=4.5,
            total_reviews=150,
            fetched_at="2026-08-20T10:00:00Z",
            sentiment_topics=[
                SentimentTopic(
                    topic="stemning",
                    sentiment="positive",
                    mention_count=12,
                    sample_quotes=["Flott stemning!"],
                )
            ],
        )
        self.assertEqual(rev.rating, 4.5)

    def test_signal_and_recommendation_deduplication(self):
        """Signal source_ids deduplication and duplicate ID rejection."""
        sig = Signal(
            id="sig-1",
            claim="Trender viser økt interesse",
            source_ids=["src-1", "src-1", "src-2"],
            geography="Kristiansand",
            confidence="confirmed",
        )
        self.assertEqual(sig.source_ids, ["src-1", "src-2"])

        # Duplicate signal ids in ReaderOutput
        with self.assertRaises(ValueError):
            ReaderOutput(signals=[sig, sig])

        rec = Recommendation(
            id="rec-1",
            action="Øk kapasitet",
            rationale="Stor etterspørsel",
            source_ids=["src-1"],
            expected_value="Høyere omsetning",
            effort="medium",
        )
        # Duplicate rec ids in AnalysisOutput
        with self.assertRaises(ValueError):
            AnalysisOutput(recommendations=[rec, rec])


if __name__ == "__main__":
    unittest.main()
