import ipaddress
import re
import socket
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
    assert_review_limit,
    is_forbidden_column_header,
    is_valid_luhn,
    is_valid_norwegian_fnr,
    mask_sensitive_error,
    redact_contact_details,
    redact_reviewer_identity,
    safe_error_summary,
    scan_public_artifact,
)


def _generate_valid_fnr(day: int, month: int, year_2digit: int, individual: int) -> str | None:
    """Helper to compute valid 11-digit Modulo 11 FNR."""
    d_str = f"{day:02d}{month:02d}{year_2digit:02d}{individual:03d}"
    digits = [int(c) for c in d_str]
    w1 = [3, 7, 6, 1, 8, 9, 4, 5, 2]
    s1 = sum(w * d for w, d in zip(w1, digits))
    r1 = s1 % 11
    k1 = 0 if r1 == 0 else (11 - r1)
    if k1 == 10:
        return None

    digits_with_k1 = digits + [k1]
    w2 = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    s2 = sum(w * d for w, d in zip(w2, digits_with_k1))
    r2 = s2 % 11
    k2 = 0 if r2 == 0 else (11 - r2)
    if k2 == 10:
        return None

    return f"{d_str}{k1}{k2}"


def _generate_valid_luhn(prefix: str, length: int) -> str:
    """Helper to compute valid Luhn number of given length with prefix."""
    needed = length - len(prefix) - 1
    base = prefix + "0" * needed
    digits = [int(c) for c in base]
    checksum = 0
    # calculate checksum for base digits shifted by 1 (since check digit will be at index 0 reversed)
    for i, d in enumerate(digits[::-1]):
        # check digit will be at index 0 of reversed, so digits[0] of reversed is at index 1 of full reversed
        if (i + 1) % 2 == 1:
            d_val = d * 2
            if d_val > 9:
                d_val -= 9
            checksum += d_val
        else:
            checksum += d
    check_digit = (10 - (checksum % 10)) % 10
    return base + str(check_digit)


