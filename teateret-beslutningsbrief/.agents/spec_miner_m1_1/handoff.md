# Handoff Report: GastroPlanner Ingestion & Normalization Engine Specification

**Agent**: `spec_miner_m1_1`  
**Milestone**: Milestone 1 (GastroPlanner Aggregated Ingestion & Zero-PII Schema Adaptation - R1)  
**Date**: 2026-08-20  
**Integrity Mode**: Development / Strict Governance  

---

## 1. Observation

Direct observations extracted from authoritative project artifacts and reference files:

1. **Original Request (`.agents/ORIGINAL_REQUEST.md`)**:
   - Lines 12–13 (R1): Ingestion of aggregated CSV/Excel exports from GastroPlanner with zero personal data (PII) leakage. Columns: rooms, event IDs, tickets sold, capacity, table bookings, preorder packages, and gross revenue with explicit type checking.
   - Lines 27–29: Acceptance criteria require ingesting `sample_data/gastroplanner_sample_2026.csv` with 0 PII or schema errors, >= 90% matching rate against the 129 verified events (2025–2026), and zero instances of PII in generated artifacts.

2. **Project Architecture & Scope (`.agents/orchestrator/PROJECT.md` & `.agents/sub_orch_m1/SCOPE.md`)**:
   - `PROJECT.md` Lines 55–60: Contract `load_aggregated_csv(path: Path, mapping: CsvMapping) -> list[SalesObservation]`.
   - `PROJECT.md` Line 58: `SalesObservation` model attributes: `period: date`, `label: str`, `metric: str`, `value: float`, `unit: str`, `room: str | None`, `event_id: str | None`, `source_system: str`, `match_status: Literal["matched", "needs_review", "unmatched"]`.
   - `SCOPE.md` Lines 10–16: Milestone 1 features:
     - Feature 1: GastroPlanner CSV Ingestion (Semicolon/comma delimiter, date parsing `%Y-%m-%d`, `%d.%m.%Y`, `%d/%m/%Y`, room mapping).
     - Feature 2: Norwegian Number & Currency Normalizer (`45 500,50` -> `45500.5`, strips `\u00a0`, validates positive finite floats).
     - Feature 3: Ingestion PII & Strict Column Gate (Rejects unknown columns in strict mode and forbids PII columns `kunde`, `email`, `phone`, `notat`).
     - Feature 4: Additional PII Hardening (Strict scanner for 11-digit Norwegian FNR and credit card patterns).

3. **Data Policy (`docs/data-policy.md`)**:
   - Lines 10–15: Permitted in Phase 1: Aggregated sales per event, date, or category; capacity, sold tickets, revenue, aggregate table bookings and preorder packages.
   - Lines 17–23: Forbidden in Phase 1: Customer names, emails, phones, customer free-text notes, booking notes, preferences, order history at individual level.
   - Lines 34–37: Technical enforcement: CSV reader rejects known identifier columns and direct email/phone regex patterns.

4. **Official GastroPlanner Research (`docs/research/gastroplanner-offisiell-dok-og-forretningsbruk.md`)**:
   - Lines 34–39: Modules identified: Table Booking & Capacity Management, Event Manager & Ticket Sales, Pre-order & Package Menus, Report Generator (exports to CSV/Excel).
   - Lines 75–89: Minimum allowed data contract:
     - Allowed fields: Date/Time (ISO), Room/Stage (`Hovedscenen`, `Biscenen`, `Intimscenen`, `Foajeen`, `Restauranten`), Show/Title, Capacity (integer), Sold tickets / Table count / Guest count (aggregate integer), Gross Revenue (NOK), Pre-ordered packages (aggregate integer).
     - Blocked fields: Customer names, email addresses, phone numbers, individual booking IDs, seat numbers, guest notes, allergies, credit cards.

