# Scope: Milestone 2 — Deterministic 3-Level Event Matching & Cross-Sales Synthesis (R2)

## Architecture
Milestone 2 implements the core deterministic matching logic (following ADR 0002) and dining cross-sales correlation:
- **Event Database Loading**: Loads and indexes the 129 verified events from `docs/research/arrangementsdata-2025-2026.md` or embedded data structures into `PublicEvent` models.
- **Level 1 Matching**: Exact ID match (`EVT-YYMMDD` or `EVT-YYYYMMDD-HHMM` / event code) against the event database.
- **Level 2 Matching**: Normalized title + date + room heuristic matching with Norwegian text normalization, synonym dictionary, and room mapping (Hovedscenen, Biscenen, Intimscenen, Foajeen).
- **Level 3 Matching**: Proximity indication for single event on date marked as *nærhetskorrelasjon* (`needs_review`).
- **Batch Evaluation & Metrics**: Processes batch of `SalesObservation` instances and computes match report (total observations, matched, needs_review, unmatched, match_rate_percent >= 90%).
- **Cross-Sales Correlation**: Calculates +/- 2h restaurant cross-sales correlation (table bookings, preorder packages) linked to matched stage performances.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 5 | Level 1 Event Matching | Exact ID match (`EVT-YYMMDD`) against 129-event database | M2 | survey_miner_1 |
| 6 | Level 2 Event Matching | Normalized title + date + room heuristic matching with synonym dictionary | M2 | survey_miner_1 |
| 7 | Level 3 Event Matching | Proximity indication for single event on date marked as *nærhetskorrelasjon* / `needs_review` | M2 | survey_miner_1 |
| 8 | Event Matching Report & Batch Metrics | Batch evaluation reporting total observations, match count, needs_review count, and match rate % | M2 | survey_miner_1 |
| 9 | Cross-Sales Correlation Synthesis | Synthesizes table bookings and preorder packages with +/- 2h show window | M2 | survey_explorer_2 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M2.1 | Level 1-3 Matching Engine & Event DB | Features 5, 6, 7 | M1 | IN_PROGRESS |
| M2.2 | Match Reporting & Metrics Engine | Feature 8 | M2.1 | PLANNED |
| M2.3 | Cross-Sales Correlation Engine | Feature 9 | M2.1 | PLANNED |

## Interface Contracts
### Ingestion ↔ Matcher (`csv_adapter` ↔ `matcher`)
- `SalesObservation`: `period: date`, `label: str`, `metric: str`, `value: float`, `unit: str`, `room: str | None`, `event_id: str | None`, `source_system: str`
- `PublicEvent`: `event_id: str`, `title: str`, `start_date: date`, `start_time: str | time | None`, `room: str`, `capacity: int | None`, `category: str | None`
- `MatchResult`: `observation: SalesObservation`, `matched_event: PublicEvent | None`, `match_level: Literal["level_1_id", "level_2_title_date_room", "level_3_proximity", "none"]`, `match_status: Literal["matched", "needs_review", "unmatched"]`, `reason: str`
- `EventMatcher.match(observation: SalesObservation) -> MatchResult`
- `EventMatcher.match_batch(observations: list[SalesObservation]) -> MatchReport`
- `MatchReport`: `total_observations: int`, `matched_count: int`, `needs_review_count: int`, `unmatched_count: int`, `match_rate_percent: float`, `results: list[MatchResult]`

### Matcher / Sales ↔ Cross-Sales Analytics (`analytics.py`)
- `CrossSalesCorrelation`: `event_id: str`, `event_title: str`, `event_date: date`, `ticket_sales: float`, `table_covers_2h: int`, `preorder_revenue_2h: float`, `cross_sales_ratio: float`
- `calculate_cross_sales_correlations(observations: list[SalesObservation], matched_events: list[PublicEvent], window_hours: int = 2) -> list[CrossSalesCorrelation]`

## Code Layout
- Implementation files owned by M2:
  - `teateret_brief/matcher.py` (owned)
  - `teateret_brief/analytics.py` (cross-sales functions)
  - `teateret_brief/models.py` (extend models if needed, preserving existing M1 models)
  - `tests/test_matcher.py` (unit tests for matcher)
  - `tests/test_analytics.py` (unit tests for cross-sales analytics)