class TestFNRFuzzingAdversarial(unittest.TestCase):
    """Stress-test and fuzz Norwegian FNR and D-number validation & scanning."""

    def test_modulo11_algorithmic_coverage(self):
        # Generate and verify a batch of valid FNRs
        valid_count = 0
        for day in [1, 15, 31]:
            for month in [1, 6, 12]:
                for indiv in range(100, 200):
                    fnr = _generate_valid_fnr(day, month, 90, indiv)
                    if fnr:
                        self.assertTrue(is_valid_norwegian_fnr(fnr), f"Failed for valid FNR: {fnr}")
                        self.assertEqual(len(fnr), 11)
                        valid_count += 1
        self.assertGreater(valid_count, 50, "Should generate and test at least 50 valid FNRs")

    def test_d_number_validation(self):
        # D-numbers have day + 40 (41 to 71)
        valid_d_count = 0
        for day in [41, 55, 71]:
            for month in [1, 6, 12]:
                for indiv in range(100, 200):
                    dfnr = _generate_valid_fnr(day, month, 85, indiv)
                    if dfnr:
                        self.assertTrue(is_valid_norwegian_fnr(dfnr), f"Failed for valid D-number: {dfnr}")
                        valid_d_count += 1
        self.assertGreater(valid_d_count, 15, "Should generate and test at least 15 valid D-numbers")

    def test_h_number_validation(self):
        # H-numbers have day + 80 or month + 20
        valid_h_count = 0
        for day in [81, 85, 91]:
            for month in [1, 5, 12]:
                for indiv in range(100, 150):
                    hfnr = _generate_valid_fnr(day, month, 95, indiv)
                    if hfnr:
                        self.assertTrue(is_valid_norwegian_fnr(hfnr), f"Failed for valid H-number: {hfnr}")
                        valid_h_count += 1
        self.assertGreater(valid_h_count, 5)

    def test_invalid_fnrs_rejected(self):
        # Corrupted k1 / k2
        valid = "01010112377"
        self.assertTrue(is_valid_norwegian_fnr(valid))
        # Corrupt last digit
        for bad_digit in range(10):
            if bad_digit != 7:
                corrupted = valid[:10] + str(bad_digit)
                self.assertFalse(is_valid_norwegian_fnr(corrupted), f"Corrupted last digit {corrupted} accepted")
        # Corrupt second to last digit
        for bad_digit in range(10):
            if bad_digit != 7:
                corrupted = valid[:9] + str(bad_digit) + valid[10]
                self.assertFalse(is_valid_norwegian_fnr(corrupted), f"Corrupted k1 {corrupted} accepted")

        # Impossible calendar days/months
        self.assertFalse(is_valid_norwegian_fnr("00010112345"))  # Day 0
        self.assertFalse(is_valid_norwegian_fnr("32010112345"))  # Day 32
        self.assertFalse(is_valid_norwegian_fnr("72010112345"))  # Day 72
        self.assertFalse(is_valid_norwegian_fnr("92010112345"))  # Day 92
        self.assertFalse(is_valid_norwegian_fnr("01000112345"))  # Month 0
        self.assertFalse(is_valid_norwegian_fnr("01130112345"))  # Month 13
        self.assertFalse(is_valid_norwegian_fnr("01330112345"))  # Month 33
        self.assertFalse(is_valid_norwegian_fnr("01530112345"))  # Month 53

        # Length and type checks
        self.assertFalse(is_valid_norwegian_fnr(""))
        self.assertFalse(is_valid_norwegian_fnr("010101"))
        self.assertFalse(is_valid_norwegian_fnr("010101123456"))
        self.assertFalse(is_valid_norwegian_fnr("0101011234a"))
        self.assertFalse(is_valid_norwegian_fnr(None))

    def test_fnr_regex_detection_and_formats(self):
        cases = [
            "01010112377",
            "010101 12377",
            "010101-12377",
            "010101 123 77",
            "010101-123-77",
            "Fødselsnummer: 010101-12377 i notatfelt",
            "Gjest har D-nr 410101 12373",
        ]
        for c in cases:
            with self.subTest(case=c):
                findings = scan_public_artifact(c)
                self.assertIn("fnr", findings, f"FNR scanner missed formatted case: {c}")

    def test_fnr_false_positive_resistance(self):
        # Dates and normal numbers should NOT trigger FNR detection
        clean_cases = [
            "Dato: 2026-08-20",
            "Forestillingsdato: 20.08.2026",
            "Transaksjon: 20260820-9999",
            "Ordreref: REF-98765432",
            "Omsetning: 45 500 NOK",
            "Billettnr: 123456",
            "Klokkeslett: 19:30:00",
        ]
        for c in clean_cases:
            with self.subTest(case=c):
                findings = scan_public_artifact(c)
                self.assertNotIn("fnr", findings, f"FNR scanner had false positive on: {c}")


class TestCreditCardFuzzingAdversarial(unittest.TestCase):
    """Stress-test and fuzz Luhn algorithm and credit card pattern scanning."""

    def test_luhn_across_card_schemes(self):
        # Visa 16-digit
        visa = _generate_valid_luhn("4", 16)
        self.assertTrue(is_valid_luhn(visa))
        self.assertTrue(is_valid_luhn(f"{visa[:4]} {visa[4:8]} {visa[8:12]} {visa[12:]}"))
        self.assertTrue(is_valid_luhn(f"{visa[:4]}-{visa[4:8]}-{visa[8:12]}-{visa[12:]}"))

        # Mastercard 16-digit (51-55)
        for prefix in ["51", "52", "53", "54", "55"]:
            mc = _generate_valid_luhn(prefix, 16)
            self.assertTrue(is_valid_luhn(mc), f"Failed for valid MC: {mc}")

        # Amex 15-digit (34, 37)
        for prefix in ["34", "37"]:
            amex = _generate_valid_luhn(prefix, 15)
            self.assertTrue(is_valid_luhn(amex), f"Failed for valid Amex: {amex}")

    def test_luhn_single_digit_and_transposition_errors(self):
        valid = "4532015000000007"
        self.assertTrue(is_valid_luhn(valid))

        # Single digit change must fail
        for i in range(len(valid)):
            orig_digit = int(valid[i])
            for new_digit in range(10):
                if new_digit != orig_digit:
                    mutated = valid[:i] + str(new_digit) + valid[i+1:]
                    self.assertFalse(is_valid_luhn(mutated), f"Luhn accepted single mutation: {mutated}")

        # Adjacent digit transposition must fail (except 09/90 which both sum to 9)
        for i in range(len(valid) - 1):
            if valid[i] != valid[i+1] and set(valid[i:i+2]) != {"0", "9"}:
                transposed = valid[:i] + valid[i+1] + valid[i] + valid[i+2:]
                self.assertFalse(is_valid_luhn(transposed), f"Luhn accepted transposition: {transposed}")

    def test_credit_card_scanner_and_redaction(self):
        cards = [
            "4532015000000007",
            "4532 0150 0000 0007",
            "4532-0150-0000-0007",
            "5105 1051 0510 5100",
            "3782 822463 10005",
            "6011 1111 1111 1117",
        ]
        for card in cards:
            text = f"Betalt med kort: {card} ref OK"
            findings = scan_public_artifact(text)
            self.assertIn("credit_card", findings, f"Scanner missed card: {card}")
            redacted, _ = redact_contact_details(text)
            self.assertNotIn(card, redacted)
            self.assertIn("[MASKERT_KORT]", redacted)


