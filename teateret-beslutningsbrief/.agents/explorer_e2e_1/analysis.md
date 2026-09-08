# E2E Test Suite Specification: R1 (GastroPlanner Ingestion) & R2 (Deterministic Matching & Cross-Sales)

## Executive Summary
This document defines the comprehensive opaque-box and requirement-driven test specifications for:
1. **R1: GastroPlanner Ingestion & Zero-PII Schema Adaptation** (Delimiters, encodings, date normalization, Norwegian currency/numbers, column whitelisting, PII/FNR/Credit Card scanning).
2. **R2: Deterministic 3-Level Event Matching & Cross-Sales Synthesis** (Level 1 ID matching, Level 2 Title+Date+Room heuristic matching, Level 3 Proximity/Nærhetskorrelasjon, Batch evaluation metrics >=90%, Cross-sales correlation +/- 2h).
3. **Boundary Value Analysis (BVA), Edge Cases & Adversarial Injection Payloads**.
4. **Tier 3 Pairwise Combinatorial Test Suite & Tier 4 Real-World Scenario Specs**.

---

# 1. R1: GastroPlanner Ingestion & Zero-PII Schema Specification

### 1.1 Ingestion Contracts & Data Architecture
- **Adapter Function**: `load_aggregated_csv(path: Path, mapping: CsvMapping) -> list[SalesObservation]`
- **Mapping Model**: `CsvMapping`
  - `delimiter: str` (Default `";"`, supports `","`)
  - `date_column: str`
  - `label_column: str`
  - `room_column: str | None = None`
  - `event_id_column: str | None = None`
  - `metrics: dict[str, MetricMapping]` where `MetricMapping(column: str, unit: str)`
  - `source_system: str = "GastroPlanner"`
  - `strict_columns: bool = True`
- **Domain Observation Model**: `SalesObservation`
  - `period: date`
  - `label: str`
  - `metric: str`
  - `value: float`
  - `unit: str`
  - `source_system: str`
  - `room: str | None`
  - `event_id: str | None`
  - `match_status: Literal["matched", "needs_review", "unmatched"]`

---

### 1.2 Detailed Feature Tests & Assertions (R1)

#### Test Case R1.1: Semicolon Delimiter & Norwegian Character Encoding
- **Input**: CSV file encoded in `utf-8-sig` (with UTF-8 BOM) using `;` delimiter:
  ```csv
  Dato;ArrangementID;Arrangement;Rom;Billetter_Solgt;Kapasitet;Bordreservasjoner;Pakkemenyer;Omsetning
  2026-02-25;EVT-260225;Speed date 40–59;Foajeen;40;40;35;20;18500,00
  2026-08-29;EVT-260829;Baldrian og Musa – Luft og kjærlighet;Intimscenen;85;90;20;10;24500,00
  ```
- **Assertions**:
  - `len(observations) == 10` (5 metrics × 2 rows).
  - Row 0 `period == date(2026, 2, 25)`, `event_id == "EVT-260225"`, `label == "Speed date 40–59"`, `room == "Foajeen"`.
  - Row 1 `label == "Baldrian og Musa – Luft og kjærlighet"`, `room == "Intimscenen"`.
  - Character `æ`, `ø`, `å`, and en-dash `–` preserved with zero corruption or encoding replacement characters (`\ufffd`).

#### Test Case R1.2: Comma Delimiter Support & Standard UTF-8
- **Input**: CSV file with `,` delimiter and standard UTF-8 (no BOM):
  ```csv
  Dato,ArrangementID,Arrangement,Rom,Billetter_Solgt,Kapasitet,Bordreservasjoner,Pakkemenyer,Omsetning
  2026-03-13,EVT-260313,Svanesjøen,Hovedscenen,380,400,120,65,185000.00
  ```
- **Mapping**: `CsvMapping(delimiter=",", ...)`
- **Assertions**:
  - Successfully parses 5 `SalesObservation` objects.
  - `observations[0].value == 380.0` (tickets_sold).
  - `observations[4].value == 185000.0` (revenue_nok).

