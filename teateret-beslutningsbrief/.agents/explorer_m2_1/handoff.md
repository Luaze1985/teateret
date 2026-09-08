# Handoff Report: 129-Event Database & Schema Representation (Milestone 2)

## 1. Observation

### 1.1 Dataset Sources and Structure
Direct observation of `docs/research/arrangementsdata-2025-2026.md` (242 lines, 26,049 bytes):
- **Header & Scope** (lines 14–22):
  > "Dette dokumentet inneholder den komplette kartleggingen av alle identifiserte offentlige arrangementer... for perioden 2025 og 2026."
  > "Totalt inneholder databasen 129 verifiserte oppføringer (54 fra 2025 og 75 fra 2026) uten noen form for personopplysninger om publikum eller billettkjøpere (GDPR-samsvar)."
- **Room Capacities** (lines 28–34):
  - `Hovedscenen`: Teatersal / Storscene, capacity 350–450 plasser.
  - `Biscenen`: Amfi / Black Box, capacity 148 sitteplasser (inntil 250).
  - `Intimscenen`: Salong m/ røde sofaer, capacity 67–90 sitteplasser.
  - `Foajeen & Restauranten`: Åpen sosial sone & bar, capacity variabel (50–150).
- **2025 Calendar Table** (lines 39–102):
  - Contains 62 table rows across 2025 (e.g., `2025-01-16` ImproTorsdag to `2025-12-30` Baldrian og Musa).
  - Table header: `| Dato (ÅÅÅÅ-MM-DD) | Tid | Tittel / Arrangement | Format | Rom / Scene | Offisiell kilde |`
- **2026 Calendar Table** (lines 108–217):
  - Contains 108 table rows across 2026 (e.g., `2026-01-17` Stian Nedrejord to `2026-12-28` Baldrian og Musa).
  - Combined row count across both tables: 170 table rows representing 129 distinct event productions/series (some with multiple showtimes or multi-day runs).
- **Sample Data Reference**:
  - `sample_data/gastroplanner_sample_2026.csv`: 10 rows containing columns `Dato;ArrangementID;Arrangement;Rom;Billetter_Solgt;Kapasitet;Bordreservasjoner;Pakkemenyer;Omsetning`.
  - Format of `ArrangementID`: `EVT-260225`, `EVT-260313`, `EVT-260422`, `EVT-260711`, `EVT-260717`, `EVT-260820`, `EVT-260826`, `EVT-260829`, `EVT-260911`.

### 1.2 Existing Code and Model State
- **`teateret_brief/models.py`** (161 lines):
  - Defines `SalesObservation` (lines 42–52) with fields: `period: date`, `label: str`, `metric: str`, `value: float`, `unit: str`, `source_system: str = "GastroPlanner"`, `room: str | None`, `event_id: str | None`, `match_status: Literal["matched", "needs_review", "unmatched"]`.
  - Currently does NOT define `PublicEvent` in `models.py`.
- **`teateret_brief/matcher.py`** (168 lines):
  - Defines `PublicEvent` (lines 12–19) with fields: `event_id: str | None = None`, `date: date`, `time: str | None = None`, `title: str = Field(min_length=1)`, `room: str | None = None`, `source_url: str | None = None`.
  - Defines `MatchResult` (lines 21–30) and `MatchingReport` (lines 32–39).
  - Defines `_normalize_title(title: str) -> str` (lines 41–45) stripping hyphens and collapsing whitespace.
  - Implements `EventMatcher` (lines 48–168) with 3-level matching:
    - Level 1: `observation.event_id` in `_events_by_id`.
    - Level 2: Title substring/synonym + date + room agreement.
    - Level 3: Single event on date marked as `needs_review` (`level_3_proximity`).
- **`teateret_brief/csv_adapter.py`** (269 lines):
  - Implements `normalize_room(raw: str | None) -> str | None` (lines 81–100) handling canonical venues (`Hovedscenen`, `Biscenen`, `Intimscenen`, `Foajeen`, `Restauranten`) and compound venues (`" / "`).
- **`tests/e2e/conftest.py`** (lines 93–131):
  - Implements `_load_129_events_from_markdown(md_path: Path) -> list[PublicEvent]` which parses table rows using regex `\|\s*\*\*(\d{4}-\d{2}-\d{2}(?:–\d{2})?)\*\*\s*\|\s*([^|]*)\|\s*([^|]+)\|\s*([^|]*)\|\s*([^|]+)\|\s*\[?([^\]|]*)`.

---

## 2. Logic Chain

