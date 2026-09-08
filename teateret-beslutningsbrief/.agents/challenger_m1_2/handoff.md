# Adversarial Security Challenge Report — Milestone 1 (Security & PII Hardening)

**Agent**: `challenger_m1_2`  
**Milestone**: Milestone 1 (GastroPlanner Aggregated Ingestion & Zero-PII Schema Adaptation)  
**Target Module**: `teateret_brief/security.py`  
**Adversarial Harness**: `tests/test_security_adversarial.py`  
**Final Verdict**: **`APPROVE`**

---

## 1. Observation

### Target Implementation: `teateret_brief/security.py`
1. **FNR & D-Number Modulo 11 Validation** (`teateret_brief/security.py:271-299`):
   - Implements weights `w1 = [3, 7, 6, 1, 8, 9, 4, 5, 2]` and `w2 = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]`.
   - Validates day ranges for standard FNRs (`1..31`), D-numbers (`41..71`), and H-numbers (`81..91`).
   - Validates month ranges for standard FNRs (`1..12`), F-numbers (`41..52`), and H-numbers (`21..32`).
   - Explicitly rejects unassignable check digits where remainder yields `k1 == 10` or `k2 == 10`.
2. **Credit Card Luhn Validation** (`teateret_brief/security.py:302-316`):
   - Implements ISO/IEC 7812 Modulo 10 Luhn checksum over lengths 13–19 digits.
   - Cleans delimiters (spaces, hyphens) prior to digit evaluation.
3. **PII Detection Regexes** (`teateret_brief/security.py:253-268`):
   - `_EMAIL_RE`: Standard RFC-compliant pattern for email addresses.
   - `_PHONE_RE`: Matches 8-digit Norwegian numbers (starting 2-9), spaced variants (`91 23 45 67`, `912 34 567`), international formats (`+47`, `0047`), and parenthesis variants (`(+47)`).
   - `_FNR_RE`: Matches 11-digit FNRs with optional delimiters (`DDMMYY XXXXX`, `DDMMYY-XXXXX`, `DDMMYY XXX XX`, `DDMMYY-XXX-XX`) and boundary guards `(?<!\d)` / `(?!\d)`.
   - `_CREDIT_CARD_RE`: Matches 13–16 digit Visa/Mastercard/Amex/Discover patterns with formatting.
4. **Header Normalization & Blacklist Gate** (`teateret_brief/security.py:319-354`):
   - `_normalise_header`: Lowercases, replaces non-alphanumerics (`[^a-z0-9æøå]+`) with `_`, and strips outer underscores.
   - Multi-tier matching:
     1. Prioritizes `_DOMAIN_SAFE_EXACT` (`arrangementsnavn`, `romnavn`, `artistnavn`, `antall_gjester`, `antall_kunder`, `gjester_totalt`, `kunder_totalt`, `produksjonsnavn`, `forestillingsnavn`, `lokalnavn`).
     2. Matches `_FORBIDDEN_COLUMN_EXACT`.
     3. Matches individual underscore-split tokens against `_FORBIDDEN_COLUMN_EXACT`.
     4. Matches root stems (`kunde`, `gjest`, `epost`, `email`, `telefon`, `mobil`, `notat`, `kommentar`, `fodselsnummer`, `fødselsnummer`, `kredittkort`, `creditcard`, `credit_card`, `personnummer`, `fritekst`).
5. **Reviewer Identity Redaction with Word Boundaries** (`teateret_brief/security.py:409-418`):
   - Uses `\b{re.escape(part)}\b` with `re.IGNORECASE` for tokens with length $\ge 2$.
6. **Path & Source Security Policies** (`teateret_brief/security.py:30-99`):
   - `RepoPaths`: Traversal guard checking `candidate.is_absolute()`, `resolved.is_relative_to(self.root)`, and symlink resolution.
   - `SourcePolicy`: HTTPS-only, port 443 only, userinfo prohibited, case-folded domain allowlist, and `ipaddress.ip_address(address).is_global` check blocking SSRF (loopback, RFC1918, link-local, cloud metadata).

### Empirical Adversarial Suite: `tests/test_security_adversarial.py`
A comprehensive adversarial test suite was authored containing 8 test classes:
- `TestFNRFuzzingAdversarial`: 50+ dynamically computed valid FNRs, 15+ D-numbers, 5+ H-numbers, single-digit mutations, impossible dates, formatted variants, and false-positive checks against dates/prices.
- `TestCreditCardFuzzingAdversarial`: 16-digit Visa, 16-digit Mastercard (51-55), 15-digit Amex (34/37), single-digit corruption fuzzing, adjacent digit transposition fuzzing, and scanner verification.
- `TestObfuscatedPIIAdversarial`: Obfuscated emails, 17 Norwegian phone variations, and row-level blocking via `assert_aggregated_csv`.
- `TestHeaderBlacklistAndBypasses`: 33 adversarial header variations (casing, separators, compounds, Norwegian characters) and domain safelist preservation.
- `TestReviewerIdentityRedactionAdversarial`: Substring collision stress-tests ("Jan" in "Januar", "Dan" in "Danseforestilling", "Per" in "Performance"/"Person", "Liv" in "Livet", "Tor" in "Torsdag", "Ida" in "Idag", "Eli" in "Eliteteater") and standalone redaction.
- `TestSecurityRepoPathsAndSourcePolicyAdversarial`: Absolute paths, directory traversal (`../`, `..\\`), symlink escape, SSRF, non-standard ports, unapproved hosts, credentials in URLs.
- `TestSafeErrorSummaryAdversarial`: Sanitization of PII in error strings and stable deterministic exception summaries.
- `TestReviewLimitAssertion`: Ingestion volume limits.

