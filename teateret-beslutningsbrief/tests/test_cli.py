import unittest
from pathlib import Path

from teateret_brief.cli import main


class CliTests(unittest.TestCase):
    def test_live_mode_is_disabled_by_runtime_configuration(self):
        root = Path(__file__).resolve().parents[1]
        with self.assertRaisesRegex(SystemExit, "Live-modus er deaktivert"):
            main(
                [
                    "--mode",
                    "live",
                    "--repo-root",
                    str(root),
                    "--allow-live-network",
                    "--allow-live-model",
                ]
            )

    def test_demo_mode_with_google_flags_succeeds(self):
        import tempfile

        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run_id = f"test-cli-demo-{Path(tmp).name}"
            exit_code = main(
                [
                    "--mode",
                    "demo",
                    "--repo-root",
                    str(root),
                    "--run-id",
                    run_id,
                    "--google-places",
                    "--google-trends",
                    "--schema-events",
                ]
            )
            self.assertEqual(exit_code, 0)
            run_dir = root / "runs" / run_id
            self.assertTrue((run_dir / "manifest.json").exists())
            self.assertTrue((run_dir / "brief.md").exists())
            self.assertTrue((run_dir / "brief.html").exists())
            self.assertTrue((run_dir / "email.txt").exists())
            brief_content = (run_dir / "brief.md").read_text(encoding="utf-8")
            self.assertIn("Gjestevurderinger og omdømme (Google)", brief_content)
            self.assertIn("Markedssignaler og trender", brief_content)


if __name__ == "__main__":
    unittest.main()
