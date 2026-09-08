# BRIEFING — 2026-08-20T07:44:00Z

## Mission
Implement Milestone 2: 3-level event matcher, public event loader (129 events), cross-sales correlation analytics, and comprehensive tests with DuckDB/Python parity.

## 🔒 My Identity
- Archetype: teamwork_preview_worker
- Roles: implementer, qa, specialist
- Working directory: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\worker_m2_1
- Original parent: 92802359-db7b-45bc-8886-e3ba9ecfbbc1
- Milestone: Milestone 2 (M2)

## 🔒 Key Constraints
- DO NOT CHEAT. All implementations must be genuine.
- DO NOT hardcode test results, expected outputs, or verification strings in source code.
- File boundaries: only modify teateret_brief/models.py, teateret_brief/matcher.py, teateret_brief/analytics.py, tests/test_matcher.py, tests/test_analytics.py.
- DO NOT modify files owned by other milestones (csv_adapter.py, weather_and_calendar.py, render.py, pipeline.py).
- Preserve existing M1 models and functions.
- 100% test pass rate with 0 warnings or errors across all test suites including E2E tiers.

## Current Parent
- Conversation ID: 92802359-db7b-45bc-8886-e3ba9ecfbbc1
- Updated: not yet

## Task Summary
- **What to build**:
  1. `PublicEvent`, `CrossSalesCorrelation` model definitions and exports.
  2. Public event parser in `matcher.py` for 129 events in `docs/research/arrangementsdata-2025-2026.md` with multi-day expansion and deterministic ID handling.
  3. ADR 0002 3-level matching logic in `matcher.py` (L1 exact/normalized + date + room, L2 synonym + room constraint, L3 proximity marked needs_review, batch deduplication, aliases MatchReport = MatchingReport, match_batch = evaluate_all).
  4. Cross-sales correlation engine in `analytics.py` (with zero-division safety and confidence classification).
  5. Full unit test suites in `tests/test_matcher.py` and `tests/test_analytics.py`.
- **Success criteria**: All existing tests and new unit/tier tests pass.
- **Interface contracts**: PROJECT.md, SCOPE.md, ADR 0002.
- **Code layout**: teateret_brief/

## Change Tracker
- **Files modified**: none yet
- **Build status**: pending
- **Pending issues**: none

## Quality Status
- **Build/test result**: pending
- **Lint status**: pending
- **Tests added/modified**: pending

## Loaded Skills
- None explicitly required beyond standard implementer/qa capabilities.

## Key Decisions Made
- [TBD]

## Artifact Index
- C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\worker_m2_1\DISPATCH.md
- C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\worker_m2_1\BRIEFING.md
- C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\worker_m2_1\progress.md
- C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\worker_m2_1\handoff.md