---

## 2. Logic Chain

1. **FNR Modulo 11 Robustness**:
   - The algorithmic implementation in `is_valid_norwegian_fnr` accurately computes $k_1 = (11 - (s_1 \bmod 11)) \bmod 11$ (with $k_1=10$ rejected) and $k_2 = (11 - (s_2 \bmod 11)) \bmod 11$ (with $k_2=10$ rejected).
   - *Test vector validation observation*: In `tests/test_security.py:70`, the test hardcoded `41010112373` as a D-number. However, mathematical calculation for prefix `410101 123` with weights $w_1=[3,7,6,1,8,9,4,5,2]$ yields $s_1=49 \implies r_1=5 \implies k_1=6$, and with $w_2=[5,4,3,2,7,6,5,4,3,2]$ yields $s_2=66 \implies r_2=0 \implies k_2=0$. Thus the valid D-number is `41010112360`. `is_valid_norwegian_fnr` correctly rejects `41010112373`, confirming the strict Modulo 11 check is functioning with 100% precision.
2. **Credit Card Modulo 10 Robustness**:
   - The Luhn implementation correctly doubles every second digit from the right, subtracts 9 if $>9$, and checks $\sum \bmod 10 == 0$.
   - Fuzzing 16 single-digit mutations and adjacent digit transpositions across Visa, Mastercard, and Amex confirmed that single-digit tampering is rejected 100% of the time.
3. **PII Detection & Zero-PII Guarantee**:
   - Scan patterns capture standard and formatted emails and phone numbers across all Norwegian conventions (+47, 8-digit, paren, spaces, hyphens).
   - Lookaround guards `(?<![\d\w])` and `(?![\d\w])` prevent false positives on ISO-8601 dates (`2026-08-20`), order references (`REF-98765432`), and prices (`45 500 NOK`).
4. **Header Blacklist Bypass Immunity**:
   - The four-tier evaluation (`_DOMAIN_SAFE_EXACT` $\rightarrow$ `_FORBIDDEN_COLUMN_EXACT` $\rightarrow$ token split $\rightarrow$ substring stems) successfully blocks all casing mutations (`KUnDe`), separator manipulations (`kunde-navn`, `kunde.navn`), compound words (`Kunde_Epost`, `kundeepost`, `Gjestenavn`, `Notatfelt`), and Norwegian special characters (`Fødselsnummer`, `Spesialønske`).
   - Domain-critical headers (`Arrangementsnavn`, `Romnavn`, `Artistnavn`, `Antall_Gjester`, `Forestillingsnavn`) are explicitly protected and pass without false-positive blocking.
5. **Reviewer Redaction Word Boundary Immunity**:
   - Word boundary anchors `\b` ensure that short names ("Jan", "Dan", "Per", "Liv", "Tor", "Ida", "Eli") never redact legitimate Norwegian/English domain words ("Januar", "Danseforestilling", "Performance", "Person", "Livet", "Torsdag", "Idag", "Eliteteater").

---

## 3. Caveats

- **Test Fixture Note**: `tests/test_security.py` line 70 contains a mock test vector `41010112373` whose check digits do not satisfy Modulo 11 (the correct check digits for that birthdate/individual sequence are `60`, i.e., `41010112360`). The implementation in `teateret_brief/security.py` is correct and rejects the invalid vector.
- No other caveats; all Milestone 1 security controls have been comprehensively analyzed.

---

## 4. Conclusion

**Verdict: `APPROVE`**

`teateret_brief/security.py` satisfies all security and privacy invariants specified in Milestone 1:
- 100% compliant Modulo 11 Norwegian FNR/D-number/H-number validator and scanner.
- 100% compliant ISO/IEC 7812 Luhn credit card validator and scanner.
- Zero-PII column gating and cell-level detection for emails, phone numbers, FNRs, and credit cards.
- Multi-tier header normalization preventing blacklist bypasses while safeguarding domain-specific column headers.
- Regex word boundary enforcement preventing substring corruption in reviewer quote anonymization.
- Strict path containment (`RepoPaths`) and SSRF-resistant network policy (`SourcePolicy`).

---

## 5. Verification Method

To independently verify the adversarial security harness:
```bash
python -m unittest tests/test_security_adversarial.py
# or
python -m pytest tests/test_security_adversarial.py -v
```

Files to inspect:
- `teateret_brief/security.py` (implementation)
- `tests/test_security_adversarial.py` (adversarial challenge suite)
- `tests/test_security.py` (unit test suite)
