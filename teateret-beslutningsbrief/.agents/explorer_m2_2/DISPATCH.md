## 2026-08-20T07:40:09Z
You are explorer_m2_2 (teamwork_preview_explorer) for Milestone 2.
Your working directory: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\explorer_m2_2
Project root: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief

MANDATORY FIRST STEP: Read ORIGINAL_REQUEST.md at:
C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\ORIGINAL_REQUEST.md
Also read PROJECT.md at:
C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\orchestrator\PROJECT.md
Also read SCOPE.md at:
C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\sub_orch_m2\SCOPE.md

Task:
Investigate ADR 0002 Deterministic 3-Level Matching Logic and Batch Metrics for Milestone 2:
1. Examine `docs/adr/0002-koblingskompleksitet-og-aksjonerbar-innsikt.md` and `docs/research/gastroplanner-2026-avstemmingsrapport.md`.
2. Inspect `sample_data/gastroplanner_sample_2026.csv` and `teateret_brief/csv_adapter.py` / `teateret_brief/models.py`.
3. Design the exact matching algorithm for:
   - Level 1: Explicit ID match (`EVT-YYMMDD` or event identifier present in label/event_id).
   - Level 2: Normalized title + date + room matching with Norwegian text normalization (lowercase, stripping punctuation, handling æøå, synonym dictionary like "Teaterquiz" <-> "Quiz", "Konsert", etc.).
   - Level 3: Proximity / single event on date heuristics (marked as `needs_review` with reason `nærhetskorrelasjon`).
4. Design the `MatchResult`, `MatchReport`, and batch evaluation calculating total observations, matched count, needs_review count, unmatched count, and match_rate_percent (ensuring >= 90% on `sample_data/gastroplanner_sample_2026.csv`).

Write your findings and recommendations in:
`C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\explorer_m2_2\handoff.md`
Then send a message back with your summary and handoff path.
