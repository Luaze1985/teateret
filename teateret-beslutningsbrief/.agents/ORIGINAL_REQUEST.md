# Original User Request

## 2026-08-20T07:10:58Z

Build an automated, production-ready weekly decision brief engine for Teateret in Kristiansand that ingests aggregated GastroPlanner data, enriches it with public event history (129 events across 2025–2026) and external market/weather signals, and deterministically produces executive-level recommendations for theater leadership (Amir).

Working directory: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief
Integrity mode: development

## Requirements

### R1. GastroPlanner Aggregated Ingestion & Schema Adaptation
The system must parse, validate, and normalize aggregated CSV/Excel exports from GastroPlanner with zero personal data (PII) leakage. Columns representing rooms, event IDs, tickets sold, capacity, table bookings, preorder packages, and gross revenue must be handled robustly with explicit type checking.

### R2. Deterministic 3-Level Event Matching & Cross-Sales Synthesis
The system must match incoming sales and table reservation data against the official 129-event database (2025–2026) across all four venues (Hovedscenen, Biscenen, Intimscenen, Foajeen). Matching must strictly follow ADR 0002 (Level 1: Explicit ID; Level 2: Title+Date+Room; Level 3: Proximity indication marked as correlation).

### R3. External Context Enrichment (Weather, School Holidays & City Events)
The system must integrate open, non-authenticated public signals (MET.no weather forecasts for Kristiansand, Agder school holiday calendar, and major city event clashes) to contextualize demand fluctuations and forecast weekend restaurant/box office volume.

### R4. Automated Decision Brief Rendering & Security Audit
The engine must compute capacity utilization, identify program gaps on weekdays, calculate cross-sales signals, and format a human-in-the-loop draft (Markdown, HTML, email text) with up to 3 prioritized operational recommendations, verified by a strict PII and schema scanner.

## Acceptance Criteria

### Data & Matching Quality
- [ ] Ingests `sample_data/gastroplanner_sample_2026.csv` without raising PII or schema errors.
- [ ] Achieves >= 90 % matching rate against the 129 verified 2025–2026 event dataset.
- [ ] Zero instances of customer/employee personal identifiable information (emails, phone numbers, notes) in generated output files.

### Business & Operational Output
- [ ] Generates a complete decision brief in `outputs/` or `runs/<id>/` addressing:
  1. Room/stage capacity utilization (highlighting sold-out vs underperforming shows).
  2. Estimated restaurant cross-sales correlation (+/- 2h window).
  3. Actionable marketing/staffing recommendations for upcoming weeks.
- [ ] Includes automated audit trail (`manifest.json`) containing SHA-256 hashes of all inputs and generated artifacts.

### Automated Test Suite
- [ ] `python -m pytest tests/` passes 100 % of unit and integration tests.
- [ ] `python -m compileall teateret_brief tests` reports zero syntax or type compilation errors.