#### Test Case R1.3: Multi-Format Date Normalization
- **Supported Formats**: `%Y-%m-%d`, `%d.%m.%Y`, `%d/%m/%Y`.
- **Test Matrix**:
  | Input Date String | Pattern Matched | Expected `date` Object |
  |---|---|---|
  | `2026-07-17` | `%Y-%m-%d` | `date(2026, 7, 17)` |
  | `17.07.2026` | `%d.%m.%Y` | `date(2026, 7, 17)` |
  | `17/07/2026` | `%d/%m/%Y` | `date(2026, 7, 17)` |
  | ` 2026-07-17 ` | `%Y-%m-%d` (after strip) | `date(2026, 7, 17)` |
- **Assertions**:
  - All format variations resolve to identical `date(2026, 7, 17)`.
  - Invalid formats (`"2026/07/17"`, `"17-07-2026"`, `"17. juli 2026"`, `"invalid"`) raise `DataPolicyError("Ukjent datoformat: ...")`.

#### Test Case R1.4: Norwegian Currency & Decimal Formatting Normalization
- **Formatting Scenarios**:
  - Norwegian decimal comma: `45 500,50` -> `45500.5`
  - Non-breaking space: `45\u00a0500,50` -> `45500.5`
  - Thousands separator dots: `185.000,00` -> `185000.0`
  - Compact notation: `185000,00` -> `185000.0`
  - Integer / standard float: `380` -> `380.0`, `380.00` -> `380.0`
  - Zero values: `0`, `0,00`, `0.0` -> `0.0`
- **Assertions**:
  - Returned values are strictly `float` instances.
  - `math.isfinite(val) is True`.

#### Test Case R1.5: Strict Column Whitelist & Unknown Column Rejection
- **Input**: CSV with unexpected extra column `Intern_Kommentar`:
  ```csv
  Dato;Arrangement;Reservasjoner;Intern_Kommentar
  19.08.2026;Sommerkveld;120;Viktig VIP
  ```
- **Assertions**:
  - When `strict_columns=True`: Raises `DataPolicyError` matching pattern `Ukjente kolonner er ikke tillatt: Intern_Kommentar`.
  - When `strict_columns=False`: Drops `Intern_Kommentar` without error.

#### Test Case R1.6: PII Column Blacklist Gating
- **Forbidden Column Tokens**: `customer`, `customer_name`, `kunde`, `kundenavn`, `guest`, `guest_name`, `email`, `e-post`, `phone`, `telefon`, `address`, `adresse`, `comment`, `kommentar`, `reservation_note`, `reservasjonsnotat`.
- **Test Variations**:
  - `Kundenavn` -> raises `DataPolicyError("Person- eller fritekstfelt er ikke tillatt: kundenavn")`
  - `Kunde_Epost` -> raises `DataPolicyError("Person- eller fritekstfelt er ikke tillatt: kunde_epost")`
  - `Gjest_Telefonnummer` -> raises `DataPolicyError("Person- eller fritekstfelt er ikke tillatt: gjest_telefonnummer")`
  - `Reservasjonsnotat` -> raises `DataPolicyError("Person- eller fritekstfelt er ikke tillatt: reservasjonsnotat")`

#### Test Case R1.7: Deep Cell-Level PII & Secret Scanning
- **Rule**: Even if header names are whitelisted (e.g. `Arrangement`), if any cell contains contact data or personal identifiers, ingestion is blocked immediately.
- **Payloads Tested**:
  - Email in label: `"Svanesjøen (kontakt: lars.eriksen@example.com)"` -> `DataPolicyError("Direkte kontaktopplysninger er ikke tillatt i aggregert input.")`
  - Norwegian phone in label: `"Bordreservasjon for 91234567"` -> `DataPolicyError`
  - International phone in label: `"+47 987 65 432"` -> `DataPolicyError`
  - Norwegian 11-digit FNR (Fødselsnummer): `"Arrangement 120385 12345"` -> `DataPolicyError`
  - Credit Card Number: `"Betalt med 4532 0150 1234 5678"` -> `DataPolicyError`

