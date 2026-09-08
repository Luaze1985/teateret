# Handoff Report: Security & PII Gating Mechanisms Investigation

**Agent**: `explorer_m1_2`  
**Working Directory**: `C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\explorer_m1_2`  
**Milestone**: M1 (GastroPlanner Ingestion & Zero-PII Schema Adaptation)  
**Parent Agent**: `sub_orch_m1` (`3b098b0f-ac4f-40c2-bd6b-42e9b79ae0bc`)  
**Date**: 2026-08-20  

---

## 1. Observation

Direct observations from the current codebase (`teateret_brief/security.py`, `teateret_brief/csv_adapter.py`, `teateret_brief/google_places.py`, `teateret_brief/pipeline.py`, `tests/test_security.py`):

### 1.1 Column Header Filtering (`teateret_brief/security.py:101-140`)
Current implementation:
```python
_FORBIDDEN_COLUMN_PARTS = {
    "customer",
    "customer_name",
    "kunde",
    "kundenavn",
    "guest",
    "guest_name",
    "email",
    "e-post",
    "phone",
    "telefon",
    "address",
    "adresse",
    "comment",
    "kommentar",
    "reservation_note",
    "reservasjonsnotat",
}

def _normalise_header(header: str) -> str:
    return re.sub(r"[^a-z0-9æøå]+", "_", header.casefold()).strip("_")

def assert_aggregated_csv(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> None:
    normalised = [_normalise_header(header) for header in headers]
    violations = [
        header
        for header in normalised
        if any(part == header or part in header for part in _FORBIDDEN_COLUMN_PARTS)
    ]
    if violations:
        raise DataPolicyError(f"Person- eller fritekstfelt er ikke tillatt: {', '.join(violations)}")
```

**Observed Weaknesses & Vulnerabilities:**
1. **"Epost" Bypass**: `_normalise_header("Epost")` becomes `"epost"`. In `_FORBIDDEN_COLUMN_PARTS`, only `"e-post"` is present (`_normalise_header("e-post")` is `"e_post"`). `"e_post" in "epost"` evaluates to `False`, allowing unhyphenated `Epost` or `Epostadresse` to bypass filtering!
2. **Missing Essential Forbidden PII Keywords**:
   - Customer/Guest name terms: `navn`, `name`, `fullt_navn`, `full_name`, `fornavn`, `first_name`, `etternavn`, `last_name`, `kontaktperson`, `kontakt`, `contact`, `gjest` (uncompounded), `gjestenavn`, `bruker`, `brukernavn`, `user`.
   - Notes & free-text: `notat`, `notater`, `note`, `notes`, `bestillingsnotat`, `ordrenotat`, `beskjed`, `melding`, `message`, `fritekst`, `free_text`.
   - Contact numbers: `mobil`, `mobilnr`, `mobilnummer`, `tlf`, `tlfnr`, `telefonnr`, `cell`, `mobile`.
   - National identity numbers & payment details: `fnr`, `fodselsnummer`, `fødselsnummer`, `personnummer`, `ssn`, `d_nummer`, `kortnummer`, `kredittkort`, `credit_card`, `card_number`, `pan`, `cvv`, `kontonummer`, `bankkonto`, `iban`.
   - Dietary & special requests: `allergi`, `allergier`, `allergy`, `spesialønske`, `special_request`.
3. **Substring Matching False Positive Risk on `navn`**:
   - If `navn` is added to `_FORBIDDEN_COLUMN_PARTS` with substring check (`part in header`), valid domain columns like `Arrangementsnavn`, `Forestillingsnavn`, `Romnavn`, `Lokalnavn`, `Artistnavn` would be falsely rejected.
   - An explicit domain whitelist (e.g. `_DOMAIN_SAFE_EXACT`) and structured token matching are required.

