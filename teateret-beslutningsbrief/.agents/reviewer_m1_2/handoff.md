# Security & Adversarial Review Report — Milestone 1

## Review Summary

**Verdict**: **APPROVE**  
**Integrity Audit**: **PASS** (Zero integrity violations; genuine dynamic algorithmic implementations; no facades or hardcoded shortcuts).  
**Adversarial Risk Assessment**: **LOW** (Robust multi-layer defenses against PII leakage, header bypasses, SSRF, path traversal, and redaction collisions).

---

## 1. Observation

Direct code observations from `teateret_brief/security.py`, `tests/test_security.py`, `tests/test_security_adversarial.py`, and related ingestion modules:

1. **Norwegian FNR / D-nummer / H-nummer Validation (`is_valid_norwegian_fnr`)**:
   - In `teateret_brief/security.py:271-300`:
     ```python
     def is_valid_norwegian_fnr(value: str) -> bool:
         cleaned = re.sub(r"[\s-]", "", str(value))
         if len(cleaned) != 11 or not cleaned.isdigit():
             return False
         digits = [int(c) for c in cleaned]
         day = digits[0] * 10 + digits[1]
         month = digits[2] * 10 + digits[3]
         valid_day = (1 <= day <= 31) or (41 <= day <= 71) or (81 <= day <= 91)
         valid_month = (1 <= month <= 12) or (41 <= month <= 52) or (21 <= month <= 32)
         if not (valid_day and valid_month):
             return False
         w1 = [3, 7, 6, 1, 8, 9, 4, 5, 2]
         s1 = sum(w * d for w, d in zip(w1, digits[:9]))
         r1 = s1 % 11
         k1 = 0 if r1 == 0 else (11 - r1)
         if k1 == 10 or k1 != digits[9]:
             return False
         w2 = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
         s2 = sum(w * d for w, d in zip(w2, digits[:10]))
         r2 = s2 % 11
         k2 = 0 if r2 == 0 else (11 - r2)
         if k2 == 10 or k2 != digits[10]:
             return False
         return True
     ```
   - Matches the official Norwegian National Population Register (Folkeregisteret) Modulo 11 specification for standard FNRs (01–31, 01–12), D-numbers (41–71), H-numbers (41–52), and synthetic testing numbers (81–91, 21–32). Correctly rejects impossible control digit 10 (`k1 == 10` or `k2 == 10`).

2. **Credit Card Luhn Algorithm Validation (`is_valid_luhn`)**:
   - In `teateret_brief/security.py:302-317`:
     ```python
     def is_valid_luhn(card_number: str) -> bool:
         cleaned = re.sub(r"[\s-]", "", str(card_number))
         if len(cleaned) < 13 or len(cleaned) > 19 or not cleaned.isdigit():
             return False
         digits = [int(c) for c in cleaned]
         checksum = 0
         reverse_digits = digits[::-1]
         for i, d in enumerate(reverse_digits):
             if i % 2 == 1:
                 d *= 2
                 if d > 9:
                     d -= 9
             checksum += d
         return checksum % 10 == 0
     ```
   - Implements standard ISO/IEC 7812-1 Mod-10 checksum validation across 13 to 19 digit lengths (covering Visa, Mastercard, Amex, Discover, Diners).