class TestObfuscatedPIIAdversarial(unittest.TestCase):
    """Stress-test obfuscated emails, phone numbers, and cell-level blocking."""

    def test_phone_number_variations_detected(self):
        phones = [
            "+47 91234567",
            "+47 91 23 45 67",
            "+47 912 34 567",
            "0047 91234567",
            "0047 91 23 45 67",
            "(+47) 91234567",
            "(+47) 91 23 45 67",
            "(+47) 912 34 567",
            "91234567",
            "91 23 45 67",
            "912 34 567",
            "41234567",
            "41 23 45 67",
            "412 34 567",
            "22334455",
            "22 33 44 55",
            "38000000",
        ]
        for phone in phones:
            with self.subTest(phone=phone):
                sample = f"Kontakt kunden på {phone} snarest."
                findings = scan_public_artifact(sample)
                self.assertIn("phone", findings, f"Phone scanner failed for: {phone}")

                redacted, _ = redact_contact_details(sample)
                self.assertIn("[MASKERT_TELEFON]", redacted)

    def test_email_variations_detected(self):
        emails = [
            "test@example.com",
            "user.name+tag@sub.domain.no",
            "TEST_USER@GMAIL.COM",
            "ola.nordmann@teateret.no",
            "booking@restaurant.org",
        ]
        for email in emails:
            with self.subTest(email=email):
                sample = f"E-post sendt til {email} vedrørende bord."
                findings = scan_public_artifact(sample)
                self.assertIn("email", findings, f"Email scanner failed for: {email}")

                redacted, _ = redact_contact_details(sample)
                self.assertNotIn(email, redacted)
                self.assertIn("[MASKERT_EPOST]", redacted)

    def test_assert_aggregated_csv_blocks_pii_in_rows(self):
        bad_rows = [
            ["2026-08-20", "Konsert", "Hovedscenen", "Bestilt av: amir@teateret.no"],
            ["2026-08-20", "Konsert", "Hovedscenen", "tlf 99 88 77 66"],
            ["2026-08-20", "Konsert", "Hovedscenen", "Fødselsnr: 010101-12377"],
            ["2026-08-20", "Konsert", "Hovedscenen", "Kort 4532 0150 0000 0007"],
        ]
        for row in bad_rows:
            with self.subTest(row=row):
                with self.assertRaises(DataPolicyError):
                    assert_aggregated_csv(
                        ["Dato", "Arrangement", "Rom", "Notater"],
                        [row],
                    )