### 1.2 PII Pattern Scanning & Redaction (`teateret_brief/security.py:119-174`)
Current implementation:
```python
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(
    r"(?<![\d-])\+\d{1,3}(?:[\s.-]?\d){8,12}(?!\d)|"
    r"(?<!\d)[2-9]\d{7}(?!\d)|"
    r"(?<!\d)[2-9]\d{2}[\s-]\d{2}[\s-]\d{3}(?!\d)|"
    r"(?<!\d)[2-9]\d[\s-]\d{2}[\s-]\d{2}[\s-]\d{2}(?!\d)"
)

def scan_public_artifact(text: str) -> list[str]:
    findings: list[str] = []
    if _EMAIL_RE.search(text):
        findings.append("email")
    if _PHONE_RE.search(text):
        findings.append("phone")
    return findings
```

**Observed Gaps & Bugs:**
1. **Zero Support for Norwegian National Identity Numbers (FNR / D-nummer)**:
   - Neither `scan_public_artifact`, `assert_aggregated_csv`, `redact_contact_details`, nor `mask_sensitive_error` inspect or block 11-digit national identity numbers (`DDMMYYXXXXX`).
2. **Zero Support for Credit Card Numbers (13–19 Digits / PAN)**:
   - No detection or Luhn checksum verification for credit card numbers (Visa, Mastercard, Amex, etc.).
3. **Phone Regex Boundary Gaps**:
   - Unspaced international prefix `004791234567` is not caught (starts with `0047`, failing `\+\d` and failing `(?<!\d)[2-9]\d{7}` due to preceding `7`).
   - Formats with parentheses like `(+47) 912 34 567` or `(47) 91234567` are unhandled.
4. **Reviewer Name Redaction Word Boundary Bug (`teateret_brief/security.py:164-173`)**:
   ```python
   def redact_reviewer_identity(text: str, author_name: str | None) -> str:
       if not author_name or not author_name.strip():
           return text
       parts = author_name.strip().split()
       for part in parts:
           if len(part) >= 2:
               text = re.sub(re.escape(part), "[ANMELDER]", text, flags=re.IGNORECASE)
       return text
   ```
   - **Bug**: Lack of `\b` word boundary means common first names (e.g. "Jan", "Dan", "Per", "Liv", "Tom", "May") corrupt standard Norwegian words:
     - "Jan" in "Januar" -> "[ANMELDER]uar"
     - "Dan" in "Danseforestilling" -> "[ANMELDER]seforestilling"
     - "Per" in "Performance" -> "[ANMELDER]formance"
     - "Liv" in "Opplevelse" -> "Opp[ANMELDER]else"

### 1.3 Strict Mode Interface Contract (`SCOPE.md:22` vs `security.py:132`)
- `SCOPE.md` declares: `assert_aggregated_csv(df: pd.DataFrame, strict: bool = True) -> None` or equivalent function accepting `strict` and `allowed_headers`.
- `security.py` currently only takes `(headers: Iterable[str], rows: Iterable[Iterable[str]])` without an `allowed_headers` or `strict` parameter; `load_aggregated_csv` implements strictness separately. Supporting `allowed_headers` and `strict=True` directly in `assert_aggregated_csv` unifies schema gating across all entry points.

---

## 2. Logic Chain

```
[Observation 1.1] "Epost" is missing from _FORBIDDEN_COLUMN_PARTS, and unhyphenated header produces "epost" which does not contain "e_post".
   │
   └──> [Inference 1]: Attackers or careless users exporting "Epost" or "Epostadresse" bypass column filtering.
        [Remedy]: Normalize and check both tokens and expanded exact/stem dictionary ("epost", "email", "mail", "e_post").

[Observation 1.1] Substring matching "navn" would block legitimate domain columns ("Arrangementsnavn", "Romnavn", "Artistnavn").
   │
   └──> [Inference 2]: A two-tier check is required: (1) Domain-safe whitelist checked first, (2) Exact/Token-level blacklist with compound checks.

[Observation 1.2] Neither FNR (11-digit Modulo 11) nor Credit Cards (13-19 digit Luhn) are detected in security.py.
   │
   └──> [Inference 3]: R1 and R4 acceptance criteria (Zero PII leakage) are vulnerable to accidental ingestion or generation of identity/financial data.
        [Remedy]: Introduce _FNR_RE + Modulo 11 validator, _CREDIT_CARD_RE + Luhn validator, and integrate into scan_public_artifact, assert_aggregated_csv, and redact_contact_details.

[Observation 1.2] redact_reviewer_identity uses re.escape(part) without \b word boundary.
   │
   └──> [Inference 4]: Names with length >= 2 that match subwords ("Jan" in "Januar", "Dan" in "Danseforestilling") cause text corruption in Google Places review quotes.
        [Remedy]: Use re.sub(rf"\b{re.escape(part)}\b", "[ANMELDER]", text, flags=re.IGNORECASE).
```