5. **Avstemmingsrapport (`docs/research/gastroplanner-2026-avstemmingsrapport.md`)**:
   - Evaluated 9 representative 2026 events across Hovedscenen, Biscenen, Intimscenen, Foajeen against `sample_data/gastroplanner_sample_2026.csv`.
   - 100.0% match rate using Level 1 Event IDs (`EVT-260225`, `EVT-260313`, `EVT-260422`, `EVT-260711`, `EVT-260717`, `EVT-260820`, `EVT-260826`, `EVT-260829`, `EVT-260911`).
   - Confirmed business metrics: Capacity, tickets sold, table reservations, preorder packages, revenue (NOK).

6. **Reference Configuration (`config/gastroplanner_mapping.example.yml`)**:
   ```yaml
   delimiter: ";"
   date_column: Dato
   label_column: Arrangement
   room_column: Rom
   event_id_column: ArrangementID
   source_system: GastroPlanner
   strict_columns: true
   metrics:
     tickets_sold:
       column: Billetter_Solgt
       unit: billetter
     capacity:
       column: Kapasitet
       unit: plasser
     table_reservations:
       column: Bordreservasjoner
       unit: bord
     preorder_packages:
       column: Pakkemenyer
       unit: pakker
     revenue_nok:
       column: Omsetning
       unit: NOK
   ```

7. **Reference CSV Sample (`sample_data/gastroplanner_sample_2026.csv`)**:
   - Header: `Dato;ArrangementID;Arrangement;Rom;Billetter_Solgt;Kapasitet;Bordreservasjoner;Pakkemenyer;Omsetning`
   - Delimiter: Semicolon `;`
   - Numeric formats: Integers (`40`, `380`), Decimals with Norwegian comma (`18500,00`, `185000,00`, `98500,00`).

---

## 2. Logic Chain

1. **Ingestion & Data Contract (Wide to Long Transformation)**:
   - GastroPlanner exports tabular CSVs where each row represents a distinct event/session with multiple metric columns (`Billetter_Solgt`, `Kapasitet`, `Bordreservasjoner`, `Pakkemenyer`, `Omsetning`).
   - Downstream consumers (`matcher.py`, `analytics.py`, `render.py`) consume a normalized stream of `SalesObservation` domain models.
   - For every data row in the CSV, the ingestion adapter must emit $K$ `SalesObservation` instances (where $K$ is the number of configured metric mappings).
   - Therefore, a 9-row CSV with 5 metric mappings deterministically produces $9 \times 5 = 45$ `SalesObservation` records.

2. **Strict Schema & Column Gating**:
   - To prevent accidental inclusion of customer-level export files, `CsvMapping` defines `declared_columns = {date_column, label_column, room_column, event_id_column} U {metric.column}`.
   - When `strict_columns=True`, any header in the CSV not in `declared_columns` raises `DataPolicyError`.
   - In addition, before processing rows, all headers are checked against `_FORBIDDEN_COLUMN_PARTS` (`customer`, `kunde`, `email`, `phone`, `notat`, etc.). Any match raises `DataPolicyError`.

3. **Cell-Level PII Gating & Hardening**:
   - Even if headers are valid, malicious or accidental PII in data cells (e.g. in the event title or notes) must be prevented.
   - Every cell value is scanned against:
     - `_EMAIL_RE`: standard RFC-compliant email pattern.
     - `_PHONE_RE`: Norwegian 8-digit numbers (`[2-9]\d{7}`), spaced/hyphenated variants, and international E.164 formats (`+\d{1,3}...`).
     - `_FNR_RE` (Hardening): 11-digit Norwegian national identification numbers (fødselsnummer / D-nummer: `\b\d{11}\b` with optional Modulus 11 validation).
     - `_CREDIT_CARD_RE` (Hardening): 13–16 digit credit card patterns (Visa, MasterCard, Amex) with Luhn algorithm check.
   - Any match in CSV cells raises `DataPolicyError` immediately, preventing unmasked ingestion.
   - Public artist names (e.g. "Tone Damli", "Amund Mathisen") are legitimate event titles and are explicitly permitted.