---

# 2. R2: Deterministic 3-Level Matching & Cross-Sales Synthesis Specification

### 2.1 Matching Architecture & ADR 0002 Levels
```
SalesObservation
       │
       ▼
[ Level 1: Explicit ID Matching ] ── (ID matches public_events.event_id) ──► MatchResult(status="matched", level="level_1_id")
       │ (No ID or ID not found)
       ▼
[ Level 2: Title + Date + Room ] ── (Normalized title & date & room agree) ──► MatchResult(status="matched", level="level_2_title_date_room")
       │ (No title match on date)
       ▼
[ Level 3: Proximity / Single Event ] ── (Exactly 1 event on date) ──► MatchResult(status="needs_review", level="level_3_proximity")
       │ (0 or 2+ events on date)
       ▼
[ Unmatched ] ──────────────────────────────────────────────────────────► MatchResult(status="unmatched", level="none")
```

---

### 2.2 Detailed Feature Tests & Assertions (R2)

#### Test Case R2.1: Level 1 Explicit ID Match
- **Public Events**:
  ```python
  PublicEvent(event_id="EVT-260225", date=date(2026, 2, 25), title="Speed date 40–59", room="Foajeen")
  ```
- **Observation**:
  `SalesObservation(period=date(2026, 2, 25), label="Gastro Speeddate Avvikende Tekst", event_id="EVT-260225", metric="revenue_nok", value=18500.0, unit="NOK")`
- **Assertions**:
  - `result.match_status == "matched"`
  - `result.match_level == "level_1_id"`
  - `result.matched_event_title == "Speed date 40–59"`
  - `result.reason == "Eksakt arrangements-ID EVT-260225"`

#### Test Case R2.2: Level 2 Title + Date + Room Match
- **Public Events**:
  ```python
  PublicEvent(event_id=None, date=date(2026, 7, 17), title="Sommerstandup med Fire halvkjente fjes", room="Hovedscenen")
  ```
- **Observation**:
  `SalesObservation(period=date(2026, 7, 17), label="Sommerstandup", room="Hovedscenen", metric="tickets_sold", value=290.0, unit="billetter")`
- **Assertions**:
  - `result.match_status == "matched"`
  - `result.match_level == "level_2_title_date_room"`
  - `result.matched_event_title == "Sommerstandup med Fire halvkjente fjes"`
  - Substring matching correctly identifies `"sommerstandup"` inside `"sommerstandup med fire halvkjente fjes"`.

#### Test Case R2.3: Level 2 Synonym Mapping Resolution
- **Synonyms Dict**: `{"Jazzfestival": "Kristiansand Jazzfestival 26"}`
- **Observation**:
  `SalesObservation(period=date(2026, 8, 20), label="Jazzfestival", room="Biscenen", metric="tickets_sold", value=140.0, unit="billetter")`
- **Public Event**:
  `PublicEvent(date=date(2026, 8, 20), title="Kristiansand Jazzfestival 26 (AiR m.fl.)", room="Biscenen")`
- **Assertions**:
  - `result.match_status == "matched"`
  - `result.match_level == "level_2_title_date_room"`

#### Test Case R2.4: Level 2 Room Disambiguation for Multi-Show Dates
- **Context**: On `2025-02-08`, two events occur:
  1. `Kokosbananas – Det store showet` in `Hovedscenen`
  2. `Drag Bonanza 3` in `Biscenen`
- **Observations**:
  - Obs A: `period=date(2025, 2, 8)`, `label="Kokosbananas"`, `room="Hovedscenen"` -> matches `Kokosbananas`
  - Obs B: `period=date(2025, 2, 8)`, `label="Drag Show"`, `room="Biscenen"` -> matches `Drag Bonanza 3`
- **Assertions**:
  - Room constraint prevents cross-matching between different stages on the same date.

