import unittest
from datetime import date

from teateret_brief.analytics import _python_summary
from teateret_brief.models import SalesObservation


def observation(period, label, value):
    return SalesObservation(
        period=date.fromisoformat(period),
        label=label,
        metric="reservations",
        value=value,
        unit="count",
    )


class AnalyticsTests(unittest.TestCase):
    def test_preserves_event_ranking_and_period_change(self):
        result = _python_summary(
            [
                observation("2026-08-01", "Jazz", 100),
                observation("2026-08-01", "Humor", 50),
                observation("2026-08-08", "Jazz", 120),
                observation("2026-08-08", "Humor", 60),
            ],
            backend="test",
        )

        self.assertEqual(result["totals"][0]["value"], 330)
        self.assertEqual(result["by_label"][0]["label"], "Jazz")
        self.assertEqual(result["by_label"][0]["rank"], 1)
        self.assertEqual(result["by_period"][0]["value"], 150)
        self.assertEqual(result["by_period"][1]["value"], 180)
        self.assertEqual(result["by_period"][1]["change_percent"], 20.0)

    def test_zero_previous_period_has_no_misleading_percentage(self):
        result = _python_summary(
            [
                observation("2026-08-01", "Jazz", 0),
                observation("2026-08-08", "Jazz", 10),
            ],
            backend="test",
        )
        self.assertIsNone(result["by_period"][1]["change_percent"])


if __name__ == "__main__":
    unittest.main()