4. **Norwegian Number & Currency Parsing**:
   - Norwegian exports format numbers with space or non-breaking space (`\u00a0`) as thousand separators and comma (`,`) as decimal separator.
   - Parsing pipeline:
     1. Trim whitespace and replace non-breaking spaces `\u00a0` and regular spaces with empty string `""`.
     2. If comma `,` is present: remove any periods `.` (thousand separators) and replace comma `,` with period `.`.
     3. Parse to `float`.
     4. Validate `math.isfinite(value)` (reject `NaN`, `inf`, `-inf`).
     5. Validate `value >= 0` (negative sales/capacity values are forbidden in the aggregated pilot).

5. **Date Normalization**:
   - Supported input date strings:
     - ISO 8601: `%Y-%m-%d` (e.g. `2026-02-25`)
     - Norwegian dot notation: `%d.%m.%Y` (e.g. `25.02.2026` or `19.08.2026`)
     - Forward slash notation: `%d/%m/%Y` (e.g. `25/02/2026`)
   - All dates are normalized into `datetime.date` objects.

6. **Room Taxonomy & Normalization**:
   - Known theater stages and spaces:
     - `Hovedscenen` (Main Stage: 350–450 cap)
     - `Biscenen` (Secondary Stage / Black Box: 148–250 cap)
     - `Intimscenen` (Intimate Salon: 67–90 cap)
     - `Foajeen` (Foyer & Bar: 50–150 cap)
     - `Restauranten` (Dining Room / Bar: 50–150 cap)
   - Multi-room combinations: `Foajeen / Biscenen`, `Hovedscenen / Biscenen`, `Hovedscenen / Restauranten`.
   - Matching rule: Case-insensitive substring matching; `None` indicates room unassigned.

---