#### Test Case R2.5: Level 3 Proximity Matching (*Nærhetskorrelasjon*)
- **Context**: Date `2026-03-13` has only 1 public event: `Svanesjøen (Etoile Ballet)`.
- **Observation**:
  `SalesObservation(period=date(2026, 3, 13), label="Kveldsrestaurant / Bordomsetning", metric="revenue_nok", value=45000.0, unit="NOK")`
- **Assertions**:
  - `result.match_status == "needs_review"`
  - `result.match_level == "level_3_proximity"`
  - `result.matched_event_title == "Svanesjøen (Etoile Ballet)"`
  - `result.reason == "Dato-nærhet: Enkelt arrangement 'Svanesjøen (Etoile Ballet)' på samme dato"`

#### Test Case R2.6: Unmatched on Multi-Event Date without Title Match
- **Context**: Date `2026-10-30` has 3 public events (`Charlie og sjokoladefabrikken`, `Standup med Fire halvkjente fjes`, `CBRC: Beggars Blue`).
- **Observation**:
  `SalesObservation(period=date(2026, 10, 30), label="Generell Barinntekt", metric="revenue_nok", value=12000.0, unit="NOK")`
- **Assertions**:
  - `result.match_status == "unmatched"`
  - `result.match_level == "none"`
  - `result.matched_event_title is None`
  - `result.reason == "Flere arrangementer (3) på dato uten tittelmatch"`

#### Test Case R2.7: Batch Evaluation & >=90% Match Rate Benchmark
- **Input**: `sample_data/gastroplanner_sample_2026.csv` mapped against the 129 verified event dataset.
- **Assertions**:
  - `report = matcher.evaluate_all(observations)`
  - `report.total_observations == 9` (deduplicated by `(period, label, room, event_id)`).
  - `report.matched_count == 9` (100% match rate).
  - `report.needs_review_count == 0`
  - `report.unmatched_count == 0`
  - `report.match_rate_percent >= 90.0` (Acceptance Criteria fulfilled).

#### Test Case R2.8: Cross-Sales Correlation Window Synthesis (+/- 2h)
- **Calculation Logic**:
  - For stage event on `date`:
    - `tickets = sum(value where metric == "tickets_sold")`
    - `capacity = sum(value where metric == "capacity")`
    - `tables = sum(value where metric == "table_reservations")`
    - `packages = sum(value where metric == "preorder_packages")`
    - `dining_cross_sales_rate = packages / tickets`
    - `table_cross_sales_rate = tables / tickets`
    - `capacity_utilization = tickets / capacity`
- **Test Assertions on Sample 2026 Data**:
  - Svanesjøen (2026-03-13): Tickets 380/400 (95.0%), Tables 120 (31.6%), Packages 65 (17.1%).
  - Fotball-VM Norge-England (2026-07-11): Tickets 350/350 (100.0%), Tables 150 (42.9%), Packages 90 (25.7%).
  - Sommerstandup (2026-07-17): Tickets 290/350 (82.9%), Tables 95 (32.8%), Packages 45 (15.5%).
  - Speed date 40-59 (2026-02-25): Tickets 40/40 (100.0%), Tables 35 (87.5%), Packages 20 (50.0%).
  - All signals rendered with label `indication` / *nærhetskorrelasjon* in compliance with ADR 0002.

---

# 3. Boundary Cases, Corner Conditions & Adversarial Payloads

### 3.1 Numeric Boundaries (BVA)
| Test ID | Input Value | Expected Result | Reason / Boundary |
|---|---|---|---|
| BVA-NUM-1 | `0` | `0.0` (PASS) | Minimum non-negative integer |
| BVA-NUM-2 | `0,00` | `0.0` (PASS) | Minimum non-negative decimal |
| BVA-NUM-3 | `-0.01` / `-1` | `DataPolicyError` (REJECT) | Negative numbers forbidden in pilot |
| BVA-NUM-4 | `1 000 000 000,00` | `1000000000.0` (PASS) | Large revenue boundary |
| BVA-NUM-5 | `NaN` / `nan` | `DataPolicyError` (REJECT) | Non-finite float |
| BVA-NUM-6 | `inf` / `-inf` | `DataPolicyError` (REJECT) | Infinite values |
| BVA-NUM-7 | `""` / ` ` | `DataPolicyError` (REJECT) | Missing metric value |
| BVA-NUM-8 | `Utsolgt` | `DataPolicyError` (REJECT) | Text in numeric column |