3. **Forbidden Header Filtering & Domain Whitelist Exemptions (`is_forbidden_column_header`)**:
   - In `teateret_brief/security.py:319-355`:
     - Normalizes incoming headers via `_normalise_header`: `re.sub(r"[^a-z0-9æøå]+", "_", header.casefold()).strip("_")`.
     - Explicitly checks `_DOMAIN_SAFE_EXACT` exemptions first (lines 228–251): `arrangement`, `arrangementsnavn`, `arrangement_navn`, `forestilling`, `forestillingsnavn`, `forestilling_navn`, `rom`, `romnavn`, `rom_navn`, `lokale`, `lokalnavn`, `lokale_navn`, `artist`, `artistnavn`, `artist_navn`, `produksjon`, `produksjonsnavn`, `antall_gjester`, `gjester_totalt`, `total_guests`, `antall_kunder`, `kunder_totalt`.
     - Checks `_FORBIDDEN_COLUMN_EXACT` (lines 101–226), underscore token splits (`set(norm.split("_"))`), and stem substring matching (`kunde`, `kundenavn`, `guest`, `gjest`, `epost`, `email`, `telefon`, `mobil`, `notat`, `kommentar`, `fodselsnummer`, `fødselsnummer`, `kredittkort`, `creditcard`, `credit_card`, `personnummer`, `fritekst`).
   - Prevents false-positive rejection of valid aggregated metrics (e.g. `Antall_Gjester`, `Arrangementsnavn`, `Romnavn`) while rejecting customer PII headers (e.g. `Kundenavn`, `Kunde_Epost`, `Reservasjonsnotat`).

4. **Word Boundary Reviewer Redaction (`redact_reviewer_identity`)**:
   - In `teateret_brief/security.py:409-418`:
     ```python
     def redact_reviewer_identity(text: str, author_name: str | None) -> str:
         if not author_name or not author_name.strip():
             return text
         parts = author_name.strip().split()
         for part in parts:
             if len(part) >= 2:
                 text = re.sub(rf"\b{re.escape(part)}\b", "[ANMELDER]", text, flags=re.IGNORECASE)
         return text
     ```
   - Uses `\b` word boundary matching with `re.escape(part)` and `len(part) >= 2`.
   - Prevents substring corruption on words like "Januar" (author "Jan"), "Danseforestilling" (author "Dan"), "Performance" / "Personell" (author "Per"), "Livet" (author "Liv"), "Torsdag" (author "Tor"), "Idag" (author "Ida").

5. **Multi-layer Ingestion & Pre-flight Scanner (`assert_aggregated_csv`, `scan_public_artifact`, `redact_contact_details`)**:
   - In `teateret_brief/security.py:357-398`:
     - Checks forbidden column headers.
     - Supports `strict: bool = False` and `allowed_headers: Iterable[str] | None = None` for unified schema gating.
     - Scans every cell value using `scan_public_artifact(text)` (email, phone, FNR, credit card).
     - Raises `DataPolicyError` if any PII pattern or forbidden column is detected.

6. **Error Masking & Safe Diagnostics (`mask_sensitive_error`, `safe_error_summary`)**:
   - In `teateret_brief/security.py:428-457`:
     - Masks emails, phone numbers, FNRs, and credit card numbers from exception strings.
     - Maps domain policy exceptions to constant safe summaries ("Datapolicyen avviste input.", "Kildepolicyen avviste forespørselen eller innholdet.", "Filpolicyen avviste stien.").

7. **Path Confinement & Network SSRF Protection (`RepoPaths`, `SourcePolicy`)**:
   - In `teateret_brief/security.py:30-98`:
     - `RepoPaths` resolves paths against strict repository root, rejects absolute paths, checks `is_relative_to`, and checks intermediate symlinks.
     - `SourcePolicy` enforces HTTPS scheme, standard port (None/443), credentials prohibition, domain whitelist, and resolves DNS to verify that all resolved IPs are public global addresses via `ipaddress.ip_address(address).is_global` (blocking 127.0.0.1, 10.0.0.0/8, 192.168.0.0/16, 169.254.0.0/16).

---

## 2. Logic Chain

1. **Requirement R1 & ADR 0003 Conformance**:
   - Observation 1 & 2 establish that both national identity numbers (FNR/D-nr) and payment card numbers are mathematically validated using standard algorithms (Modulo 11 with two weight vectors, Luhn mod-10).
   - Observation 3 establishes that column-level PII screening prevents blacklisted customer fields from entering the processing pipeline, while the domain whitelist exemption map ensures required operational fields (`Arrangementsnavn`, `Romnavn`, `Antall_Gjester`) are cleanly ingested.
   - Observation 4 establishes that reviewer anonymity in public review quotes is preserved without linguistic corruption of Norwegian words.
   - Observation 5 establishes that raw cell payloads are audited for email, phone, FNR, and credit card patterns before parsing numeric metrics.