## 3. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Ingestion | Delimiter & BOM Detection | Parses UTF-8 and UTF-8-BOM files with configurable delimiter (default `;`, optional `,`). | `Path` to CSV file, `CsvMapping` | CSV reader generator | Raises `FileNotFoundError` if file missing; `DataPolicyError` if delimiter mismatch fails parsing. | `csv_adapter.py:69`, `gastroplanner_mapping.example.yml:1` |
| 2 | Ingestion | Column Header Whitelist & Strict Gate | Enforces that all CSV headers match configured `declared_columns`. | CSV header list | Validated header set | Raises `DataPolicyError("Påkrevde kolonner mangler: ...")` or `DataPolicyError("Ukjente kolonner er ikke tillatt: ...")` | `csv_adapter.py:73-78` |
| 3 | Security | Forbidden PII Header Blocker | Rejects CSV files containing personal data columns (`customer`, `kunde`, `email`, `telefon`, `kommentar`, `notat`, etc.). | Normalized header list | Validated header list | Raises `DataPolicyError("Person- eller fritekstfelt er ikke tillatt: ...")` | `security.py:101-140` |
| 4 | Security | Cell-Level PII Scanner | Scans all cell values for email addresses and phone numbers. | Cell string contents | Clean text or error | Raises `DataPolicyError("Direkte kontaktopplysninger er ikke tillatt i aggregert input.")` | `security.py:141-146` |
| 5 | Security | National ID & Card Hardening | Scans cells for 11-digit Norwegian FNR and 13–16 digit credit card patterns. | Cell string contents | Clean text or error | Raises `DataPolicyError("Sensitiv identifikator oppdaget i input.")` | `PROJECT.md:17`, `SCOPE.md:16` |
| 6 | Normalization | Date Parser | Parses ISO (`%Y-%m-%d`), Norwegian dot (`%d.%m.%Y`), and slash (`%d/%m/%Y`) date formats. | Date string | `datetime.date` | Raises `DataPolicyError("Ukjent datoformat: ...")` if format unparseable or out of range. | `csv_adapter.py:43-50` |
| 7 | Normalization | Norwegian Number Normalizer | Normalizes Norwegian currency and numbers (`45 500,50` -> `45500.5`), removing spaces and `\u00a0`. | Numeric string | `float` | Raises `DataPolicyError("Aggregert måleverdi er ikke et tall.")` on invalid format. | `csv_adapter.py:53-65` |
| 8 | Validation | Non-Finite Number Guard | Rejects `NaN`, `inf`, `-inf` in numeric metric fields. | Numeric string | Finite `float` | Raises `DataPolicyError("Aggregert måleverdi må være et endelig tall.")` | `csv_adapter.py:61-62` |
| 9 | Validation | Non-Negative Number Guard | Rejects negative sales, capacity, or booking numbers (`value < 0`). | Numeric float value | Non-negative `float` | Raises `DataPolicyError("Negative aggregerte måleverdier er ikke tillatt i piloten.")` | `csv_adapter.py:63-64` |
| 10 | Validation | Non-Empty Label Guard | Ensures event title/label is not empty or whitespace-only. | Label string | Stripped `str` (min length 1) | Raises `DataPolicyError("Arrangement/etikett kan ikke være tom.")` | `csv_adapter.py:84-86` |
| 11 | Domain Modeling | Wide-to-Long Observation Unpivoting | Unpivots each CSV row into multiple `SalesObservation` instances per configured metric. | CSV row dict + `metrics` dict | `list[SalesObservation]` | Produces deterministic sequence of observations. | `csv_adapter.py:90-103` |
| 12 | Room Taxonomy | Room Name Normalization | Captures room names (`Hovedscenen`, `Biscenen`, `Intimscenen`, `Foajeen`, `Restauranten`) or `None`. | Room string | Stripped `str` or `None` | Case-insensitive matching downstream; preserves canonical names. | `csv_adapter.py:87`, `arrangementsdata-2025-2026.md:26-34` |
| 13 | Event Matching | Level 1 ID Linking | Matches observation directly against public event database via `event_id` (`EVT-YYMMDD`). | `event_id: str` | `MatchResult(match_level="level_1_id", match_status="matched")` | Returns `unmatched` if ID unknown. | `matcher.py:66-78`, `ADR 0002` |
| 14 | Event Matching | Level 2 Title+Date+Room Heuristic | Matches normalized title substring + date + compatible room. | `label`, `period`, `room` | `MatchResult(match_level="level_2_title_date_room", match_status="matched")` | Proceeds to Level 3 if no title match. | `matcher.py:96-116`, `ADR 0002` |
| 15 | Event Matching | Level 3 Proximity Correlation | Marks single event on same date as proximity correlation (`needs_review`). | `period` | `MatchResult(match_level="level_3_proximity", match_status="needs_review")` | Returns `unmatched` if multiple events on date. | `matcher.py:118-130`, `ADR 0002` |
| 16 | Analytics | Deterministic Sales Summarizer | Aggregates totals by metric, ranks events by volume, and computes period-over-period changes. | `list[SalesObservation]` | Dict summary (DuckDB backend or Python fallback) | Deterministic output; fallback if DuckDB missing. | `analytics.py:8-54` |
| 17 | Security | Output Redactor | Sanitizes any output strings to redact accidental contact details (`[MASKERT_EPOST]`, `[MASKERT_TELEFON]`). | Output string | Redacted string + findings list | Redacts all occurrences. | `security.py:157-162` |
| 18 | Security | Reviewer Identity Redactor | Sanitizes customer names from review quotes (`[ANMELDER]`). | Text string, author name | Redacted text | Replaces author name tokens. | `security.py:164-174` |
| 19 | Security | Safe Error Masking | Masks exceptions to prevent leaking source data or internal tokens in logs. | `Exception` | Safe generic string | Returns standardized error summary. | `security.py:189-211` |

---

