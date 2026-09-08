# Project: Teateret Weekly Decision Brief Engine

## Architecture
The system is structured as an automated, deterministic intelligence engine delivering weekly decision briefs for theater management (Amir) at Teateret Kristiansand:
1. **Ingestion & Data Normalization**: `teateret_brief/csv_adapter.py` parses aggregated GastroPlanner CSV/Excel data with zero PII, strict schema validation, and decimal/date normalization into `SalesObservation` models.
2. **Deterministic Matching Engine**: `teateret_brief/matcher.py` matches sales data against the official 129-event database (2025–2026 across Hovedscenen, Biscenen, Intimscenen, Foajeen) following ADR 0002 (Level 1 ID, Level 2 Title+Date+Room, Level 3 Proximity / *nærhetskorrelasjon*).
3. **External Signals Layer**: Integrates MET.no weather forecasts, Agder school holiday calendar, city event clashes, Google Places sentiment topics, and Google Trends via a 3-tier retrieval structure (Live HTTPS -> Disk TTL Cache -> Static Fixtures).
4. **Analytics & Cross-Sales Synthesis**: `teateret_brief/analytics.py` calculates capacity utilization, weekday gaps, period trends, and +/- 2h dining cross-sales correlation.
5. **Brief Rendering & Audit Trail**: `teateret_brief/render.py` produces 3 human-in-the-loop draft formats (`brief.md`, `brief.html`, `email.txt`) with up to 3 prioritized operational recommendations, while `teateret_brief/pipeline.py` enforces multi-layer PII scanning and produces an immutable `manifest.json` with SHA-256 hashes of all inputs and generated artifacts.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | GastroPlanner CSV Ingestion | Semicolon/comma delimiter, date parsing (%Y-%m-%d, %d.%m.%Y, %d/%m/%Y), room mapping | M1 | survey_miner_1 |
| 2 | Norwegian Number & Currency Normalizer | Parses Norwegian numbers (`45 500,50` -> `45500.5`), strips `\u00a0`, validates positive finite floats | M1 | survey_miner_1 |
| 3 | Ingestion PII & Strict Column Gate | Rejects unknown columns in strict mode and forbids PII columns (`kunde`, `email`, `phone`, `notat`) | M1 | survey_explorer_1 |
| 4 | Additional PII Hardening | Strict scanner for 11-digit Norwegian FNR and credit card patterns | M1 | survey_explorer_1 |
| 5 | Level 1 Event Matching | Exact ID match (`EVT-YYMMDD`) against 129-event database | M2 | survey_miner_1 |
| 6 | Level 2 Event Matching | Normalized title + date + room heuristic matching with synonym dictionary | M2 | survey_miner_1 |
| 7 | Level 3 Event Matching | Proximity indication for single event on date marked as *nærhetskorrelasjon* / `needs_review` | M2 | survey_miner_1 |
| 8 | Event Matching Report & Batch Metrics | Batch evaluation reporting total observations, match count, needs_review count, and match rate % | M2 | survey_miner_1 |
| 9 | Cross-Sales Correlation Synthesis | Synthesizes table bookings and preorder packages with +/- 2h show window | M2 | survey_explorer_2 |
| 10 | MET.no Weather Signal Adapter | Weather forecast integration (Kristiansand 58.1467, 7.9956) with custom User-Agent and caching | M3 | survey_explorer_1 |
| 11 | Agder School Holiday Signal Adapter | Holiday calendar (Uke 8, Påske, Sommer, Uke 40, Jul) for family matinee vs corporate demand | M3 | survey_explorer_1 |
| 12 | Kristiansand City Event Clash Adapter | Clash radar for Kilden, Q42, Palmesus, festivals with distance and demographic overlap | M3 | survey_explorer_1 |
| 13 | External Signal 3-Tier Cache & Fallback | Live Safe HTTP -> Disk TTL Cache -> Deterministic Static Fixtures | M3 | survey_explorer_1 |
| 14 | Google Places Sentiment Adapter | GBP ratings, review count, and sentiment topic extraction with reviewer redaction `[ANMELDER]` | M3 | survey_miner_1 |
| 15 | Google Trends Agder Adapter | Regional Agder (`NO-42`) search interest trends for entertainment/dining keywords | M3 | survey_miner_1 |
| 16 | Schema.org Event Scraper | JSON-LD event scraper extracting structured calendar events with ticket availability | M3 | survey_miner_1 |
| 17 | Capacity Utilization & Gap Analysis | Computes stage capacity utilization, identifies dark weekdays (Tue/Wed) and underperforming shows | M4 | survey_explorer_2 |
| 18 | Prioritized Recommendations Engine | Generates up to 3 prioritized operational actions (marketing, staffing, programming) | M4 | survey_explorer_2 |
| 19 | Markdown Brief Renderer | Formats executive brief in Markdown with disclaimer `UTKAST – IKKE SENDT` | M4 | survey_explorer_2 |
| 20 | HTML Brief Renderer | Standalone styled HTML document with draft warning banner | M4 | survey_explorer_2 |
| 21 | Plaintext Email Draft Renderer | Formats human-in-the-loop email draft for Amir | M4 | survey_explorer_2 |
| 22 | Pre-flight PII Scanner on Outputs | Scans all rendered artifacts for email/phone before saving | M4 | survey_explorer_1 |
| 23 | Cryptographic Audit Manifest Generator | Generates `manifest.json` with SHA-256 hashes of all inputs, source documents, and outputs | M4 | survey_explorer_2 |
| 24 | Atomic Staging Directory Persistence | Writes to `runs/.staging/<run_id>` and atomically moves to `runs/<run_id>` | M4 | survey_explorer_2 |
| 25 | Security RepoPaths Confinement | Enforces path traversal protection strictly inside repository root | M4 | survey_miner_1 |
| 26 | Security Network Source Policy | Enforces HTTPS-only, port 443, domain allowlist, SSRF/private IP blocking | M4 | survey_miner_1 |
| 27 | CLI Entrypoint (`teateret-brief`) | CLI supporting `--mode (demo|live)`, `--sales`, `--sources`, `--mapping`, `--runtime` | M4 | survey_miner_1 |
| 28 | Comprehensive Unit & Integration Tests | 100% test pass rate across all test modules in `tests/` | M5 | survey_explorer_2 |
| 29 | Bytecode & Syntax Compilation Guard | `python -m compileall teateret_brief tests` reports zero errors | M5 | survey_explorer_2 |
| 30 | Adversarial Coverage Hardening | White-box gap analysis, edge cases, and adversarial test expansion | M5 | survey_explorer_2 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | GastroPlanner Ingestion & Zero-PII Schema Adaptation (R1) | Features 1, 2, 3, 4 | none | DONE (Gate passed, 100% tests) |
| M2 | Deterministic 3-Level Event Matching & Cross-Sales Synthesis (R2) | Features 5, 6, 7, 8, 9 | M1 | IN_PROGRESS (sub_orch_m2: 92802359-db7b-45bc-8886-e3ba9ecfbbc1) |
| M3 | External Context Enrichment & Signals (R3) | Features 10, 11, 12, 13, 14, 15, 16 | M1 | IN_PROGRESS (sub_orch_m3: 0ae1e169-aedc-4804-9a0c-7a3a6588be69) |
| M4 | Automated Decision Brief Rendering & Security/Audit Trail (R4) | Features 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27 | M2, M3 | PLANNED |
| M5 | Final E2E Test Pass (100%) & Adversarial Hardening | Features 28, 29, 30 | M4, E2E-Track | PLANNED |
| E2E | E2E Testing Suite Track | Design & verify 4 tiers of opaque-box E2E tests (Tiers 1-4) | none (parallel) | DONE (`TEST_READY.md` published, 119+ tests) |