class TestHeaderBlacklistAndBypasses(unittest.TestCase):
    """Stress-test casing, compound headers, Norwegian letters, and delimiters."""

    def test_header_casing_and_separators(self):
        variants = [
            "KUNDE",
            "Kunde",
            "kUnDe",
            "KUNDE_NAVN",
            "kunde_navn",
            "kunde-navn",
            "kunde.navn",
            "kunde navn",
            "Kunde_Epost",
            "kundeepost",
            "KUNDE_EPOST",
            "Gjestenavn",
            "Gjeste_Navn",
            "GJESTER",
            "Notatfelt",
            "Ordrenotat",
            "Reservasjonsnotat",
            "Kommentarfelt",
            "Fritekst_Notat",
            "Kundetelefon",
            "Mobil_Nummer",
            "TLF_NR",
            "Fødselsnummer",
            "fodselsnummer",
            "FØDSELSNUMMER",
            "Kredittkort_Nr",
            "Credit_Card_Number",
            "Personnummer",
            "Postadresse",
            "Gateadresse",
            "Brukernavn",
            "Passord",
            "Spesialønske",
            "Allergier",
        ]
        for header in variants:
            with self.subTest(header=header):
                self.assertTrue(
                    is_forbidden_column_header(header),
                    f"Header blacklist bypassed by: '{header}'",
                )
                with self.assertRaises(DataPolicyError):
                    assert_aggregated_csv([header, "Omsetning"], [["test", "100"]])

    def test_domain_safelist_preserved_against_blacklist(self):
        safe_headers = [
            "Arrangement",
            "arrangementsnavn",
            "Arrangementsnavn",
            "ARRANGEMENTSNAVN",
            "arrangement_navn",
            "Rom",
            "romnavn",
            "Romnavn",
            "rom_navn",
            "Lokale",
            "lokalnavn",
            "lokale_navn",
            "Artist",
            "artistnavn",
            "Artistnavn",
            "artist_navn",
            "Produksjon",
            "produksjonsnavn",
            "Produksjonsnavn",
            "Antall_Gjester",
            "antall_gjester",
            "gjester_totalt",
            "total_guests",
            "Antall_Kunder",
            "antall_kunder",
            "kunder_totalt",
            "Forestillingsnavn",
            "forestillingsnavn",
        ]
        for header in safe_headers:
            with self.subTest(header=header):
                self.assertFalse(
                    is_forbidden_column_header(header),
                    f"Domain safe header incorrectly blocked: '{header}'",
                )
                # Ensure assert_aggregated_csv accepts it
                assert_aggregated_csv([header, "Dato"], [["Verdi", "2026-08-20"]])


class TestReviewerIdentityRedactionAdversarial(unittest.TestCase):
    """Stress-test reviewer redaction with tricky word boundaries and names."""

    def test_substring_collisions_not_redacted(self):
        # Name "Jan" should not redact "Januar"
        self.assertEqual(
            redact_reviewer_identity("Dette skjedde i Januar 2026", "Jan"),
            "Dette skjedde i Januar 2026",
        )
        # Name "Dan" should not redact "Danseforestilling"
        self.assertEqual(
            redact_reviewer_identity("En fantastisk Danseforestilling", "Dan"),
            "En fantastisk Danseforestilling",
        )
        # Name "Per" should not redact "Performance" or "Person"
        self.assertEqual(
            redact_reviewer_identity("En unik Performance for hver person", "Per"),
            "En unik Performance for hver person",
        )
        # Name "Liv" should not redact "Livet"
        self.assertEqual(
            redact_reviewer_identity("Livet på scenen var magisk", "Liv"),
            "Livet på scenen var magisk",
        )
        # Name "Tor" should not redact "Torsdag"
        self.assertEqual(
            redact_reviewer_identity("Forestilling på Torsdag kveld", "Tor"),
            "Forestilling på Torsdag kveld",
        )
        # Name "Ida" should not redact "Idag"
        self.assertEqual(
            redact_reviewer_identity("Idag opplevde vi teateret", "Ida"),
            "Idag opplevde vi teateret",
        )
        # Name "Eli" should not redact "Eliteteater"
        self.assertEqual(
            redact_reviewer_identity("Et ekte Eliteteater i byen", "Eli"),
            "Et ekte Eliteteater i byen",
        )

    def test_standalone_names_redacted(self):
        cases = [
            ("Jan sa: Maten var nydelig!", "Jan", "[ANMELDER] sa: Maten var nydelig!"),
            ("Sitat fra Jan.", "Jan", "Sitat fra [ANMELDER]."),
            ("Dan og Per likte showet", "Dan", "[ANMELDER] og Per likte showet"),
            ("Kari Nordmann mente servicen var topp", "Kari Nordmann", "[ANMELDER] [ANMELDER] mente servicen var topp"),
            ("Omtale: (Kari) ga 5 stjerner", "Kari", "Omtale: ([ANMELDER]) ga 5 stjerner"),
        ]
        for original, author, expected in cases:
            with self.subTest(original=original, author=author):
                self.assertEqual(redact_reviewer_identity(original, author), expected)

    def test_empty_or_none_author(self):
        self.assertEqual(redact_reviewer_identity("Tekst", None), "Tekst")
        self.assertEqual(redact_reviewer_identity("Tekst", ""), "Tekst")
        self.assertEqual(redact_reviewer_identity("Tekst", "   "), "Tekst")


