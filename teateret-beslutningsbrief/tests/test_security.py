import tempfile
import unittest
from pathlib import Path

from teateret_brief.security import (
    DataPolicyError,
    PathPolicyError,
    RepoPaths,
    SourcePolicy,
    SourcePolicyError,
    assert_aggregated_csv,
    is_forbidden_column_header,
    is_valid_luhn,
    is_valid_norwegian_fnr,
    mask_sensitive_error,
    redact_contact_details,
    redact_reviewer_identity,
    scan_public_artifact,
)


class RepoPathsTests(unittest.TestCase):
    def test_paths_cannot_escape_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = RepoPaths(Path(tmp))
            safe = paths.output_path("runs/test/manifest.json")
            self.assertTrue(safe.is_relative_to(Path(tmp).resolve()))

            with self.assertRaises(PathPolicyError):
                paths.output_path("../outside.txt")


class SourcePolicyTests(unittest.TestCase):
    def test_allows_approved_https_source_with_public_dns(self):
        policy = SourcePolicy(
            allowed_hosts={"example.com"},
            resolver=lambda _host: ["93.184.216.34"],
        )
        self.assertEqual(
            policy.validate("https://example.com/program").host,
            "example.com",
        )

    def test_blocks_credentials_unknown_hosts_and_private_dns(self):
        public = SourcePolicy(
            allowed_hosts={"example.com"},
            resolver=lambda _host: ["93.184.216.34"],
        )
        private = SourcePolicy(
            allowed_hosts={"example.com"},
            resolver=lambda _host: ["127.0.0.1"],
        )
        for url in (
            "http://example.com/program",
            "https://user:pass@example.com/program",
            "https://unknown.example/program",
            "https://example.com:8443/program",
        ):
            with self.subTest(url=url), self.assertRaises(SourcePolicyError):
                public.validate(url)
        with self.assertRaises(SourcePolicyError):
            private.validate("https://example.com/program")