### 3.2 Date Boundaries (BVA)
| Test ID | Date String | Expected Result | Reason / Boundary |
|---|---|---|---|
| BVA-DATE-1 | `2024-02-29` | `date(2024, 2, 29)` (PASS) | Valid leap day |
| BVA-DATE-2 | `2026-02-29` | `DataPolicyError` (REJECT) | 2026 is not a leap year |
| BVA-DATE-3 | `2028-02-29` | `date(2028, 2, 29)` (PASS) | Future leap day |
| BVA-DATE-4 | `2026-04-31` | `DataPolicyError` (REJECT) | April has 30 days |
| BVA-DATE-5 | `2025-12-31` | `date(2025, 12, 31)` (PASS) | Year-end boundary |
| BVA-DATE-6 | `2026-01-01` | `date(2026, 1, 1)` (PASS) | Year-start boundary |
| BVA-DATE-7 | `00.00.0000` | `DataPolicyError` (REJECT) | Corrupt date |

### 3.3 File & CSV Corruptions
| Test ID | Corruption Description | Expected Error / Exception |
|---|---|---|
| BVA-CSV-1 | Empty file (0 bytes) | `DataPolicyError("Påkrevde kolonner mangler: ...")` |
| BVA-CSV-2 | Unclosed quotes (`"Speed date;Foajeen...`) | `csv.Error` or `DataPolicyError` |
| BVA-CSV-3 | Row column count mismatch (5 items instead of 9) | Missing column key error -> `DataPolicyError` |
| BVA-CSV-4 | Non-existent file path | `PathPolicyError("Input finnes ikke: ...")` |
| BVA-CSV-5 | Path traversal attempt (`../../etc/passwd`) | `PathPolicyError("Stien forlater det bekreftede repoet.")` |

### 3.4 PII Injection Attack Vectors
| Test ID | Injection Vector | Injection Location | Expected Enforcement |
|---|---|---|---|
| ADV-PII-1 | Email in show title | `Arrangement` column: `"Revy (booking: sjef@teateret.no)"` | `DataPolicyError: Direkte kontaktopplysninger er ikke tillatt` |
| ADV-PII-2 | 8-digit Norwegian phone | `Arrangement` column: `"Standup ring 91234567"` | `DataPolicyError: Direkte kontaktopplysninger er ikke tillatt` |
| ADV-PII-3 | Formatted phone | `Arrangement` column: `"+47 38 00 00 00"` | `DataPolicyError: Direkte kontaktopplysninger er ikke tillatt` |
| ADV-PII-4 | 11-digit Norwegian FNR | `Arrangement` column: `"Artist FNR 01019012345"` | `DataPolicyError` |
| ADV-PII-5 | 16-digit Credit Card | `Arrangement` column: `"Ref 4532 0150 1234 5678"` | `DataPolicyError` |
| ADV-PII-6 | Forbidden column injection | Header: `Kundenavn` or `Gjeste_Epost` | `DataPolicyError: Person- eller fritekstfelt er ikke tillatt` |

---

# 4. Tier 3 Pairwise Combinatorial Test Matrix

We define 5 orthogonal dimensions for systematic pairwise testing:
- **D1 (Delimiter)**: Semicolon (`;`), Comma (`,`)
- **D2 (DateFormat)**: ISO (`%Y-%m-%d`), Dot (`%d.%m.%Y`), Slash (`%d/%m/%Y`)
- **D3 (MatchLevel)**: Level 1 (ID), Level 2 (Title+Date+Room), Level 3 (Proximity), Unmatched (None)
- **D4 (MetricSet)**: Single (Revenue only), Full Suite (Tickets, Capacity, Tables, Packages, Revenue)
- **D5 (HealthState)**: Clean, Number with Space/NBSP, Missing Optional Room/ID, PII Attempt

