# Handoff Report: E2E Test Suite Specification for R1 & R2

## 1. Observation
1. **GastroPlanner CSV Ingestion & Normalization (`teateret_brief/csv_adapter.py`)**:
   - `CsvMapping` (lines 19–41) defines configurable delimiters (default `";"`), date column, label column, optional `room_column` and `event_id_column`, and metric mappings.
   - `_parse_date` (lines 43–51) handles `%Y-%m-%d`, `%d.%m.%Y`, and `%d/%m/%Y`, raising `DataPolicyError("Ukjent datoformat: ...")` on failure.
   - `_parse_number` (lines 53–66) strips non-breaking space `\u00a0` and regular space, normalizes decimal commas (e.g. `45 500,50` -> `45500.5`), validates `math.isfinite(value)`, and strictly rejects negative values with `DataPolicyError("Negative aggregerte måleverdier er ikke tillatt i piloten.")`.
   - `load_aggregated_csv` (lines 68–104) checks `strict_columns` (rejecting unwhitelisted headers) and executes `assert_aggregated_csv(headers, rows)`.

2. **PII and Data Security Enforcement (`teateret_brief/security.py`)**:
   - `_FORBIDDEN_COLUMN_PARTS` (lines 101–118) blacklists tokens: `{"customer", "customer_name", "kunde", "kundenavn", "guest", "guest_name", "email", "e-post", "phone", "telefon", "address", "adresse", "comment", "kommentar", "reservation_note", "reservasjonsnotat"}`.
   - `_EMAIL_RE` (line 119) and `_PHONE_RE` (lines 120–125) scan all row values; matches trigger immediate `DataPolicyError("Direkte kontaktopplysninger er ikke tillatt i aggregert input.")`.
   - Feature 4 in `PROJECT.md` (line 17) requires extended scanning for 11-digit Norwegian FNR and 16-digit credit card patterns.

3. **Deterministic 3-Level Matching Engine (`teateret_brief/matcher.py`)**:
   - `_normalize_title` (lines 41–45) cleans case, en-dashes (`–`), hyphens (`-`), and whitespace.
   - **Level 1** (lines 66–78): Matches `observation.event_id` directly against `self._events_by_id`, returning `match_status="matched"`, `match_level="level_1_id"`.
   - **Level 2** (lines 96–116): Matches normalized title, date, and compatible room (or synonym lookup), returning `match_status="matched"`, `match_level="level_2_title_date_room"`.
   - **Level 3** (lines 118–130): Matches if exactly 1 event exists on the observation date, returning `match_status="needs_review"`, `match_level="level_3_proximity"`, reason `"Dato-nærhet: Enkelt arrangement '<title>' på samme dato"`.
   - **Unmatched** (lines 81–91, 132–141): Returns `match_status="unmatched"`, `match_level="none"`.
   - `evaluate_all` (lines 143–167) deduplicates observations by `(period, label, room, event_id)` and computes `match_rate_percent`.

4. **Authoritative Datasets**:
   - `sample_data/gastroplanner_sample_2026.csv` (11 lines, 9 events) covers all 4 stages (Hovedscenen, Biscenen, Intimscenen, Foajeen).
   - `docs/research/arrangementsdata-2025-2026.md` (lines 26–218) documents 129 verified public events (54 in 2025, 75 in 2026).
   - avstemmingsrapport `docs/research/gastroplanner-2026-avstemmingsrapport.md` confirms 100% match rate (9/9) on the 2026 sample.

---

## 2. Logic Chain
1. *From Obs 1 & Obs 2*: Ingestion correctness requires verifying delimiter flexibility (`;` and `,`), multi-format date handling, Norwegian decimal normalization, non-breaking space stripping, non-negative bounds, and strict column gating.
2. *From Obs 2*: PII protection requires testing both structural column rejections (forbidden header keywords) and adversarial cell payload injections (emails, Norwegian phone numbers, FNR, credit cards embedded in labels or room names).
3. *From Obs 3 & Obs 4*: ADR 0002 deterministic matching requires testing each level in isolation and in hierarchy:
   - Level 1 exact ID overrides title discrepancies.
   - Level 2 substring title matching and synonym mappings work across special characters and Norwegian letters (`æ, ø, å`).
   - Level 2 room constraints correctly disambiguate multi-show dates (e.g. `2025-02-08`).
   - Level 3 single-event date proximity generates `needs_review` and *nærhetskorrelasjon*.
   - Multi-event dates without title match correctly fall through to `unmatched`.
4. *From Obs 4*: Batch evaluation must deduplicate observations with multiple metric lines per event and verify the acceptance criterion: `match_rate_percent >= 90%`.
5. *From ADR 0002 & PROJECT.md*: Cross-sales correlation must evaluate table reservations and preorder packages against ticket volume and capacity within the +/- 2h window, labeling outputs as `indication` (*nærhetskorrelasjon*).

---

## 3. Caveats
- The extended FNR (11-digit) and credit card regex hardening is specified as Feature 4 in `PROJECT.md`; test suites include adversarial cases that test both current and hardened scanning behaviors.
- Schema.org event scraping (Feature 16) and external weather/holiday signals (R3) are covered in parallel tracks by explorer_e2e_2; this report focuses strictly on R1 and R2 contracts.

---

## 4. Conclusion
The test specifications for R1 and R2 are fully articulated across 4 testing tiers:
- **Tier 1 (Feature Coverage)**: 8 core test cases for delimiters, dates, numbers, column whitelist, PII cell scanning, Level 1 ID matching, Level 2 title+room matching, Level 3 proximity matching, and cross-sales synthesis.
- **Tier 2 (Boundary & Corner Cases)**: 26 boundary cases covering numeric bounds (`0`, `0,00`, `1e9`, `-0.01`, `NaN`, `inf`), date edges (leap years `2024-02-29` vs non-leap `2026-02-29`, invalid days `2026-04-31`), CSV corruptions, and adversarial PII injection payloads.
- **Tier 3 (Cross-Feature Pairwise Matrix)**: 15 orthogonal combinatorial test suites testing Delimiters × Date Formats × Match Tiers × Metric Suites × Data Health States.
- **Tier 4 (Real-World Scenarios)**: Complete end-to-end workload specifications for 2026 reference season, legacy date fallback, and adversarial PII containment.

---

## 5. Verification Method
1. **Full Pytest Execution**:
   ```bash
   python -m pytest tests/
   ```
2. **Bytecode Compilation Guard**:
   ```bash
   python -m compileall teateret_brief tests
   ```
3. **Inspect Specification Artifacts**:
   - `analysis.md`: Detailed test definitions, data tables, and assertions.
   - `tests/test_csv_adapter.py` and `tests/test_matcher.py`: Verified existing unit test baselines.
   - `sample_data/gastroplanner_sample_2026.csv`: Reference dataset for 100% matching pass.