### 2.1 Schema Mapping: Raw Markdown to `PublicEvent` Domain Model
From the observed markdown table headers:
`| Dato (ÅÅÅÅ-MM-DD) | Tid | Tittel / Arrangement | Format | Rom / Scene | Offisiell kilde |`

We map the attributes to `PublicEvent` as follows:
| Markdown Column | Field Name | Type | Processing / Normalization | Example |
|---|---|---|---|---|
| `Dato` | `date` (alias `start_date`) | `datetime.date` | Parse ISO date `%Y-%m-%d`. For date ranges (`2026-05-02–08`), extract start date `2026-05-02` and optional `end_date: date(2026, 5, 8)`. | `date(2026, 3, 13)` |
| `Dato` (derived) | `event_id` | `str` | Format: `EVT-YYMMDD`. If multiple events occur on the same date, append sequence or room code (e.g., `EVT-250208-1` or `EVT-250208-HOVED`). | `"EVT-260313"` |
| `Tid` | `time` (alias `start_time`) | `str \| None` | Raw time string or primary showtime. | `"19:00"`, `"12:30 & 14:30"`, `"Fra 17:45"` |
| `Tid` (derived) | `show_times` | `list[str]` | List of individual showtimes parsed from compound strings (e.g. `["12:30", "14:30"]`). | `["19:00", "21:00"]` |
| `Tittel / Arrangement` | `title` | `str` | Cleaned title without enclosing formatting quotes (`«`, `»`). | `"Svanesjøen (Etoile Ballet)"` |
| `Format` | `category` (or `format`) | `str \| None` | Cultural format / genre category. | `"Standup / Humor"`, `"Dukketeater"`, `"Konsert / Blues"` |
| `Rom / Scene` | `room` | `str \| None` | Normalized canonical room using `csv_adapter.normalize_room`. | `"Hovedscenen"`, `"Foajeen / Biscenen"` |
| `Rom / Scene` (derived) | `capacity` | `int \| None` | Standard default capacity inferred from venue if not explicit: `Hovedscenen`: 400, `Biscenen`: 148, `Intimscenen`: 90, `Foajeen`: 50, `Restauranten`: 80. | `400` |
| `Offisiell kilde` | `source_url` | `str \| None` | Extracted URL from markdown link `[name](url)`. | `"https://teateret.no"` |

### 2.2 Critical Data Quirks & Handling Strategy

1. **Same-Day Multiple Events & ID Disambiguation**:
   - *Observation*: 22 dates have 2 or more separate events (e.g. `2025-02-08` has *Kokosbananas* and *Drag Bonanza 3*; `2025-08-23` has 4 jazz festival events).
   - *Logic*: A naive keying `_events_by_id[f"EVT-{yy}{mm}{dd}"] = event` causes earlier events on that date to be overwritten.
   - *Resolution*: 
     - Generate deterministic unique IDs: `EVT-YYMMDD` for the first event, `EVT-YYMMDD-2`, `EVT-YYMMDD-3` for subsequent events on that date.
     - For Level 1 matching, if `observation.event_id` is `EVT-YYMMDD` and multiple events exist on that date, resolve via room/title context, or support querying `_events_by_id` as a multimap / alias map.

2. **Date Ranges (Multi-day Events)**:
   - *Observation*: Three entries span multiple days: `2026-05-02–08` (Demokratiuka), `2026-08-20–22` (Jazzfestival 26), `2026-09-04–05` (Punkt 2026).
   - *Logic*: GastroPlanner sales observations occur on a specific date (e.g. `2026-05-04`). If the event is only indexed under `2026-05-02`, lookups on intermediate days will miss.
   - *Resolution*: During ingestion/indexing, populate `_events_by_date` for every calendar date in `[start_date, end_date]`.

3. **Compound Showtimes (Multiple Shows)**:
   - *Observation*: Entries such as `19:00 & 21:00` (Erlend Osnes), `12:30 & 14:30` (Kokosbananas).
   - *Logic*: Cross-sales calculation (+/- 2h dining window) needs to correlate table reservations with both the early and late showtimes.
   - *Resolution*: Expose `show_times: list[str]` containing all individual showtime timestamps alongside raw `time`.

4. **Multi-Venue Events**:
   - *Observation*: Entries like `Foajeen / Biscenen`, `Hovedscenen / Biscenen`.
   - *Logic*: Sales observations may specify either `Foajeen` or `Biscenen`.
   - *Resolution*: `normalize_room` decomposes multi-room entries, and room agreement in Level 2 checks intersection between observation room and event rooms.

