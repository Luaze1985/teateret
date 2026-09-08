import json
import tempfile
import unittest
from pathlib import Path

from teateret_brief.models import (
    AnalysisOutput,
    ReaderOutput,
    Recommendation,
    Signal,
    SourceDocument,
    SourceSpec,
    VerificationOutput,
)
from teateret_brief.pipeline import BriefPipeline, PipelineSettings


class FakeFetcher:
    def fetch(self, source):
        return SourceDocument(
            source_id=source.id,
            url=str(source.url),
            title="Nytt arrangement",
            published_at="2026-08-18T10:00:00+02:00",
            fetched_at="2026-08-19T09:00:00+02:00",
            text="Et nytt lokalt arrangement er annonsert.",
            content_sha256="a" * 64,
            extractor="fixture",
        )


class FakeRoles:
    call_count = 0

    def read_sources(self, documents):
        self.call_count += 1
        return ReaderOutput(
            signals=[
                Signal(
                    id="signal-1",
                    claim="Nytt lokalt arrangement er annonsert.",
                    source_ids=[documents[0].source_id],
                    geography="Kristiansand",
                    confidence="confirmed",
                )
            ]
        )

    def analyze(self, signals, observations, decision_questions, **kwargs):
        self.call_count += 1
        self.decision_questions = decision_questions
        return AnalysisOutput(
            recommendations=[
                Recommendation(
                    id="rec-1",
                    action="Vurder en tydelig kampanje mot det lokale publikummet.",
                    rationale="Det finnes et ferskt lokalt signal.",
                    source_ids=[signals[0].source_ids[0]],
                    expected_value="Teste lokal interesse",
                    effort="low",
                )
            ]
        )

    def verify(self, signals, recommendations, documents, decision_questions):
        self.call_count += 1
        self.verified_questions = decision_questions
        return VerificationOutput(
            status="pass",
            approved_recommendation_ids=[recommendations[0].id],
            warnings=[],
        )


class PipelineTests(unittest.TestCase):
    def test_fixture_run_writes_three_consistent_outputs_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            roles = FakeRoles()
            pipeline = BriefPipeline(
                root,
                PipelineSettings(
                    max_model_calls=4,
                    max_retries=1,
                    decision_questions=["Hva bør vi gjøre?"],
                ),
                FakeFetcher(),
                roles,
            )
            result = pipeline.run(
                sources=[
                    SourceSpec(
                        id="source-1",
                        name="Eksempelkilde",
                        url="https://example.com/program",
                        region="local",
                        topic="events",
                    )
                ],
                observations=[],
                run_id="test-run",
            )

            self.assertEqual(result.status, "completed")
            self.assertEqual(roles.call_count, 3)
            self.assertEqual(roles.decision_questions, ["Hva bør vi gjøre?"])
            self.assertEqual(roles.verified_questions, ["Hva bør vi gjøre?"])
            for filename in ("brief.md", "brief.html", "email.txt", "manifest.json"):
                self.assertTrue((result.run_dir / filename).exists(), filename)
            markdown = (result.run_dir / "brief.md").read_text(encoding="utf-8")
            html = (result.run_dir / "brief.html").read_text(encoding="utf-8")
            email = (result.run_dir / "email.txt").read_text(encoding="utf-8")
            for output in (markdown, html, email):
                self.assertIn("test-run", output)
                self.assertIn("rec-1", output)
                self.assertIn("source-1", output)
                self.assertIn("UTKAST", output)
            self.assertIn("Hvorfor:", email)
            self.assertIn("Verdi/innsats", email)
            manifest = json.loads(
                (result.run_dir / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["call_count"], 3)
            self.assertEqual(manifest["source_records"][0]["source_id"], "source-1")
            self.assertEqual(manifest["decision_questions"], ["Hva bør vi gjøre?"])
            self.assertEqual(len(manifest["decision_questions_sha256"]), 64)
            self.assertIn("https://example.com/program", markdown)
            self.assertIn("https://example.com/program", html)
            self.assertIn("https://example.com/program", email)
            self.assertNotIn("Et nytt lokalt arrangement", json.dumps(manifest))

    def test_all_source_failures_block_customer_facing_outputs(self):
        class BrokenFetcher:
            def fetch(self, source):
                raise RuntimeError("source unavailable")

        with tempfile.TemporaryDirectory() as tmp:
            pipeline = BriefPipeline(
                Path(tmp),
                PipelineSettings(decision_questions=["Hva bør vi gjøre?"]),
                BrokenFetcher(),
                FakeRoles(),
            )
            result = pipeline.run(
                sources=[
                    SourceSpec(
                        id="source-1",
                        name="Eksempelkilde",
                        url="https://example.com/program",
                        region="local",
                        topic="events",
                    )
                ],
                observations=[],
                run_id="blocked-run",
            )
            self.assertEqual(result.status, "blocked")
            self.assertTrue((result.run_dir / "manifest.json").exists())
            self.assertTrue((result.run_dir / "errors.json").exists())
            self.assertFalse((result.run_dir / "brief.md").exists())

    def test_dot_run_ids_are_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = BriefPipeline(
                Path(tmp),
                PipelineSettings(decision_questions=["Hva bør vi gjøre?"]),
                FakeFetcher(),
                FakeRoles(),
            )
            for run_id in (".", "..", "-bad", "bad-"):
                with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                    pipeline.run([], [], run_id=run_id)
            self.assertFalse((Path(tmp) / "runs").exists())

    def test_late_write_failure_cleans_customer_facing_outputs(self):
        class OneTimeManifestFailurePipeline(BriefPipeline):
            failed = False

            def _write_json(self, path, payload):
                if path.name == "manifest.json" and not self.failed:
                    self.failed = True
                    raise OSError("simulated disk failure with booking@example.com")
                return super()._write_json(path, payload)

        with tempfile.TemporaryDirectory() as tmp:
            pipeline = OneTimeManifestFailurePipeline(
                Path(tmp),
                PipelineSettings(decision_questions=["Hva bør vi gjøre?"]),
                FakeFetcher(),
                FakeRoles(),
            )
            result = pipeline.run(
                [
                    SourceSpec(
                        id="source-1",
                        name="Eksempelkilde",
                        url="https://example.com/program",
                        region="local",
                        topic="events",
                    )
                ],
                [],
                run_id="late-failure",
            )
            self.assertEqual(result.status, "blocked")
            self.assertFalse((result.run_dir / "brief.md").exists())
            errors = (result.run_dir / "errors.json").read_text(encoding="utf-8")
            self.assertNotIn("booking@example.com", errors)


if __name__ == "__main__":
    unittest.main()
