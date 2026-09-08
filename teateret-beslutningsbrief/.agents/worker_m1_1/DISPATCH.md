## 2026-08-20T07:25:00Z

You are worker_m1_1, the implementation worker for Milestone 1.

Your assigned working directory: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\worker_m1_1
Project root: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief
Parent conversation ID: 3b098b0f-ac4f-40c2-bd6b-42e9b79ae0bc
Original user request file: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\ORIGINAL_REQUEST.md
Project plan file: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\orchestrator\PROJECT.md
Scope file: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\sub_orch_m1\SCOPE.md

Explorer handoff files to review:
- C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\spec_miner_m1_1\handoff.md
- C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\explorer_m1_2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Boundaries & Ownership:
You exclusively own and may edit:
- `teateret_brief/csv_adapter.py`
- `teateret_brief/security.py`
- `teateret_brief/models.py`
- `tests/test_csv_adapter.py`
- `tests/test_security.py`

Tasks to Implement:
1. `teateret_brief/csv_adapter.py`:
   - Add delimiter sniffing / fallback (handles `;`, `,`, `\t` and auto mode).
   - Enhance `_parse_date` to support ISO dates (`%Y-%m-%d`), Norwegian dot dates (`%d.%m.%Y`), slash dates (`%d/%m/%Y`), and datetimes with time (`%Y-%m-%d %H:%M:%S`, `%Y-%m-%dT%H:%M:%S`, `%d.%m.%Y %H:%M`) normalizing down to `datetime.date`.
   - Fix `_parse_number`:
     - Strip all spaces (regular, NBSP `\u00a0`, NNBSP `\u202f`).
     - Handle currency tokens (`kr`, `NOK`, `kr.`, `,-` -> `,00`).
     - Disambiguate dot thousand separators (e.g. `"1.200"` -> `1200.0`, `"185.000"` -> `185000.0`, `"1.200.000,50"` -> `1200000.50`).
     - Convert blank `""` and dash `"-"` to `0.0`.
     - Validate finite (`math.isfinite`) and non-negative (`value >= 0`).
   - Add `normalize_room(raw: str | None) -> str | None` function mapping stage aliases (`Hovedsalen`, `Black Box`, `Intimscene`, `Foajé`, `Restaurant`) to canonical names (`Hovedscenen`, `Biscenen`, `Intimscenen`, `Foajeen`, `Restauranten`).
   - Add encoding fallback (`utf-8-sig` -> `cp1252`/`latin-1`).

2. `teateret_brief/security.py`:
   - Add 11-digit Norwegian FNR regex + Modulo 11 validator (`is_valid_norwegian_fnr`).
   - Add 13-19 digit Credit card regex + Luhn algorithm validator (`is_valid_luhn`).
   - Expand forbidden column headers with exact dictionary, stem matching, and domain whitelist exemptions (`Arrangementsnavn`, `Romnavn`, `Artistnavn`, `Antall_Gjester`, `Antall_Kunder`).
   - Fix `redact_reviewer_identity` with word boundary `\b` (`rf"\b{re.escape(part)}\b"`).
   - Update `assert_aggregated_csv(headers, rows, *, allowed_headers=None, strict=False)` to check forbidden headers, strict unknown header rejection, and cell-level PII scanning.
   - Update `scan_public_artifact`, `redact_contact_details`, `mask_sensitive_error` to detect/redact FNR and credit card tokens.

3. `tests/test_csv_adapter.py` & `tests/test_security.py`:
   - Expand unit tests to thoroughly cover delimiter sniffing, number parsing variations, date formats, room normalization, PII detection (emails, phones, FNRs, credit cards), forbidden column headers, domain whitelist exemptions, reviewer word boundary redaction, and ingestion of `sample_data/gastroplanner_sample_2026.csv` (asserting 45 `SalesObservation` instances).

4. Verification:
   - Run `python -m pytest tests/test_csv_adapter.py tests/test_security.py` (or `python -m unittest tests/test_csv_adapter.py tests/test_security.py`).
   - Run `python -m compileall teateret_brief tests`.
   - Ensure all tests pass with 0 errors.

5. Report:
   - Write your complete handoff report to `C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\worker_m1_1\handoff.md`.
   - Send completion message to parent with verification results.