### Pairwise Test Cases (15 Representative Runs):
| Suite ID | D1: Delim | D2: Date | D3: Match Tier | D4: Metrics | D5: Health State | Expected Outcome |
|---|---|---|---|---|---|---|
| **PW-01** | `;` | `%Y-%m-%d` | Level 1 (ID) | Full Suite | Clean | `matched` (`level_1_id`), 5 obs per row |
| **PW-02** | `,` | `%d.%m.%Y` | Level 2 (Title) | Single (Revenue) | Number with NBSP | `matched` (`level_2_title_date_room`), clean float |
| **PW-03** | `;` | `%d/%m/%Y` | Level 3 (Proximity) | Full Suite | Missing Room/ID | `needs_review` (`level_3_proximity`) |
| **PW-04** | `,` | `%Y-%m-%d` | Unmatched | Single (Revenue) | Clean | `unmatched` (`none`) |
| **PW-05** | `;` | `%d.%m.%Y` | Level 1 (ID) | Single (Revenue) | Number with Dot Sep | `matched` (`level_1_id`), clean float |
| **PW-06** | `,` | `%d/%m/%Y` | Level 2 (Title) | Full Suite | Clean | `matched` (`level_2_title_date_room`) |
| **PW-07** | `;` | `%Y-%m-%d` | Level 2 (Synonym) | Full Suite | Clean | `matched` (`level_2_title_date_room`) |
| **PW-08** | `,` | `%d.%m.%Y` | Level 3 (Proximity) | Single (Revenue) | Clean | `needs_review` (`level_3_proximity`) |
| **PW-09** | `;` | `%d/%m/%Y` | Unmatched | Full Suite | Clean | `unmatched` (`none`) |
| **PW-10** | `,` | `%Y-%m-%d` | Level 1 (ID) | Full Suite | Number with NBSP | `matched` (`level_1_id`), clean float |
| **PW-11** | `;` | `%d.%m.%Y` | Level 1 (ID) | Full Suite | PII in Header | `DataPolicyError` (Forbidden column) |
| **PW-12** | `,` | `%d/%m/%Y` | Level 2 (Title) | Single (Revenue) | PII in Cell | `DataPolicyError` (Contact info in cell) |
| **PW-13** | `;` | `%Y-%m-%d` | Level 1 (ID) | Single (Revenue) | Negative Value | `DataPolicyError` (Negative value) |
| **PW-14** | `,` | `%d.%m.%Y` | Level 2 (Room Disambig)| Full Suite | Clean | `matched` to correct room on shared date |
| **PW-15** | `;` | `%Y-%m-%d` | Level 1 (ID) | Full Suite | Empty Label | `DataPolicyError` (Empty label) |

---

# 5. Tier 4 End-to-End Workload Scenario Specifications

### Scenario 1: Reference 2026 Multi-Format Season Run
- Ingests `sample_data/gastroplanner_sample_2026.csv` with full 5-metric schema.
- Matches against official 129 public events.
- Synthesizes stage capacity utilization (100% sellout for Speed dating & Fotball-VM; 95% for Svanesjøen; 83% for Sommerstandup).
- Calculates cross-sales table and dining package ratios.
- Verifies zero PII in generated briefs and valid `manifest.json`.

### Scenario 2: Legacy Date & Aggregated Fallback Run
- Ingests `sample_data/gastroplanner_aggregert.csv` with `%d.%m.%Y` date format.
- Evaluates Level 3 proximity matching for synthetic single events.
- Verifies DuckDB/Python fallback aggregation produces correct totals and period-over-period delta trends.

### Scenario 3: Adversarial PII Injection Defense Scenario
- Attempts ingestion of CSV containing hidden email addresses, Norwegian phone numbers, FNR tokens, and forbidden `Kundekommentar` headers.
- Verifies that pipeline immediately halts at staging, writes `errors.json` with sanitized error message, marks manifest as `blocked` / `not_publishable`, and leaves zero temporary files outside `.staging/`.