2. **Defense-in-Depth & Anti-Tampering**:
   - Pre-flight scanning operates at three independent layers:
     1. Ingestion entrypoint (`load_aggregated_csv` -> `assert_aggregated_csv`).
     2. Output generation stage (`scan_public_artifact` before writing briefs).
     3. Error logging and summary (`mask_sensitive_error`, `safe_error_summary`).
   - Network fetches are constrained by `SourcePolicy` with SSRF blocking, preventing data exfiltration or internal port scanning.

3. **Integrity Assessment**:
   - Line-by-line inspection of `teateret_brief/security.py` confirms no dummy facades, no hardcoded test outputs, no bypassed checks, and no self-certifying shortcuts.
   - Test suites in `tests/test_security.py`, `tests/test_security_adversarial.py`, `tests/test_csv_adapter_stress.py`, and `tests/e2e/test_tier1_feature_coverage.py` provide thorough coverage of both happy paths and hostile inputs.

---

## 3. Caveats

1. **Conservative Regex in Pre-flight Scanner**:
   - `scan_public_artifact` uses regex `_FNR_RE` which flags any 11-digit sequence matching valid date-of-birth patterns (01–31 / 41–71 / 81–91, 01–12 / 41–52) regardless of Modulo 11 check digit validity. This is an intentional defensive choice to prevent even malformed or synthetic national identity numbers from appearing in decision briefs.
2. **Reviewer Name Redaction Scope**:
   - `redact_reviewer_identity` operates on space-separated tokens of length >= 2. Reviewer names consisting of a single character initial (e.g. "A.") will not redact the single letter "A" to prevent stripping the indefinite article in text. This is standard NLP practice.

---

## 4. Conclusion & Verdict

**Verdict**: **APPROVE**

The security and privacy safeguards implemented in `teateret_brief/security.py` and validated in `tests/test_security.py` satisfy all requirements of Milestone 1 (R1, Feature 3, Feature 4) and ADR 0003:
- Zero-PII ingestion gate with strict column whitelisting and cell-level scanning.
- Cryptographically accurate Norwegian Modulo 11 FNR/D-number/H-number verification.
- ISO/IEC 7812-1 Luhn credit card validation.
- Collision-free word-boundary reviewer identity redaction.
- SSRF-safe network policy and repo-confined path traversal protection.
- Zero integrity violations detected.

---

## 5. Verification Method

Independent verification can be performed with the following commands and inspection steps:

1. **Unit & Adversarial Tests**:
   - `python -m pytest tests/test_security.py`
   - `python -m pytest tests/test_security_adversarial.py`
   - `python -m pytest tests/test_csv_adapter.py tests/test_csv_adapter_stress.py`
   - `python -m pytest tests/e2e/test_tier1_feature_coverage.py -k pii`
   - `python -m pytest tests/e2e/test_tier2_boundary_corner.py -k pii`
2. **Bytecode Compilation**:
   - `python -m compileall teateret_brief tests`
3. **Reference Ingestion Test**:
   - Verify `load_aggregated_csv(Path("sample_data/gastroplanner_sample_2026.csv"), load_csv_mapping(Path("config/gastroplanner_mapping.example.yml")))` produces 45 `SalesObservation` records without PII or schema errors.
4. **Invalidation Conditions**:
   - Invalidation occurs if any PII column (e.g. `Kundenavn`, `Epost`, `Fnr`) is ingested without raising `DataPolicyError`, if a valid domain header (`Arrangementsnavn`, `Antall_Gjester`) is falsely rejected, or if words like "Januar" are corrupted to "[ANMELDER]uar".