---

## 3. Caveats

1. **Synthetic vs Real FNR Numbers**: Synthetic test FNRs generated for unit tests must satisfy either the Modulo 11 control digit algorithm or be recognized by pattern scanning. In the scanner, pattern matching with valid day/month ranges catches both synthetic and real numbers, while the `is_valid_norwegian_fnr` function offers mathematical proof.
2. **Large Metric Numbers (e.g. 25 000 000 NOK)**: 8-digit numbers in text could theoretically collide with 8-digit phone numbers if not formatted properly. However, phone regex requiring word boundaries `(?<![\d\w])` and Norwegian leading digit ranges `[2-9]`, combined with cell scanning, ensures sales revenue in standard formats (`185000,00`, `250000.00`) is parsed cleanly without false positives.
3. **Execution Environment**: Shell command execution (`run_command`) was not available during subagent execution; all analysis was performed via static inspection and code analysis.

---

## 4. Conclusion & Proposed Implementation Plan

The current security foundation in `security.py` has solid architectural bones (`RepoPaths`, `SourcePolicy`, DNS validation, SSRF checks), but requires critical hardening in:
1. PII detection expansion (Norwegian FNR with Modulo 11 and Credit Cards with Luhn algorithm).
2. Forbidden column list expansion and robust token-based matching with domain whitelist exemptions.
3. Reviewer name redaction fix with word boundaries (`\b`).
4. `assert_aggregated_csv` support for `strict: bool = False` and `allowed_headers: Iterable[str] | None = None`.
5. Comprehensive test coverage in `tests/test_security.py`.

### 4.1 Proposed Code Changes for `teateret_brief/security.py`