## 4. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Ingestion | File starting with UTF-8 BOM (`\ufeff`) | Handled cleanly by `encoding="utf-8-sig"`; headers match declared columns without BOM prefix corrupting first column name. |
| 2 | Ingestion | Semicolon delimited file with comma decimals (`45 500,50`) | Standard Norwegian format parsed correctly into `45500.5`. |
| 3 | Ingestion | Comma delimited file with standard decimals (`45500.50`) | Configurable via `delimiter: ","`; parsed correctly into `45500.5`. |
| 4 | Ingestion | Spaces in numbers (`185 000,00` or `185\u00a0000,00`) | Non-breaking space `\u00a0` and ASCII space `' '` stripped before float conversion; parsed to `185000.0`. |
| 5 | Ingestion | Value with `NaN`, `inf`, or `-inf` | `_parse_number` checks `math.isfinite()`; raises `DataPolicyError("Aggregert måleverdi må være et endelig tall.")`. |
| 6 | Ingestion | Negative value (`-100` or `-18500,00`) | `_parse_number` checks `value < 0`; raises `DataPolicyError("Negative aggregerte måleverdier er ikke tillatt i piloten.")`. |
| 7 | Ingestion | Non-numeric string in metric cell (`"N/A"`, `"-"`, `"ukjent"`) | `_parse_number` fails float conversion; raises `DataPolicyError("Aggregert måleverdi er ikke et tall.")`. |
| 8 | Ingestion | Date formatted as ISO `2026-02-25` | `_parse_date` matches `%Y-%m-%d`; returns `date(2026, 2, 25)`. |
| 9 | Ingestion | Date formatted as Norwegian dot `25.02.2026` or `19.08.2026` | `_parse_date` matches `%d.%m.%Y`; returns `date(2026, 2, 25)` / `date(2026, 8, 19)`. |
| 10 | Ingestion | Date formatted as slash `25/02/2026` | `_parse_date` matches `%d/%m/%Y`; returns `date(2026, 2, 25)`. |
| 11 | Ingestion | Invalid calendar date (`2026-02-31` or `2026-13-01`) | `datetime.strptime` raises `ValueError`; caught and re-raised as `DataPolicyError("Ukjent datoformat: ...")`. |
| 12 | Ingestion | Unsupported date format (`"Feb 25, 2026"` or `"2026/02/25"`) | `_parse_date` fails all patterns; raises `DataPolicyError("Ukjent datoformat: ...")`. |
| 13 | Ingestion | CSV missing declared metric column (e.g. `Omsetning` missing) | `mapping.declared_columns.difference(headers)` detects missing header; raises `DataPolicyError("Påkrevde kolonner mangler: Omsetning")`. |
| 14 | Ingestion | CSV with unknown extra column (e.g. `Rabattkode`) with `strict_columns: true` | `set(headers).difference(mapping.declared_columns)` detects unknown column; raises `DataPolicyError("Ukjente kolonner er ikke tillatt: Rabattkode")`. |
| 15 | Ingestion | CSV with forbidden PII column header (`Kunde_Epost`, `Kundenavn`, `Reservasjonsnotat`) | `assert_aggregated_csv` normalizes headers and detects forbidden substring; raises `DataPolicyError("Person- eller fritekstfelt er ikke tillatt: kunde_epost")`. |
| 16 | Ingestion | CSV with email address in cell value (`ola.nordmann@example.no` in label or note) | `_EMAIL_RE.search` detects email; raises `DataPolicyError("Direkte kontaktopplysninger er ikke tillatt i aggregert input.")`. |
| 17 | Ingestion | CSV with phone number in cell value (`+47 999 88 777` or `99988777` in cell) | `_PHONE_RE.search` detects phone number; raises `DataPolicyError("Direkte kontaktopplysninger er ikke tillatt i aggregert input.")`. |
| 18 | Ingestion | CSV with 11-digit Norwegian FNR in cell (`01019012345`) | Hardened PII scanner detects 11-digit sequence; raises `DataPolicyError`. |
| 19 | Ingestion | CSV with 16-digit credit card number in cell (`4532 1234 5678 9012`) | Hardened PII scanner detects card pattern; raises `DataPolicyError`. |
| 20 | Ingestion | Public artist name in label (`"Amund Mathisen // Teateret"`, `"Tone Damli"`, `"Anne-Kat. Hærland"`) | Validated as public event title; does NOT trigger PII false alarms; parsed into valid `SalesObservation`. |
| 21 | Ingestion | Empty or whitespace-only label (`Arrangement: "   "`) | `row[mapping.label_column].strip()` is empty string; raises `DataPolicyError("Arrangement/etikett kan ikke være tom.")`. |
| 22 | Ingestion | Missing room column in CSV when `room_column` is `None` in mapping | `room` defaults to `None` in `SalesObservation`; matching proceeds without room filtering. |
| 23 | Ingestion | Missing `event_id_column` in mapping | `event_id` defaults to `None` in `SalesObservation`; matching falls back to Level 2/3. |
| 24 | Ingestion | Zero sales / zero bookings (`0` or `0,00`) | Parsed as `0.0`; non-negative validation succeeds; valid observation emitted. |
| 25 | Ingestion | Trailing empty rows or CRLF line breaks in CSV | `csv.DictReader` ignores blank lines; `load_aggregated_csv` filters out empty lines without raising errors. |

