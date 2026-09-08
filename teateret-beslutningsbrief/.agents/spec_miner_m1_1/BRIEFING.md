# BRIEFING — 2026-08-20T09:23:00+02:00

## Mission
Mine authoritative requirements, contracts, and specifications for Milestone 1 (GastroPlanner CSV Ingestion, Validation, Normalization, Aggregation, and Mapping Engine).

## 🔒 My Identity
- Archetype: specification-miner
- Roles: Specification Investigator
- Working directory: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\spec_miner_m1_1
- Original parent: 3b098b0f-ac4f-40c2-bd6b-42e9b79ae0bc
- Milestone: Milestone 1 (GastroPlanner Ingestion & Normalization Engine)

## 🔒 Key Constraints
- Read-only on codebase/docs, write only to assigned agent folder `.agents/spec_miner_m1_1/`.
- Discover and document authoritative specs from reference docs, sample data, mapping configs, and data policies.
- Enumerate exact column mappings, metrics, allowable rooms, error conditions, edge cases.
- Follow 5-Component Handoff format with Features Discovered and Edge Cases tables.

## Current Parent
- Conversation ID: 3b098b0f-ac4f-40c2-bd6b-42e9b79ae0bc
- Updated: 2026-08-20T09:23:00+02:00

## Task Summary
- **What to build**: Specification report (`handoff.md`) detailing GastroPlanner CSV format, mapping rules, metric calculation rules, data policy constraints, room matching rules, and malformed input handling.
- **Success criteria**: Comprehensive, exhaustive specification covering all schemas, column types, variations, error cases, edge cases, formulas, room aliases, privacy rules. Complete 5-component handoff with Features Discovered and Edge Cases tables.
- **Interface contracts**: `load_aggregated_csv(path: Path, mapping: CsvMapping) -> list[SalesObservation]`, `assert_aggregated_csv(headers, rows) -> None`, `CsvMapping`, `SalesObservation`.
- **Code layout**: `teateret_brief/csv_adapter.py`, `teateret_brief/security.py`, `teateret_brief/models.py`.

## Key Decisions Made
- Fully mined and mapped all 19 features and 25 edge cases from authoritative specifications, sample data, and policies.
- Documented wide-to-long unpivoting ($9 \times 5 = 45$ observations on reference dataset).
- Documented Norwegian number normalization (`\u00a0`, spaces, comma decimals) and multi-format date parsing.
- Documented two-layer Zero-PII gate (header blacklist + cell regex scanning for email, phone, FNR, credit cards).

## Artifact Index
- `.agents/spec_miner_m1_1/DISPATCH.md` — Dispatch instructions
- `.agents/spec_miner_m1_1/BRIEFING.md` — Persistent briefing
- `.agents/spec_miner_m1_1/progress.md` — Progress tracker
- `.agents/spec_miner_m1_1/handoff.md` — Final comprehensive specification mining report
