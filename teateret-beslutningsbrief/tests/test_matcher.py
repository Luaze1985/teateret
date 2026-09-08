import unittest
from datetime import date
from pathlib import Path

from teateret_brief.matcher import (
    EventMatcher,
    MatchingReport,
    MatchReport,
    PublicEvent,
    load_public_events,
    normalize_title,
)
from teateret_brief.models import SalesObservation


class MatcherTests(unittest.TestCase):
    def setUp(self):
        self.events = [
            PublicEvent(
                event_id="EVT-260225",
                date=date(2026, 2, 25),
                title="Speed date 40–59",
                room="Foajeen",
                capacity=50,
            ),
            PublicEvent(
                event_id="EVT-260313",
                date=date(2026, 3, 13),
                title="Svanesjøen (Etoile Ballet)",
                room="Hovedscenen",
                capacity=400,
            ),
            PublicEvent(
                event_id="EVT-260717",
                date=date(2026, 7, 17),
                title="Sommerstandup med Fire halvkjente fjes",
                room="Hovedscenen",
                capacity=400,
            ),
            PublicEvent(
                event_id="EVT-250208",
                date=date(2025, 2, 8),
                title="Kokosbananas – Det store showet",
                room="Hovedscenen",
                capacity=400,
            ),
            PublicEvent(
                event_id="EVT-250208-2",
                date=date(2025, 2, 8),
                title="Drag Bonanza 3",
                room="Biscenen",
                capacity=148,
            ),
            PublicEvent(
                event_id="EVT-260820",
                date=date(2026, 8, 20),
                end_date=date(2026, 8, 22),
                title="Kristiansand Jazzfestival 26 (AiR m.fl.)",
                room="Biscenen",
                capacity=148,
            ),
        ]
        self.matcher = EventMatcher(self.events)

    # -----------------------------------------------------------------------
    # Level 1 Matching Tests
    # -----------------------------------------------------------------------
    def test_level_1_explicit_id_match(self):
        obs = SalesObservation(
            period=date(2026, 2, 25),
            label="Ulik tittel i kasse",
            metric="revenue_nok",
            value=18500.0,
            unit="NOK",
            event_id="EVT-260225",
        )
        res = self.matcher.match(obs)
        self.assertEqual(res.match_status, "matched")
        self.assertEqual(res.match_level, "level_1_id")
        self.assertEqual(res.matched_event_title, "Speed date 40–59")
        self.assertIn("EVT-260225", res.reason)

    def test_level_1_case_insensitivity(self):
        obs = SalesObservation(
            period=date(2026, 2, 25),
            label="Kasselabel",
            metric="revenue_nok",
            value=18500.0,
            unit="NOK",
            event_id="evt-260225",
        )
        res = self.matcher.match(obs)
        self.assertEqual(res.match_status, "matched")
        self.assertEqual(res.match_level, "level_1_id")
        self.assertEqual(res.matched_event_title, "Speed date 40–59")

    def test_level_1_id_takes_priority_over_disparate_title(self):
        obs = SalesObservation(
            period=date(2026, 3, 13),
            label="Helt feil tittel her",
            metric="tickets_sold",
            value=380.0,
            unit="billetter",
            event_id="EVT-260313",
        )
        res = self.matcher.match(obs)
        self.assertEqual(res.match_status, "matched")
        self.assertEqual(res.match_level, "level_1_id")
        self.assertEqual(res.matched_event_title, "Svanesjøen (Etoile Ballet)")

    # -----------------------------------------------------------------------
    # Level 2 Matching Tests
    # -----------------------------------------------------------------------
    def test_level_2_title_date_room_match(self):
        obs = SalesObservation(
            period=date(2026, 7, 17),
            label="Sommerstandup",
            metric="tickets_sold",
            value=290.0,
            unit="billetter",
            room="Hovedscenen",
        )
        res = self.matcher.match(obs)
        self.assertEqual(res.match_status, "matched")
        self.assertEqual(res.match_level, "level_2_title_date_room")
        self.assertEqual(res.matched_event_title, "Sommerstandup med Fire halvkjente fjes")

    def test_level_2_exact_title(self):
        obs = SalesObservation(
            period=date(2026, 2, 25),
            label="Speed date 40–59",
            metric="tickets_sold",
            value=40.0,
            unit="stk",
            room="Foajeen",
        )
        res = self.matcher.match(obs)
        self.assertEqual(res.match_status, "matched")
        self.assertEqual(res.match_level, "level_2_title_date_room")
        self.assertEqual(res.matched_event_title, "Speed date 40–59")

    def test_level_2_norwegian_special_characters(self):
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
            room="Intimscenen",
        )
        res = matcher.match(obs)
        self.assertEqual(res.match_status, "matched")
        self.assertEqual(res.match_level, "level_2_title_date_room")

    def test_level_2_synonym_resolution(self):
        obs = SalesObservation(
            period=date(2026, 8, 20),
            label="Jazzfestival",
            metric="tickets_sold",
            value=140.0,
            unit="billetter",
            room="Biscenen",
        )
        res = self.matcher.match(obs)
        self.assertEqual(res.match_status, "matched")
        self.assertEqual(res.match_level, "level_2_title_date_room")
        self.assertIn("Kristiansand Jazzfestival", res.matched_event_title or "")

    def test_level_2_room_aliases(self):
        obs = SalesObservation(
            period=date(2026, 7, 17),
            label="Sommerstandup med Fire halvkjente fjes",
            metric="tickets_sold",
            value=290.0,
            unit="billetter",
            room="Store sal",  # Alias for Hovedscenen
        )
        res = self.matcher.match(obs)
        self.assertEqual(res.match_status, "matched")
        self.assertEqual(res.match_level, "level_2_title_date_room")

    def test_level_2_room_disambiguation(self):
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
        res_hoved = self.matcher.match(obs_hoved)
        res_bi = self.matcher.match(obs_bi)

        self.assertEqual(res_hoved.matched_event_title, "Kokosbananas – Det store showet")
        self.assertEqual(res_bi.matched_event_title, "Drag Bonanza 3")

    def test_level_2_missing_room_matches_unique_title(self):
        obs = SalesObservation(
            period=date(2026, 7, 17),
            label="Sommerstandup med Fire halvkjente fjes",
            metric="tickets_sold",
            value=290.0,
            unit="billetter",
            room=None,
        )
        res = self.matcher.match(obs)
        self.assertEqual(res.match_status, "matched")
        self.assertEqual(res.match_level, "level_2_title_date_room")

    # -----------------------------------------------------------------------
    # Level 3 Proximity Matching Tests
    # -----------------------------------------------------------------------
    def test_level_3_proximity_needs_review(self):
        obs = SalesObservation(
            period=date(2026, 3, 13),
            label="Restaurantkveld uten tittelmatch",
            metric="table_reservations",
            value=120.0,
            unit="bord",
        )
        res = self.matcher.match(obs)
        self.assertEqual(res.match_status, "needs_review")
        self.assertEqual(res.match_level, "level_3_proximity")
        self.assertEqual(res.matched_event_title, "Svanesjøen (Etoile Ballet)")
        self.assertIn("Dato-nærhet", res.reason)

    def test_level_3_multi_event_date_unmatched_without_title(self):
        obs = SalesObservation(
            period=date(2025, 2, 8),
            label="Generell Barinntekt Uten Match",
            metric="revenue_nok",
            value=15000.0,
            unit="NOK",
        )
        res = self.matcher.match(obs)
        self.assertEqual(res.match_status, "unmatched")
        self.assertEqual(res.match_level, "none")
        self.assertIn("Flere arrangementer", res.reason)

    # -----------------------------------------------------------------------
    # Unmatched and Edge Cases
    # -----------------------------------------------------------------------
    def test_unmatched_when_no_event_on_date(self):
        obs = SalesObservation(
            period=date(2026, 1, 1),
            label="Ukjent Nyttårsfest",
            metric="revenue_nok",
            value=5000.0,
            unit="NOK",
        )
        res = self.matcher.match(obs)
        self.assertEqual(res.match_status, "unmatched")
        self.assertEqual(res.match_level, "none")
        self.assertIn("Ingen offentlige arrangementer", res.reason)

    def test_empty_observations_batch(self):
        report = self.matcher.evaluate_all([])
        self.assertEqual(report.total_observations, 0)
        self.assertEqual(report.matched_count, 0)
        self.assertEqual(report.needs_review_count, 0)
        self.assertEqual(report.unmatched_count, 0)
        self.assertEqual(report.match_rate_percent, 0.0)
        self.assertEqual(report.results, [])

    def test_batch_evaluation_metrics_and_deduplication(self):
        observations = [
            SalesObservation(
                period=date(2026, 2, 25),
                label="Speed date 40–59",
                metric="tickets_sold",
                value=40.0,
                unit="stk",
                event_id="EVT-260225",
            ),
            SalesObservation(
                period=date(2026, 2, 25),
                label="Speed date 40–59",
                metric="revenue_nok",
                value=18500.0,
                unit="NOK",
                event_id="EVT-260225",
            ),
            SalesObservation(
                period=date(2026, 3, 13),
                label="Uavstemt bordbooking",
                metric="table_reservations",
                value=50.0,
                unit="bord",
            ),
            SalesObservation(
                period=date(2026, 1, 1),
                label="Utenfor program",
                metric="revenue_nok",
                value=2000.0,
                unit="NOK",
            ),
        ]
        report = self.matcher.evaluate_all(observations)
        self.assertEqual(report.total_observations, 3)  # Dedup row 1 & 2
        self.assertEqual(report.matched_count, 1)
        self.assertEqual(report.needs_review_count, 1)
        self.assertEqual(report.unmatched_count, 1)
        self.assertAlmostEqual(report.match_rate_percent, 33.3, places=1)

    def test_match_batch_alias(self):
        obs = [
            SalesObservation(
                period=date(2026, 2, 25),
                label="Speed date 40–59",
                metric="revenue_nok",
                value=18500.0,
                unit="NOK",
                event_id="EVT-260225",
            )
        ]
        rep1 = self.matcher.evaluate_all(obs)
        rep2 = self.matcher.match_batch(obs)
        self.assertEqual(rep1.total_observations, rep2.total_observations)
        self.assertEqual(rep1.matched_count, rep2.matched_count)
        self.assertEqual(rep1.match_rate_percent, rep2.match_rate_percent)

    def test_match_report_alias(self):
        self.assertIs(MatchReport, MatchingReport)

    # -----------------------------------------------------------------------
    # Public Events Dataset Loader Tests
    # -----------------------------------------------------------------------
    def test_load_public_events_from_markdown(self):
        events = load_public_events()
        self.assertGreaterEqual(len(events), 129)
        sample = next((e for e in events if e.date == date(2026, 3, 13)), None)
        self.assertIsNotNone(sample)
        self.assertEqual(sample.room, "Hovedscenen")
        self.assertEqual(sample.capacity, 400)

    def test_load_public_events_multi_day_range(self):
        events = load_public_events()
        demokrati = next((e for e in events if "Demokratiuka" in e.title), None)
        self.assertIsNotNone(demokrati)
        self.assertEqual(demokrati.date, date(2026, 5, 2))
        self.assertEqual(demokrati.end_date, date(2026, 5, 8))

    def test_load_public_events_capacity_inference(self):
        events = load_public_events()
        hoved = next((e for e in events if e.room == "Hovedscenen"), None)
        bi = next((e for e in events if e.room == "Biscenen"), None)
        intim = next((e for e in events if e.room == "Intimscenen"), None)

        self.assertIsNotNone(hoved)
        self.assertEqual(hoved.capacity, 400)
        self.assertIsNotNone(bi)
        self.assertEqual(bi.capacity, 148)
        self.assertIsNotNone(intim)
        self.assertEqual(intim.capacity, 90)

    def test_load_public_events_nonexistent_file(self):
        events = load_public_events(Path("nonexistent/path/events.md"))
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
