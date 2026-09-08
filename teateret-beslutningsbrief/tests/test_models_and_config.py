import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from teateret_brief.config import load_sources
from teateret_brief.models import AnalysisOutput, ReaderOutput, Recommendation, Signal


class IdentifierTests(unittest.TestCase):
    def test_duplicate_source_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.yml"
            path.write_text(
                """sources:
  - {id: same, name: A, url: 'https://example.com/a', region: local, topic: events}
  - {id: same, name: B, url: 'https://example.com/b', region: local, topic: events}
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Kilde-ID-er"):
                load_sources(path)

    def test_duplicate_signal_and_recommendation_ids_are_rejected(self):
        signal = Signal(
            id="same",
            claim="Signal",
            source_ids=["source-1"],
            geography="Kristiansand",
            confidence="confirmed",
        )
        with self.assertRaises(ValidationError):
            ReaderOutput(signals=[signal, signal])

        recommendation = Recommendation(
            id="same",
            action="Vurder tiltak",
            rationale="Kilden viser et signal",
            source_ids=["source-1"],
            expected_value="Læring",
            effort="low",
        )
        with self.assertRaises(ValidationError):
            AnalysisOutput(recommendations=[recommendation, recommendation])


if __name__ == "__main__":
    unittest.main()