class TestSecurityRepoPathsAndSourcePolicyAdversarial(unittest.TestCase):
    """Stress-test path confinement and network security policies."""

    def test_repopaths_traversal_attacks(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "allowed").mkdir()
            paths = RepoPaths(root)

            # Valid internal paths
            p1 = paths.output_path("allowed/file.txt")
            self.assertTrue(p1.is_relative_to(root))

            # Traversal attacks
            attacks = [
                "../escape.txt",
                "allowed/../../escape.txt",
                "..\\escape.txt",
                "allowed\\..\\..\\escape.txt",
                "C:/Windows/System32/calc.exe",
                "/etc/passwd",
            ]
            for attack in attacks:
                with self.subTest(attack=attack):
                    with self.assertRaises(PathPolicyError):
                        paths.output_path(attack)

    def test_source_policy_ssrf_and_dns(self):
        # Whitelisted host with public IP
        policy = SourcePolicy(
            allowed_hosts={"api.met.no", "places.googleapis.com"},
            resolver=lambda host: ["157.249.40.10"] if host == "api.met.no" else ["142.250.74.42"],
        )
        self.assertEqual(policy.validate("https://api.met.no/weather").host, "api.met.no")

        # HTTP rejected
        with self.assertRaises(SourcePolicyError):
            policy.validate("http://api.met.no/weather")

        # Credentials in URL rejected
        with self.assertRaises(SourcePolicyError):
            policy.validate("https://admin:pass@api.met.no/weather")

        # Custom port rejected
        with self.assertRaises(SourcePolicyError):
            policy.validate("https://api.met.no:8080/weather")

        # Unapproved host rejected
        with self.assertRaises(SourcePolicyError):
            policy.validate("https://evil.com/payload")

        # Private IP / Loopback SSRF rejected
        ssrf_policy = SourcePolicy(
            allowed_hosts={"api.met.no"},
            resolver=lambda _host: ["127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.169.254"],
        )
        with self.assertRaises(SourcePolicyError):
            ssrf_policy.validate("https://api.met.no/weather")


class TestSafeErrorSummaryAdversarial(unittest.TestCase):
    """Stress-test error masking to ensure no PII leaks into log/manifest summaries."""

    def test_mask_sensitive_error_pii(self):
        err = "Failed request for user ola@example.com with tlf +47 99887766, FNR 01010112377, Card 4532 0150 0000 0007"
        masked = mask_sensitive_error(err)
        self.assertNotIn("ola@example.com", masked)
        self.assertNotIn("99887766", masked)
        self.assertNotIn("01010112377", masked)
        self.assertNotIn("4532 0150 0000 0007", masked)
        self.assertIn("[MASKERT_EPOST]", masked)
        self.assertIn("[MASKERT_TELEFON]", masked)
        self.assertIn("[MASKERT_FNR]", masked)
        self.assertIn("[MASKERT_KORT]", masked)

    def test_safe_error_summary_deterministic_messages(self):
        self.assertEqual(
            safe_error_summary(DataPolicyError("Sensitive info: 91234567")),
            "Datapolicyen avviste input.",
        )
        self.assertEqual(
            safe_error_summary(SourcePolicyError("Private IP 10.0.0.1")),
            "Kildepolicyen avviste forespørselen eller innholdet.",
        )
        self.assertEqual(
            safe_error_summary(PathPolicyError("Path escape to C:/secrets")),
            "Filpolicyen avviste stien.",
        )
        self.assertEqual(
            safe_error_summary(ValueError("Maksimalt tokenbudsjett er nådd.")),
            "Maksimalt tokenbudsjett er nådd.",
        )
        self.assertEqual(
            safe_error_summary(RuntimeError("Unexpected memory corruption")),
            "Teknisk feil (RuntimeError).",
        )


class TestReviewLimitAssertion(unittest.TestCase):
    def test_review_limit_enforced(self):
        # Within limit
        assert_review_limit(5, 10)
        assert_review_limit(10, 10)

        # Exceeds limit
        with self.assertRaises(DataPolicyError):
            assert_review_limit(11, 10)


if __name__ == "__main__":
    unittest.main()