class DataPolicyTests(unittest.TestCase):
    def test_fnr_validation_modulo_11(self):
        # Valid standard Norwegian FNR
        self.assertTrue(is_valid_norwegian_fnr("01010112377"))
        # Valid D-nummer
        self.assertTrue(is_valid_norwegian_fnr("41010112360"))
        # Invalid check digit k1 / k2
        self.assertFalse(is_valid_norwegian_fnr("01010112378"))
        self.assertFalse(is_valid_norwegian_fnr("01010112387"))
        # Invalid length or non-digits
        self.assertFalse(is_valid_norwegian_fnr("010101123"))
        self.assertFalse(is_valid_norwegian_fnr("0101011234567"))
        self.assertFalse(is_valid_norwegian_fnr("abcdefghijk"))

    def test_luhn_credit_card_validation(self):
        # Valid cards
        self.assertTrue(is_valid_luhn("4532015000000007"))
        self.assertTrue(is_valid_luhn("4532 0150 0000 0007"))
        self.assertTrue(is_valid_luhn("5105105105105100"))
        # Invalid cards
        self.assertFalse(is_valid_luhn("4532015000000008"))
        self.assertFalse(is_valid_luhn("123456"))
        self.assertFalse(is_valid_luhn("not-a-number"))

    def test_forbidden_column_headers_rejected(self):
        forbidden = [
            "kunde",
            "kundenavn",
            "kunde_navn",
            "customer_name",
            "customer",
            "guest",
            "gjest",
            "epost",
            "e-post",
            "e_post",
            "email",
            "kunde_epost",
            "kundeepost",
            "telefon",
            "mobilnummer",
            "tlf",
            "gjeste_telefon",
            "adresse",
            "kommentar",
            "notat",
            "reservasjonsnotat",
            "fritekst_kommentar",
            "fnr",
            "fødselsnummer",
            "fodselsnummer",
            "kredittkort",
            "credit_card",
        ]
        for header in forbidden:
            with self.subTest(header=header):
                self.assertTrue(is_forbidden_column_header(header))
                with self.assertRaises(DataPolicyError):
                    assert_aggregated_csv(
                        ["Dato", "Arrangement", header],
                        [["2026-08-20", "Test", "Verdi"]],
                    )

    def test_domain_whitelist_exemptions_allowed(self):
        allowed = [
            "Arrangement",
            "Arrangementsnavn",
            "arrangement_navn",
            "Rom",
            "Romnavn",
            "rom_navn",
            "Artist",
            "Artistnavn",
            "artist_navn",
            "Antall_Gjester",
            "gjester_totalt",
            "Antall_Kunder",
            "kunder_totalt",
            "Forestillingsnavn",
            "Lokalnavn",
            "Produksjonsnavn",
        ]
        for header in allowed:
            with self.subTest(header=header):
                self.assertFalse(is_forbidden_column_header(header))
                # Should not raise when passed to assert_aggregated_csv
                assert_aggregated_csv(
                    ["Dato", header, "Billetter"],
                    [["2026-08-20", "Verdi", "100"]],
                )

    def test_strict_mode_and_allowed_headers_in_assert_aggregated_csv(self):
        allowed_headers = ["Dato", "Arrangement", "Billetter", "Omsetning"]
        # Allowed set passes
        assert_aggregated_csv(
            ["Dato", "Arrangement", "Billetter"],
            [["2026-08-20", "Konsert", "50"]],
            allowed_headers=allowed_headers,
            strict=True,
        )
        # Unknown column raises in strict mode
        with self.assertRaises(DataPolicyError):
            assert_aggregated_csv(
                ["Dato", "Arrangement", "UkjentKolonne"],
                [["2026-08-20", "Konsert", "50"]],
                allowed_headers=allowed_headers,
                strict=True,
            )
        # Unknown non-PII column does not raise when strict=False
        assert_aggregated_csv(
            ["Dato", "Arrangement", "UkjentKolonne"],
            [["2026-08-20", "Konsert", "50"]],
            allowed_headers=allowed_headers,
            strict=False,
        )

    def test_cell_level_pii_rejection(self):
        cases = [
            ["2026-08-01", "Konsert", "kontakt: booking@example.com"],
            ["2026-08-01", "Konsert", "Ring 999 88 777"],
            ["2026-08-01", "Konsert", "VIP tlf: +47 99 88 77 66"],
            ["2026-08-01", "Konsert", "FNR: 01029012345"],
            ["2026-08-01", "Konsert", "Kortref: 4532 0150 1234 5678"],
        ]
        for row in cases:
            with self.subTest(row=row), self.assertRaises(DataPolicyError):
                assert_aggregated_csv(
                    ["Dato", "Arrangement", "Info"],
                    [row],
                )

    def test_public_artist_names_are_allowed(self):
        assert_aggregated_csv(
            ["date", "event", "revenue_nok"],
            [["2026-08-01", "Offentlig artistnavn: Amund Mathisen // Teateret", "1000"]],
        )
        self.assertEqual(scan_public_artifact("Artist: Tone Damli"), [])

    def test_reviewer_identity_redaction_word_boundary(self):
        # Substrings inside words should NOT be redacted
        self.assertEqual(
            redact_reviewer_identity("Danseforestilling i Januar", "Dan"),
            "Danseforestilling i Januar",
        )
        self.assertEqual(
            redact_reviewer_identity("Opplevelsen i Januar var herlig", "Jan"),
            "Opplevelsen i Januar var herlig",
        )
        self.assertEqual(
            redact_reviewer_identity("Performance med publikum", "Per"),
            "Performance med publikum",
        )
        # Standalone name tokens should be redacted
        self.assertEqual(
            redact_reviewer_identity("Jan mente opplevelsen var fantastisk", "Jan"),
            "[ANMELDER] mente opplevelsen var fantastisk",
        )
        self.assertEqual(
            redact_reviewer_identity("Sitat fra Kari Nordmann: Flott show!", "Kari Nordmann"),
            "Sitat fra [ANMELDER] [ANMELDER]: Flott show!",
        )

    def test_scan_and_redact_contact_details(self):
        sample = "Epost: user@test.no, Tlf: 91234567, FNR: 01029012345, Kort: 4532 0150 1234 5678"
        findings = scan_public_artifact(sample)
        self.assertIn("email", findings)
        self.assertIn("phone", findings)
        self.assertIn("fnr", findings)
        self.assertIn("credit_card", findings)

        redacted, findings_list = redact_contact_details(sample)
        self.assertIn("[MASKERT_EPOST]", redacted)
        self.assertIn("[MASKERT_TELEFON]", redacted)
        self.assertIn("[MASKERT_FNR]", redacted)
        self.assertIn("[MASKERT_KORT]", redacted)
        self.assertNotIn("user@test.no", redacted)
        self.assertNotIn("91234567", redacted)

    def test_mask_sensitive_error(self):
        err = "Feil oppsto for bruker test@example.com med tlf 99887766 og fnr 01029012345 og kort 4532 0150 1234 5678"
        masked = mask_sensitive_error(err)
        self.assertIn("[MASKERT_EPOST]", masked)
        self.assertIn("[MASKERT_TELEFON]", masked)
        self.assertIn("[MASKERT_FNR]", masked)
        self.assertIn("[MASKERT_KORT]", masked)
        self.assertNotIn("test@example.com", masked)
        self.assertNotIn("99887766", masked)


if __name__ == "__main__":
    unittest.main()


