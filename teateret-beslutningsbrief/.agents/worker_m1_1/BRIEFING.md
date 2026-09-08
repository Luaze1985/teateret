# BRIEFING — 2026-08-20T07:31:00Z

## Mission
Implement CSV ingestion adapter and security / PII guardrails for Milestone 1 according to specifications and handoffs.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\worker_m1_1
- Original parent: 3b098b0f-ac4f-40c2-bd6b-42e9b79ae0bc
- Milestone: M1 (Ingestion & Security)

## 🔒 Key Constraints
- Exclusively own and edit: `teateret_brief/csv_adapter.py`, `teateret_brief/security.py`, `teateret_brief/models.py`, `tests/test_csv_adapter.py`, `tests/test_security.py`.
- No mock data or fake implementations; genuine robust parsing and security checks.
- Zero test failures, full lint / compileall pass.
- Self-contained handoff.md following 5-component handoff protocol.

## Current Parent
- Conversation ID: 3b098b0f-ac4f-40c2-bd6b-42e9b79ae0bc
- Updated: 2026-08-20T07:31:00Z

## Task Summary
- **What to build**:
  1. `csv_adapter.py`: Delimiter sniffing/fallback (`;`, `,`, `\t`, `auto`), multi-encoding fallback (`utf-8-sig`, `utf-8`, `cp1252`, `latin-1`), date parsing (ISO, Norwegian dot `%d.%m.%Y`, slash, datetime with timestamps), number parsing (NBSP/NNBSP whitespace stripping, currency tokens, dot thousand separator disambiguation, blank/dash to 0.0, non-negative finite validation), `normalize_room` canonical taxonomy mapping.
  2. `security.py`: 11-digit Norwegian FNR validation (Modulo 11), 13-19 digit Credit card validation (Luhn), forbidden headers exact dictionary + token/stem matching + domain whitelist exemptions (`Arrangementsnavn`, `Romnavn`, `Artistnavn`, `Antall_Gjester`, `Antall_Kunder`), word-boundary regex for reviewer redaction, updated `assert_aggregated_csv(headers, rows, *, allowed_headers=None, strict=False)`, updated `scan_public_artifact`, `redact_contact_details`, `mask_sensitive_error`.
  3. `tests/`: Comprehensive unit tests in `test_csv_adapter.py` and `test_security.py` verifying full specification and clean ingestion of `sample_data/gastroplanner_sample_2026.csv` emitting 45 `SalesObservation` instances.
- **Success criteria**: All specifications met, 100% test pass, zero regressions.
- **Interface contracts**: PROJECT.md & SCOPE.md
- **Code layout**: `teateret_brief/` and `tests/`

## Key Decisions Made
- Used Modulo 11 algorithm with weights `[3, 7, 6, 1, 8, 9, 4, 5, 2]` and `[5, 4, 3, 2, 7, 6, 5, 4, 3, 2]` for Norwegian FNR / D-nummer verification.
- Used Luhn algorithm (Mod 10) for Credit Card PAN verification across 13-19 digits.
- Applied word boundary `\b` in reviewer identity redaction to avoid mutating substrings in Norwegian words like "Januar", "Danseforestilling", and "Performance".
- Enabled `_detect_delimiter` sniffing with Sniffer fallback for auto/comma/tab formats.
- Implemented `normalize_room` with canonical venues (`Hovedscenen`, `Biscenen`, `Intimscenen`, `Foajeen`, `Restauranten`) and combined rooms support (`/`).

## Artifact Index
- DISPATCH.md — Assignment instructions
- BRIEFING.md — Situational awareness
- progress.md — Liveness & step tracking
- handoff.md — Final deliverable report

## Change Tracker
- **Files modified**:
  - `teateret_brief/csv_adapter.py`: Delimiter sniffing, encoding fallback, date/number parser hardening, `normalize_room`.
  - `teateret_brief/security.py`: FNR (mod 11), Luhn, expanded forbidden columns, domain whitelist, word boundary redaction, `assert_aggregated_csv`.
  - `tests/test_csv_adapter.py`: Unit test expansion for delimiters, encodings, dates, numbers, room normalization, reference CSV sample.
  - `tests/test_security.py`: Unit test expansion for FNR, Luhn, forbidden headers, whitelist exemptions, cell-level PII, reviewer redaction.
- **Build status**: Clean, zero compilation errors.
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pass
- **Lint status**: Clean
- **Tests added/modified**: 14 new test cases across `test_csv_adapter.py` and `test_security.py`.

## Loaded Skills
- None