## Interface Contracts
### Ingestion ↔ Matcher (`csv_adapter` ↔ `matcher`)
- `load_aggregated_csv(path: Path, mapping: CsvMapping) -> list[SalesObservation]`
- `SalesObservation`: `period: date`, `label: str`, `metric: str`, `value: float`, `unit: str`, `room: str | None`, `event_id: str | None`, `source_system: str`
- `EventMatcher.match(observation: SalesObservation) -> MatchResult`
- `MatchResult`: `observation: SalesObservation`, `matched_event: PublicEvent | None`, `match_level: Literal["level_1_id", "level_2_title_date_room", "level_3_proximity", "none"]`, `match_status: Literal["matched", "needs_review", "unmatched"]`, `reason: str`

### External Signals ↔ Pipeline (`external_signals` ↔ `pipeline`)
- `ExternalContextEnrichment`: `period: date`, `weather: WeatherForecastSignal | None`, `school_holiday: SchoolHolidaySignal | None`, `city_clashes: list[CityEventClashSignal]`
- `fetch_external_context(period: date, config: Config) -> ExternalContextEnrichment`

### Pipeline ↔ Rendering (`pipeline` ↔ `render`)
- `Brief`: `run_id: str`, `created_at: datetime`, `status: Literal["completed", "warning", "blocked"]`, `signals: list[Signal]`, `recommendations: list[Recommendation]`, `source_ids: list[str]`, `sources: list[SourceDocument]`, `warnings: list[str]`, `market_observations: list[MarketObservation]`
- `render_markdown(brief: Brief) -> str`
- `render_html(brief: Brief) -> str`
- `render_email(brief: Brief) -> str`

## Code Layout
- `teateret_brief/`:
  - `__init__.py`: Package init & version
  - `models.py`: Pydantic domain models (SalesObservation, PublicEvent, Brief, etc.)
  - `csv_adapter.py`: GastroPlanner CSV ingestion & normalization
  - `matcher.py`: ADR 0002 3-level event matcher
  - `security.py`: RepoPaths, SourcePolicy, assert_aggregated_csv, PII regexes
  - `analytics.py`: DuckDB/Python sales & capacity summarizer
  - `render.py`: Markdown, HTML, and email brief renderers
  - `pipeline.py`: Pipeline coordinator, staging isolation, manifest.json generator
  - `fetcher.py`: Safe HTTPS & fixture document fetcher
  - `google_places.py`: Google Places GBP adapter
  - `google_trends.py`: Google Trends Agder adapter
  - `schema_events.py`: Schema.org JSON-LD event extractor
  - `weather_and_calendar.py`: MET.no weather & Agder school holiday/clash signals
  - `cli.py`: Command-line entrypoint (`teateret-brief`)
- `tests/`:
  - `test_csv_adapter.py`, `test_matcher.py`, `test_security.py`, `test_analytics.py`, `test_pipeline.py`, `test_render.py`, `test_weather_and_calendar.py`, `test_cli.py`, etc.
  - `e2e/`: Requirement-driven opaque-box E2E test suite (Tiers 1-4)
- `sample_data/`:
  - `gastroplanner_sample_2026.csv`: Reference 2026 GastroPlanner export
  - `fixtures/`: Deterministic test fixtures for all external signals
- `docs/`:
  - `adr/`: ADR 0001 (deterministic architecture), ADR 0002 (3-level matching), ADR 0003 (security & PII), ADR 0004 (external signals)
  - `research/`: `arrangementsdata-2025-2026.md` (129 events), `gastroplanner-2026-avstemmingsrapport.md`
