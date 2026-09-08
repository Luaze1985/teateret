# Scope: Milestone 1 — GastroPlanner Aggregated Ingestion & Zero-PII Schema Adaptation (R1)

## Architecture
- Ingestion of GastroPlanner CSV/Excel files into `SalesObservation` domain models.
- Strict PII filtering and column gating to ensure zero PII leakage (customer names, emails, phone numbers, notes, Norwegian FNR, credit cards).
- Support for Norwegian decimal and date formats (`45 500,50`, `%Y-%m-%d`, `%d.%m.%Y`, `%d/%m/%Y`, non-breaking spaces).
- Room mapping (Hovedscenen, Biscenen, Intimscenen, Foajeen, etc.).
- Strict adherence to `sample_data/gastroplanner_sample_2026.csv` and `docs/research/gastroplanner-2026-avstemmingsrapport.md`.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | GastroPlanner CSV Ingestion | Semicolon/comma delimiter, date parsing (%Y-%m-%d, %d.%m.%Y, %d/%m/%Y), room mapping | M1 | survey_miner_1 | DONE |
| 2 | Norwegian Number & Currency Normalizer | Parses Norwegian numbers (`45 500,50` -> `45500.5`), strips `\u00a0`, validates positive finite floats | M1 | survey_miner_1 | DONE |
| 3 | Ingestion PII & Strict Column Gate | Rejects unknown columns in strict mode and forbids PII columns (`kunde`, `email`, `phone`, `notat`) | M1 | survey_explorer_1 | DONE |
| 4 | Additional PII Hardening | Strict scanner for 11-digit Norwegian FNR and credit card patterns | M1 | survey_explorer_1 | DONE |

## Interface Contracts
### Ingestion ↔ Matcher (`csv_adapter` ↔ `matcher`)
- `load_aggregated_csv(path: Path, mapping: CsvMapping) -> list[SalesObservation]`
- `SalesObservation`: `period: date`, `label: str`, `metric: str`, `value: float`, `unit: str`, `room: str | None`, `event_id: str | None`, `source_system: str`
- Security verification: `assert_aggregated_csv(headers, rows, *, allowed_headers=None, strict=False) -> None`
- Scanner: PII scanner checking headers and values against email, phone, FNR (11-digit regex + Modulo 11 validation), and credit card regex (Luhn validation).

## Code Layout Ownership for M1
- `teateret_brief/csv_adapter.py`
- `teateret_brief/security.py`
- `teateret_brief/models.py`
- `tests/test_csv_adapter.py`
- `tests/test_security.py`
- `tests/test_csv_adapter_stress.py`
- `tests/test_security_adversarial.py`
