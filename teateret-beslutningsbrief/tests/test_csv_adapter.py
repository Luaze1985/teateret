import tempfile
import unittest
from datetime import date
from pathlib import Path

from teateret_brief.config import load_csv_mapping
from teateret_brief.csv_adapter import (
    CsvMapping,
    _parse_date,
    _parse_number,
    load_aggregated_csv,
    normalize_room,
)
from teateret_brief.security import DataPolicyError


class CsvAdapterTests(unittest.TestCase):
    def test_normalizes_configured_aggregate_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "sales.csv"
            csv_path.write_text(
                "Dato;Arrangement;Reservasjoner;Omsetning\n"
                "19.08.2026;Sommerkveld;120;45 500,50\n",
                encoding="utf-8",
            )
            mapping = CsvMapping.model_validate(
                {
                    "delimiter": ";",
                    "date_column": "Dato",
                    "label_column": "Arrangement",
                    "metrics": {
                        "reservations": {"column": "Reservasjoner", "unit": "count"},
                        "revenue_nok": {"column": "Omsetning", "unit": "NOK"},
                    },
                }
            )

            observations = load_aggregated_csv(csv_path, mapping)

            self.assertEqual(len(observations), 2)
            self.assertEqual(observations[0].label, "Sommerkveld")
            self.assertEqual(observations[0].value, 120.0)
            self.assertEqual(observations[1].value, 45500.5)

    def test_unknown_column_is_rejected_in_strict_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "sales.csv"
            csv_path.write_text(
                "Dato;Arrangement;Reservasjoner;Kundekommentar\n"
                "19.08.2026;Sommerkveld;120;Ring meg\n",
                encoding="utf-8",
            )
            mapping = CsvMapping.model_validate(
                {
                    "delimiter": ";",
                    "date_column": "Dato",
                    "label_column": "Arrangement",
                    "metrics": {
                        "reservations": {"column": "Reservasjoner", "unit": "count"}
                    },
                }
            )
            with self.assertRaises(DataPolicyError):
                load_aggregated_csv(csv_path, mapping)

    def test_non_finite_and_negative_values_are_rejected(self):
        mapping = CsvMapping.model_validate(
            {
                "delimiter": ";",
                "date_column": "Dato",
                "label_column": "Arrangement",
                "metrics": {
                    "reservations": {"column": "Reservasjoner", "unit": "count"}
                },
            }
        )
        for value in ("NaN", "inf", "-inf", "-1", "-18500,00"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                csv_path = Path(tmp) / "sales.csv"
                csv_path.write_text(
                    f"Dato;Arrangement;Reservasjoner\n19.08.2026;Jazz;{value}\n",
                    encoding="utf-8",
                )
                with self.assertRaises(DataPolicyError):
                    load_aggregated_csv(csv_path, mapping)

    def test_loads_room_and_event_id_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "rich_sales.csv"
            csv_path.write_text(
                "Dato;ArrangementID;Arrangement;Rom;Billetter;Omsetning\n"
                "2026-07-17;EVT-123;Sommerstandup;Hovedsalen;290;98500,00\n",
                encoding="utf-8",
            )
            mapping = CsvMapping.model_validate(
                {
                    "delimiter": ";",
                    "date_column": "Dato",
                    "label_column": "Arrangement",
                    "room_column": "Rom",
                    "event_id_column": "ArrangementID",
                    "metrics": {
                        "tickets_sold": {"column": "Billetter", "unit": "billetter"},
                        "revenue_nok": {"column": "Omsetning", "unit": "NOK"},
                    },
                }
            )

            observations = load_aggregated_csv(csv_path, mapping)
            self.assertEqual(len(observations), 2)
            self.assertEqual(observations[0].room, "Hovedscenen")  # Normalized from Hovedsalen
            self.assertEqual(observations[0].event_id, "EVT-123")
            self.assertEqual(observations[0].value, 290.0)
            self.assertEqual(observations[1].value, 98500.0)

    def test_delimiter_sniffing_and_fallbacks(self):
        delimiters = [
            (";", "Dato;Arrangement;Billetter\n2026-08-20;Konsert;150\n"),
            (",", "Dato,Arrangement,Billetter\n2026-08-20,Konsert,150\n"),
            ("\t", "Dato\tArrangement\tBilletter\n2026-08-20\tKonsert\t150\n"),
        ]
        for delim, content in delimiters:
            for conf_delim in (delim, "auto"):
                with self.subTest(delim=delim, conf_delim=conf_delim), tempfile.TemporaryDirectory() as tmp:
                    csv_path = Path(tmp) / "delim_test.csv"
                    csv_path.write_text(content, encoding="utf-8")
                    mapping = CsvMapping.model_validate(
                        {
                            "delimiter": conf_delim,
                            "date_column": "Dato",
                            "label_column": "Arrangement",
                            "metrics": {
                                "tickets": {"column": "Billetter", "unit": "stk"}
                            },
                        }
                    )
                    obs = load_aggregated_csv(csv_path, mapping)
                    self.assertEqual(len(obs), 1)
                    self.assertEqual(obs[0].value, 150.0)

    def test_encoding_fallback(self):
        content = "Dato;Arrangement;Billetter;Omsetning\n2026-08-20;Blåbærtur;50;12500,00\n"
        encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
        mapping = CsvMapping.model_validate(
            {
                "delimiter": ";",
                "date_column": "Dato",
                "label_column": "Arrangement",
                "metrics": {
                    "tickets": {"column": "Billetter", "unit": "stk"},
                    "revenue": {"column": "Omsetning", "unit": "NOK"},
                },
            }
        )
        for enc in encodings:
            with self.subTest(encoding=enc), tempfile.TemporaryDirectory() as tmp:
                csv_path = Path(tmp) / f"test_{enc}.csv"
                csv_path.write_bytes(content.encode(enc))
                obs = load_aggregated_csv(csv_path, mapping)
                self.assertEqual(len(obs), 2)
                self.assertEqual(obs[0].label, "Blåbærtur")

    def test_date_parsing_formats(self):
        cases = [
            ("2026-02-25", date(2026, 2, 25)),
            ("25.02.2026", date(2026, 2, 25)),
            ("25/02/2026", date(2026, 2, 25)),
            ("2026-02-25 19:30:00", date(2026, 2, 25)),
            ("2026-02-25T19:30:00", date(2026, 2, 25)),
            ("2026-02-25 19:30", date(2026, 2, 25)),
            ("25.02.2026 19:30", date(2026, 2, 25)),
            ("25/02/2026 19:30:00", date(2026, 2, 25)),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(_parse_date(raw), expected)

        with self.assertRaises(DataPolicyError):
            _parse_date("ugyldig-dato")

    def test_number_parsing_variations(self):
        cases = [
            ("45500", 45500.0),
            ("45500.5", 45500.5),
            ("45 500,50", 45500.5),
            ("45\u00a0500,50", 45500.5),
            ("45\u202f500,50", 45500.5),
            ("1.200", 1200.0),
            ("185.000", 185000.0),
            ("1.200.000,50", 1200000.50),
            ("18500,-", 18500.0),
            ("18500 kr", 18500.0),
            ("18500 NOK", 18500.0),
            ("kr. 18500,-", 18500.0),
            ("kr 185.000 NOK", 185000.0),
            ("-", 0.0),
            ("–", 0.0),
            (0, 0.0),
            (150, 150.0),
            (12.5, 12.5),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(_parse_number(raw), expected)

        # Tomt felt og «N/A» skal avvises (streng validering, jf. stabiliserings-
        # runde 002 / R1). Bindestrek beholdes som «ingen verdi = 0».
        for invalid in ("", "   ", "N/A", "n/a", "ugyldig"):
            with self.subTest(raw=invalid):
                with self.assertRaises(DataPolicyError):
                    _parse_number(invalid)

    def test_room_normalization(self):
        cases = [
            ("Hovedsalen", "Hovedscenen"),
            ("Hovedscene", "Hovedscenen"),
            ("Store sal", "Hovedscenen"),
            ("Black Box", "Biscenen"),
            ("Blackbox", "Biscenen"),
            ("Biscene", "Biscenen"),
            ("Intimscene", "Intimscenen"),
            ("Intimen", "Intimscenen"),
            ("Prøvesalen", "Intimscenen"),
            ("Foajé", "Foajeen"),
            ("Foaje", "Foajeen"),
            ("Foyer", "Foajeen"),
            ("Restaurant", "Restauranten"),
            ("Spiseriet", "Restauranten"),
            ("Hovedsalen / Black Box", "Hovedscenen / Biscenen"),
            (None, None),
            ("", None),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_room(raw), expected)

    def test_ingests_reference_sample_gastroplanner_2026(self):
        mapping_path = Path("config/gastroplanner_mapping.example.yml")
        csv_path = Path("sample_data/gastroplanner_sample_2026.csv")
        mapping = load_csv_mapping(mapping_path)
        observations = load_aggregated_csv(csv_path, mapping)

        self.assertEqual(len(observations), 45)  # 9 rows * 5 metrics
        self.assertTrue(all(obs.value >= 0 for obs in observations))
        self.assertTrue(all(obs.period.year == 2026 for obs in observations))
        self.assertTrue(all(obs.source_system == "GastroPlanner" for obs in observations))
        self.assertTrue(all(obs.room in {"Foajeen", "Hovedscenen", "Biscenen", "Intimscenen"} for obs in observations))


if __name__ == "__main__":
    unittest.main()