```python
# ==============================================================================
# PROPOSED REPLACEMENT CHUNK FOR teateret_brief/security.py
# ==============================================================================

_FORBIDDEN_COLUMN_EXACT = {
    # Names & Persons
    "navn", "name", "kundenavn", "kunde_navn", "customer_name", "customer", "kunde",
    "client", "client_name", "gjest", "gjester", "guest", "guests", "guest_name",
    "gjestenavn", "gjest_navn", "kontakt", "kontaktperson", "kontakt_navn", "contact",
    "contact_name", "fornavn", "first_name", "firstname", "etternavn", "last_name",
    "lastname", "fullt_navn", "full_name", "fullname", "personnavn", "bruker",
    "brukernavn", "user", "username", "user_name",
    
    # Contact
    "email", "e_post", "epost", "mail", "e_mail", "kundeepost", "kunde_epost",
    "customer_email", "phone", "telefon", "telefonnr", "telefonnummer", "kundetelefon",
    "tlf", "tlfnr", "mobil", "mobilnr", "mobilnummer", "cell", "cellphone", "mobile",
    
    # National ID & Payments
    "fnr", "fodselsnummer", "fødselsnummer", "personnummer", "ssn", "national_id",
    "d_nummer", "dnummer", "kortnummer", "kredittkort", "credit_card", "card_number",
    "pan", "cvv", "cvc", "kontonummer", "bankkonto", "iban",
    
    # Address
    "adresse", "address", "gateadresse", "street_address", "postadresse", "postnr",
    "postnummer", "zipcode", "postal_code", "bosted",
    
    # Notes & Free Text
    "comment", "comments", "kommentar", "kommentarer", "notat", "notater", "note",
    "notes", "reservation_note", "reservasjonsnotat", "bestillingsnotat", "ordrenotat",
    "beskjed", "beskjeder", "melding", "meldinger", "message", "messages", "fritekst",
    "free_text", "allergi", "allergier", "allergy", "allergies", "spesialonske",
    "spesialønske", "special_request", "preferanse", "preferanser", "dietary",
}

# Domain safe terms that might end in 'navn' or contain 'kunde'/'gjest' in aggregate metrics
_DOMAIN_SAFE_EXACT = {
    "arrangement", "arrangementsnavn", "arrangement_navn",
    "forestilling", "forestillingsnavn", "forestilling_navn",
    "rom", "romnavn", "rom_navn",
    "lokale", "lokalnavn", "lokale_navn",
    "artist", "artistnavn", "artist_navn",
    "produksjon", "produksjonsnavn",
    "antall_gjester", "gjester_totalt", "total_guests",
    "antall_kunder", "kunder_totalt",
}

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)

_PHONE_RE = re.compile(
    r"(?<![\d\w])(?:\+|00)\d{1,3}(?:[\s.-]|\(\d{1,3}\))?(?:[\s.-]?\d){8,12}(?!\d)|"
    r"(?<![\d\w])\(\+(?:47|\d{1,3})\)[\s-]?(?:[\s.-]?\d){8,10}(?!\d)|"
    r"(?<![\d\w])[2-9]\d{7}(?![\d\w])|"
    r"(?<![\d\w])[2-9]\d{2}[\s-]\d{2}[\s-]\d{3}(?![\d\w])|"
    r"(?<![\d\w])[2-9]\d[\s-]\d{2}[\s-]\d{2}[\s-]\d{2}(?![\d\w])"
)

# Norwegian FNR (11 digits: DDMMYYXXXXX) with valid day (01-31, 41-71 D-nr) and month (01-12, 41-52 H-nr)
_FNR_RE = re.compile(
    r"(?<!\d)(?:0[1-9]|[12]\d|3[01]|4[1-9]|[56]\d|7[01])(?:0[1-9]|1[0-2]|4[1-9]|5[0-2])\d{2}[\s-]?(?:\d{5}|\d{3}[\s-]?\d{2})(?!\d)"
)

# Credit Card (13-19 digits, Visa, Mastercard, Amex, Diners, Discover)
_CREDIT_CARD_RE = re.compile(
    r"(?<!\d)(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[\s-]?(?:\d{4}[\s-]?){2}\d{1,4}(?!\d)|"
    r"(?<!\d)(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|6011\d{12})(?!\d)|"
    r"(?<!\d)\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}(?!\d)"
)


def is_valid_norwegian_fnr(value: str) -> bool:
    """Validerer 11-sifret norsk fødselsnummer / D-nummer med modulo 11 kontrollsiffer."""
    cleaned = re.sub(r"[\s-]", "", value)
    if len(cleaned) != 11 or not cleaned.isdigit():
        return False
    digits = [int(c) for c in cleaned]
    
    day = digits[0] * 10 + digits[1]
    month = digits[2] * 10 + digits[3]
    if not ((1 <= day <= 31 or 41 <= day <= 71) and (1 <= month <= 12 or 41 <= month <= 52)):
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


def is_valid_luhn(card_number: str) -> bool:
    """Validerer kredittkortnummer med Luhn-algoritmen (Mod 10)."""
    cleaned = re.sub(r"[\s-]", "", card_number)
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


def _normalise_header(header: str) -> str:
    return re.sub(r"[^a-z0-9æøå]+", "_", header.casefold()).strip("_")


def is_forbidden_column_header(header: str) -> bool:
    norm = _normalise_header(header)
    if norm in _DOMAIN_SAFE_EXACT:
        return False
    if norm in _FORBIDDEN_COLUMN_EXACT:
        return True
    tokens = set(norm.split("_"))
    if any(t in _FORBIDDEN_COLUMN_EXACT for t in tokens):
        return True
    stems = ["kunde", "kundenavn", "guest", "gjest", "epost", "email", "telefon", "mobil", "notat", "kommentar", "fodselsnummer", "fødselsnummer", "kredittkort", "creditcard", "credit_card", "personnummer"]
    for stem in stems:
        if stem in norm and norm not in _DOMAIN_SAFE_EXACT:
            return True
    return False


def assert_aggregated_csv(
    headers: Iterable[str],
    rows: Iterable[Iterable[str]],
    *,
    allowed_headers: Iterable[str] | None = None,
    strict: bool = False,
) -> None:
    headers_list = list(headers)
    violations = [h for h in headers_list if is_forbidden_column_header(h)]
    if violations:
        raise DataPolicyError(f"Person- eller fritekstfelt er ikke tillatt: {', '.join(violations)}")
        
    if strict and allowed_headers is not None:
        allowed_set = set(allowed_headers)
        unknown = [h for h in headers_list if h not in allowed_set]
        if unknown:
            raise DataPolicyError(f"Ukjente kolonner er ikke tillatt i streng modus: {', '.join(sorted(unknown))}")
            
    for row in rows:
        for value in row:
            text = str(value)
            findings = scan_public_artifact(text)
            if findings:
                raise DataPolicyError(f"Direkte personopplysninger ({', '.join(findings)}) er ikke tillatt i aggregert input.")


def scan_public_artifact(text: str) -> list[str]:
    findings: list[str] = []
    if _EMAIL_RE.search(text):
        findings.append("email")
    if _PHONE_RE.search(text):
        findings.append("phone")
    if _FNR_RE.search(text):
        findings.append("fnr")
    if _CREDIT_CARD_RE.search(text):
        findings.append("credit_card")
    return findings


def redact_contact_details(text: str) -> tuple[str, list[str]]:
    findings = scan_public_artifact(text)
    redacted = _EMAIL_RE.sub("[MASKERT_EPOST]", text)
    redacted = _PHONE_RE.sub("[MASKERT_TELEFON]", redacted)
    redacted = _FNR_RE.sub("[MASKERT_FNR]", redacted)
    redacted = _CREDIT_CARD_RE.sub("[MASKERT_KORT]", redacted)
    return redacted, findings


def redact_reviewer_identity(text: str, author_name: str | None) -> str:
    """Fjern anmeldernavn fra sitat for å unngå PII-lekkasje med ordgrenser."""
    if not author_name or not author_name.strip():
        return text
    parts = author_name.strip().split()
    for part in parts:
        if len(part) >= 2:
            text = re.sub(rf"\b{re.escape(part)}\b", "[ANMELDER]", text, flags=re.IGNORECASE)
    return text


def mask_sensitive_error(message: str) -> str:
    masked = _EMAIL_RE.sub("[MASKERT_EPOST]", message)
    masked = _PHONE_RE.sub("[MASKERT_TELEFON]", masked)
    masked = _FNR_RE.sub("[MASKERT_FNR]", masked)
    return _CREDIT_CARD_RE.sub("[MASKERT_KORT]", masked)
```

