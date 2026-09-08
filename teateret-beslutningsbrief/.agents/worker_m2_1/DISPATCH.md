## 2026-08-20T07:43:50Z
You are worker_m2_1 (teamwork_preview_worker) for Milestone 2.
Your working directory: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\worker_m2_1
Project root: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY FIRST STEP: Read ORIGINAL_REQUEST.md at:
C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\ORIGINAL_REQUEST.md
Also read PROJECT.md at:
C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\orchestrator\PROJECT.md
Also read SCOPE.md at:
C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\sub_orch_m2\SCOPE.md

Also read the Explorer findings:
- Explorer 1 Report: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\explorer_m2_1\handoff.md
- Explorer 2 Report: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\explorer_m2_2\handoff.md
- Explorer 3 Report: C:\Users\larse\.gemini\antigravity\brain\2bce55ac-b150-4c86-94a1-4c300d294e12\handoff_explorer_m2_3.md

File Write Boundaries:
You own and may edit the following files:
- `teateret_brief/models.py` (add/export PublicEvent, CrossSalesCorrelation, keeping existing M1 models intact)
- `teateret_brief/matcher.py` (ADR 0002 3-level matcher, load_public_events from docs/research/arrangementsdata-2025-2026.md, aliases MatchReport = MatchingReport, match_batch = evaluate_all)
- `teateret_brief/analytics.py` (add calculate_cross_sales_correlations, CrossSalesCorrelation, zero division safety, preserving existing sales summarization)
- `tests/test_matcher.py` (comprehensive unit tests for Level 1, 2, 3, synonyms, Norwegian chars, room aliases, empty batches, disambiguation)
- `tests/test_analytics.py` (comprehensive unit tests for DuckDB/Python parity, rankings, cross-sales calculations, zero-ticket edge cases)

DO NOT modify files owned by other milestones (e.g. `csv_adapter.py`, `weather_and_calendar.py`, `render.py`, `pipeline.py`).