5. **Title Variations & Punctuation**:
   - *Observation*: Titles contain Norwegian guillemets (`«...»`), hyphens vs en-dashes (`-` vs `–`), and parenthetical subtitles (`(KrsImpro)`, `(UiA)`, `(Premiere)`).
   - *Logic*: A rigid string comparison `obs.label == event.title` fails when POS registers record `Sommerstandup` but the database has `Sommerstandup med Fire halvkjente fjes`.
   - *Resolution*: Title normalization strips punctuation, unfolds Norwegian characters (`æ`, `ø`, `å` retained but casefolded), and token substring matching + synonym dictionary in `config/mapping.yml` resolves variations.

### 2.3 Recommended Indexing & Lookup Mechanisms
To guarantee O(1) matching performance in high-throughput batch pipelines:
```
EventDatabase / EventIndex:
├── _by_id: dict[str, PublicEvent]                           # O(1) ID lookup
├── _by_date: dict[date, list[PublicEvent]]                  # O(1) date lookup (multi-day expanded)
├── _by_norm_title: dict[str, list[PublicEvent]]             # O(1) title lookup
├── _by_room_date: dict[tuple[str, date], list[PublicEvent]] # O(1) compound lookup
└── _sorted_dates: list[date]                                # O(log N) bisect date range search
```

---

## 3. Caveats

1. **Capacity Variations**: Room capacities in the markdown are given as ranges (e.g. Hovedscenen 350–450). Default model capacities are set to the standard configuration (400 for Hovedscenen, 148 for Biscenen, 90 for Intimscenen, 50 for Foajeen). Actual ticket capacity for a specific show comes from the GastroPlanner `Kapasitet` column when available.
2. **Daily Aggregation vs Hourly Dining**: Aggregated GastroPlanner CSVs report daily table reservations and revenue. The +/- 2h cross-sales window is evaluated relative to the event's listed showtime(s) on that date. Exact minute-by-minute reservation curves require transaction-level exports.
3. **PublicEvent Model Location**: Currently `PublicEvent` is defined in `teateret_brief/matcher.py`. Moving or re-exporting it from `teateret_brief/models.py` must maintain complete backwards compatibility with imports in `test_matcher.py` and `tests/e2e/conftest.py`.

---

## 4. Conclusion

1. **Ingestion Engine**: Implement `load_public_events(source_path: Path) -> list[PublicEvent]` in `teateret_brief/matcher.py` (or a dedicated helper) that parses `docs/research/arrangementsdata-2025-2026.md` dynamically with comprehensive error handling, multi-day range expansion, and deterministic ID allocation.
2. **Pydantic Model Schema**:
   - `event_id: str` (e.g. `EVT-260313`)
   - `title: str` (e.g. `Svanesjøen (Etoile Ballet)`)
   - `date: date` / `start_date: date`
   - `end_date: date | None = None`
   - `time: str | None = None`
   - `show_times: list[str] = Field(default_factory=list)`
   - `room: str | None = None`
   - `capacity: int | None = None`
   - `category: str | None = None`
   - `source_url: str | None = None`
3. **Deterministic 3-Tier Matcher**:
   - **Level 1**: Direct `event_id` match against `_by_id`.
   - **Level 2**: Date + Normalized Title + Room agreement (with synonym mapping).
   - **Level 3**: Date-only single-event proximity marked as `needs_review` (`level_3_proximity`).
   - **Unmatched**: Returns `unmatched` with clear audit reason.
4. **Batch Metrics & Cross-Sales**:
   - Dedup observations by `(period, label, room, event_id)`.
   - Compute `match_rate_percent >= 90.0%`.
   - Correlate `table_reservations` and `preorder_packages` against matched shows.

---

## 5. Verification Method

To independently verify the event database ingestion and matching implementation:

1. **Parse Verification**:
   - Ingest `docs/research/arrangementsdata-2025-2026.md` and verify that >= 129 events are extracted without Pydantic validation errors:
     ```bash
     python -m pytest tests/test_matcher.py -v
     ```
2. **E2E Matching Coverage & Regression Suite**:
   - Run the full E2E test suite across all 4 tiers to confirm matching against the 129-event dataset:
     ```bash
     python -m pytest tests/e2e/test_tier1_feature_coverage.py tests/e2e/test_tier3_cross_feature.py -v
     ```
3. **Syntax & Compilation Verification**:
   - Ensure zero bytecode or typing compilation errors across the codebase:
     ```bash
     python -m compileall teateret_brief tests
     ```