---

## 5. Verification Method

To independently verify the implementation after application by the builder agent:

1. **Run Full Security Unit Tests**:
   ```bash
   python -m unittest tests/test_security.py
   python -m pytest tests/test_security.py tests/test_csv_adapter.py
   ```
2. **Inspect Specific Invalidation & Acceptance Conditions**:
   - **Condition 1 (FNR Rejection)**: `assert_aggregated_csv(["Dato", "Arrangement", "Billetter"], [["2026-08-20", "Test", "01010112377"]])` must raise `DataPolicyError`.
   - **Condition 2 (Credit Card Rejection)**: `assert_aggregated_csv(["Dato", "Arrangement", "Billetter"], [["2026-08-20", "Test", "4532 0150 0000 0008"]])` must raise `DataPolicyError`.
   - **Condition 3 (Unhyphenated Epost)**: `assert_aggregated_csv(["Dato", "Epost", "Billetter"], [["2026-08-20", "a@b.no", "10"]])` must raise `DataPolicyError`.
   - **Condition 4 (Domain Whitelist Non-Regression)**: Headers like `Arrangementsnavn`, `Romnavn`, `Artistnavn` must NOT raise `DataPolicyError`.
   - **Condition 5 (Reviewer Word Boundary Redaction)**: `redact_reviewer_identity("Danseforestilling i Januar", "Dan")` must return `"Danseforestilling i Januar"` (not `"[ANMELDER]seforestilling i Januar"`).
   - **Condition 6 (Sample CSV Ingestion)**: `sample_data/gastroplanner_sample_2026.csv` must ingest cleanly without any errors.