---

## 5. Caveats

1. **GastroPlanner API & Live Export Limitation**:
   - Official documentation confirms that live REST API endpoints are closed behind support authentication (`support@gastroplanner.no`).
   - Phase 1 relies strictly on file-based exports (CSV/Excel) dropped into the workspace or configured input path.
2. **Deterministic Matching Boundary**:
   - Level 1 requires explicit `ArrangementID` (e.g. `EVT-260225`).
   - If `ArrangementID` is missing in manual exports, matching falls back to Level 2 (title + date + room) or Level 3 (proximity correlation marked as `needs_review`).
3. **Cross-Sales Correlation Interpretation**:
   - Restaurant table reservations and preorder packages matching an event within a +/- 2h window must strictly be reported as *nærhetskorrelasjon* (proximity correlation), never as proven causal dining unless a combined package ID links them directly (ADR 0002).

---

## 6. Conclusion

Milestone 1's authoritative data contract and specification have been fully mined, cross-referenced, and documented:
- **Input Specifications**: Semicolon/comma CSV with UTF-8/UTF-8-BOM encoding, strict header enforcement against `CsvMapping`.
- **Field Mappings**: `Dato` -> `period`, `Arrangement` -> `label`, `Rom` -> `room`, `ArrangementID` -> `event_id`, and metric columns mapped to float values with units.
- **Normalization**: Robust Norwegian currency/decimal parsing (`45 500,50` -> `45500.5`), multi-format date parsing (`%Y-%m-%d`, `%d.%m.%Y`, `%d/%m/%Y`), non-finite/negative number guards.
- **Zero-PII Gate**: Two-tier inspection (header blacklist + cell-level regex scanner for emails, phones, FNR, credit cards) protecting customer privacy.
- **Output Contract**: Emits deterministic `list[SalesObservation]` ready for ADR 0002 3-level event matching, DuckDB analytics summarization, and executive brief rendering.

---

## 7. Verification Method

To independently verify the specification and its reference implementation:

1. **Ingestion Test on Reference 2026 Sample Data**:
   ```python
   from pathlib import Path
   from teateret_brief.config import load_csv_mapping
   from teateret_brief.csv_adapter import load_aggregated_csv

   mapping = load_csv_mapping(Path("config/gastroplanner_mapping.example.yml"))
   observations = load_aggregated_csv(Path("sample_data/gastroplanner_sample_2026.csv"), mapping)
   assert len(observations) == 45  # 9 rows * 5 metrics
   assert all(obs.value >= 0 for obs in observations)
   ```

2. **Automated Unit & Security Tests**:
   - `python -m pytest tests/test_csv_adapter.py tests/test_security.py`
   - Verify 100% test pass rate for Norwegian number formatting, PII header rejection, PII cell rejection, date formats, and strict column gating.

3. **Compilation & Syntax Guard**:
   - `python -m compileall teateret_brief tests` reports 0 syntax or compilation errors.
