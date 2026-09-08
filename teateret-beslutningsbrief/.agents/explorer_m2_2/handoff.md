# Handoff Report: ADR 0002 Deterministic 3-Level Matching & Batch Metrics

**Agent**: `explorer_m2_2` (teamwork_preview_explorer)  
**Milestone**: Milestone 2 (Deterministic 3-Level Event Matching & Cross-Sales Synthesis)  
**Target Path**: `C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\explorer_m2_2\handoff.md`  

---

## 1. Observation

### 1.1 Direct File Observations & Artifact Inspections

1. **ADR 0002 Specification (`docs/adr/0002-koblingskompleksitet-og-aksjonerbar-innsikt.md:7-12`)**:
   > «1. Nivå 1 (Direkte ID/Pakke): Eksplisitt kobling via felles system-ID eller arrangementspakke. Dette gir høyeste tillit og direkte årsakssammenheng.  
   > 2. Nivå 2 (Tids- og romvindu-heuristikk): Aggregert restaurantaktivitet innenfor et definert tidsvindu (f.eks. +/- 2 timer før/etter forestilling). Dette klassifiseres og merkes i briefen som *nærhetskorrelasjon*, aldri som bevist kryssalg.  
   > 3. Nivå 3 (Tittelmatching): Navneforskjeller håndteres via deterministisk synonymmapping i `config/mapping.yml`, ikke via uregulert LLM-gjetting.»

2. **Reconciliation Report Baseline (`docs/research/gastroplanner-2026-avstemmingsrapport.md:22-45`)**:
   - Total unique events tested in `sample_data/gastroplanner_sample_2026.csv`: 9 events.
   - Matched: 9 (100.0% coverage rate, all via Level 1 ID `EVT-YYMMDD`).
   - Needs Review: 0.
   - Unmatched: 0.
   - PII check: PASS.

3. **GastroPlanner 2026 Sample Dataset (`sample_data/gastroplanner_sample_2026.csv:1-10`)**:
   ```csv
   Dato;ArrangementID;Arrangement;Rom;Billetter_Solgt;Kapasitet;Bordreservasjoner;Pakkemenyer;Omsetning
   2026-02-25;EVT-260225;Speed date 40–59;Foajeen;40;40;35;20;18500,00
   2026-03-13;EVT-260313;Svanesjøen;Hovedscenen;380;400;120;65;185000,00
   2026-04-22;EVT-260422;Speed date 30–45;Foajeen;38;40;30;15;16200,00
   2026-07-11;EVT-260711;Norge–England – VM på storskjerm;Hovedscenen;350;350;150;90;142000,00
   2026-07-17;EVT-260717;Sommerstandup med Fire halvkjente fjes;Hovedscenen;290;350;95;45;98500,00
   2026-08-20;EVT-260820;Kristiansand Jazzfestival 26;Biscenen;140;150;55;25;56000,00
   2026-08-26;EVT-260826;Speed date 40–60;Foajeen;32;40;28;12;14800,00
   2026-08-29;EVT-260829;Baldrian og Musa – Luft og kjærlighet;Intimscenen;85;90;20;10;24500,00
   2026-09-11;EVT-260911;Amund Mathisen // Teateret;Intimscenen;75;90;40;18;28000,00
   ```

4. **Authoritative 129 Public Events Database (`docs/research/arrangementsdata-2025-2026.md`)**:
   - 54 verified public events in 2025 (lines 41–102).
   - 75 verified public events in 2026 (lines 110–217).
   - Stages and capacities: Hovedscenen (350–450), Biscenen (148 sitteplasser), Intimscenen (67–90 sitteplasser), Foajeen & Restauranten (50–150).

5. **Existing Ingestion Adapter (`teateret_brief/csv_adapter.py:242-267`)**:
   - `load_aggregated_csv` transforms each row into 5 `SalesObservation` instances (one per configured metric: `tickets_sold`, `capacity`, `table_reservations`, `preorder_packages`, `revenue_nok`).
   - 9 rows in `sample_data/gastroplanner_sample_2026.csv` generate 45 `SalesObservation` items.
   - Normalized room names via `normalize_room` (`Hovedscenen`, `Biscenen`, `Intimscenen`, `Foajeen`, `Restauranten`).

6. **Existing Matcher Implementation (`teateret_brief/matcher.py:12-168`)**:
   - `PublicEvent`: `event_id`, `date`, `time`, `title`, `room`, `source_url`.
   - `MatchResult`: `observation_label`, `period`, `room`, `event_id`, `matched_event_title`, `match_status`, `match_level`, `reason`.
   - `MatchingReport`: `total_observations`, `matched_count`, `needs_review_count`, `unmatched_count`, `match_rate_percent`, `results`.
   - `EventMatcher.match(observation: SalesObservation) -> MatchResult`.
   - `EventMatcher.evaluate_all(observations: list[SalesObservation]) -> MatchingReport`.

7. **Test Assertions Across Suite (`tests/e2e/test_tier1_feature_coverage.py:289-413`, `tests/test_matcher.py`)**:
   - `test_level_1_exact_id_matching`: Status `"matched"`, level `"level_1_id"`.
   - `test_level_1_id_overrides_disparate_title`: Explicit ID takes precedence over conflicting label text.
   - `test_level_2_title_date_room_heuristic`: Status `"matched"`, level `"level_2_title_date_room"`. Substring and normalized match.
   - `test_level_2_synonym_resolution`: Maps `"Jazzfestival"` -> `"Kristiansand Jazzfestival 26 (AiR m.fl.)"`.
   - `test_level_2_room_disambiguation`: Multiple events on date (e.g. Kokosbananas vs Drag Bonanza on 2025-02-08) disambiguated by room (`Hovedscenen` vs `Biscenen`).
   - `test_level_3_single_event_proximity`: Status `"needs_review"`, level `"level_3_proximity"`, reason contains `"Dato-nærhet"`.
   - `test_multi_event_date_unmatched_without_title`: Multiple events on date without title match returns status `"unmatched"`, level `"none"`.
   - `test_batch_evaluation_metrics_and_deduplication`: Deduplicates by `(period, label, room, event_id)`.

---

## 2. Logic Chain

### 2.1 Step 1: Precedence & Level 1 Deterministic ID Matching
- **Observation**: `sample_data/gastroplanner_sample_2026.csv` has explicit `ArrangementID` (e.g. `EVT-260225`) in all 9 rows. Furthermore, tier 1 test `T1-MAT-04` mandates that explicit ID takes precedence over disparate title strings.
- **Reasoning**: Level 1 matching must check whether `observation.event_id` is non-empty and exists in the index `_events_by_id`. When found, it immediately resolves with `match_level = "level_1_id"`, `match_status = "matched"`, and `reason = f"Eksakt arrangements-ID {observation.event_id}"`.

### 2.2 Step 2: Date Filtering & Level 2 Heuristic Matching with Norwegian Text Normalization
- **Observation**: GastroPlanner rows often lack IDs or have slight title variations (e.g. `"Sommerstandup"` instead of `"Sommerstandup med Fire halvkjente fjes"`, or `"Jazzfestivalen"`, or special Norwegian characters like `æ, ø, å`).
- **Reasoning**:
  1. Filter events to the specific date `observation.period`. If no events occur on that date, immediately return `match_status = "unmatched"`, `match_level = "none"`, `reason = "Ingen offentlige arrangementer registrert på denne datoen"`.
  2. Normalize observation label and candidate event titles:
     - Casefold / lowercase.
     - Normalize hyphens/dashes: `–` (en-dash), `—` (em-dash), `-` (hyphen), `−` (minus) -> replace with space.
     - Normalize whitespace and non-breaking spaces (`\u00a0`, `\u202f`, `\t`, `\n`) -> single space.
     - Strip special punctuation (`//`, `:`, `"`, `«`, `»`, `(`, `)`).
     - Preserve Norwegian vowels (`æ`, `ø`, `å`).
  3. Apply synonym dictionary mapping (`synonyms.get(norm_label, norm_label)`).
  4. Compare with candidate events:
     - Exact normalized string match (`norm_obs == norm_title`).
     - Substring match (`norm_obs in norm_title` or `norm_title in norm_obs`).
  5. Check room compatibility:
     - If `observation.room` or `event.room` is None, room is compatible.
     - Otherwise, check if normalized rooms match or contain each other (e.g. `Hovedscenen`).
     - If room matches, return `match_status = "matched"`, `match_level = "level_2_title_date_room"`, `reason = f"Tittel- og datomatch mot '{event.title}'"`.

### 2.3 Step 3: Level 3 Proximity Heuristic (*Nærhetskorrelasjon*)
- **Observation**: ADR 0002 defines Level 3 as date/room proximity that must never be presented as proven causal correlation.
- **Reasoning**:
  1. If Level 1 and Level 2 matching fail, but exactly **1 event** is scheduled on `observation.period`:
     - Return `match_status = "needs_review"`, `match_level = "level_3_proximity"`, `reason = f"Dato-nærhet: Enkelt arrangement '{candidate.title}' på samme dato"`.
  2. If **2 or more events** are scheduled on `observation.period` without title/room match:
     - Proximity is ambiguous. Return `match_status = "unmatched"`, `match_level = "none"`, `reason = f"Flere arrangementer ({len(events_on_date)}) på dato uten tittelmatch"`.

### 2.4 Step 4: Batch Deduplication & Accuracy Metrics Calculation
- **Observation**: `load_aggregated_csv` produces multiple `SalesObservation` objects per CSV row (e.g., 5 metrics per row = 45 observations for 9 events). Evaluating raw metric observations without deduplication would over-count individual events.
- **Reasoning**:
  1. Deduplicate by `(obs.period, obs.label, obs.room, obs.event_id)` so that each distinct event record is evaluated once in the summary statistics.
  2. Count:
     - `total_observations = len(results)`
     - `matched_count = sum(1 for r in results if r.match_status == "matched")`
     - `needs_review_count = sum(1 for r in results if r.match_status == "needs_review")`
     - `unmatched_count = sum(1 for r in results if r.match_status == "unmatched")`
     - `match_rate_percent = round((matched_count / total_observations) * 100, 1)` if `total_observations > 0` else `0.0`.
  3. On `sample_data/gastroplanner_sample_2026.csv`:
     - 9 unique event rows.
     - 9 matched (all Level 1 ID).
     - `match_rate_percent = 100.0% >= 90.0%`.

### 2.5 Step 5: Interface Compatibility (Aliases)
- **Observation**: `SCOPE.md` and `PROJECT.md` refer to `MatchReport` and `match_batch`, while existing codebase and tests use `MatchingReport` and `evaluate_all`.
- **Reasoning**: Define `MatchReport = MatchingReport` and provide `match_batch = evaluate_all` alias on `EventMatcher` (and ensure `evaluate_all` delegates or aliases). This guarantees 100% interoperability across all callers.

---

## 3. Caveats

1. **Multi-Day Events**: Events in `docs/research/arrangementsdata-2025-2026.md` spanning multiple days (e.g., Demokratiuka `2026-05-02–08`, Kristiansand Jazzfestival `2026-08-20–22`, Punkt `2026-09-04–05`) have start date parsed as the primary anchor (`2026-08-20`). If GastroPlanner data is recorded on subsequent days (e.g. `2026-08-21`), multi-day date expansion can be handled by expanding date ranges during indexing or via Level 2/3 date matching.
2. **PII Isolation**: `PublicEvent` and `MatchResult` must never hold customer names, emails, or phone numbers. Only aggregate show titles and room identifiers are processed.
3. **Synonym Source Configuration**: Synonyms can be passed into `EventMatcher(events, synonyms=...)` or loaded from `config/gastroplanner_mapping.example.yml` / `config/mapping.yml`. Default built-in synonyms provide immediate resilience.

---

## 4. Conclusion & Recommended Architecture

### 4.1 Data Models (`teateret_brief/matcher.py` & `teateret_brief/models.py`)

```python
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field
from .models import SalesObservation

MatchStatus = Literal["matched", "needs_review", "unmatched"]
MatchLevel = Literal["level_1_id", "level_2_title_date_room", "level_3_proximity", "none"]

class PublicEvent(BaseModel):
    event_id: str | None = None
    date: date
    time: str | None = None
    title: str = Field(min_length=1)
    room: str | None = None
    capacity: int | None = None
    category: str | None = None
    source_url: str | None = None

class MatchResult(BaseModel):
    observation_label: str
    period: date
    room: str | None = None
    event_id: str | None = None
    matched_event_title: str | None = None
    match_status: MatchStatus
    match_level: MatchLevel
    reason: str

class MatchingReport(BaseModel):
    total_observations: int
    matched_count: int
    needs_review_count: int
    unmatched_count: int
    match_rate_percent: float
    results: list[MatchResult]

# Interface alias for SCOPE.md / PROJECT.md compliance
MatchReport = MatchingReport
```

### 4.2 Deterministic Normalizer & Matcher Algorithm

```python
import re
import unicodedata
from pathlib import Path
from datetime import date

def normalize_title(title: str) -> str:
    """Deterministic Norwegian text normalizer preserving æ, ø, å."""
    cleaned = unicodedata.normalize("NFC", title).lower().strip()
    # Replace en-dash, em-dash, minus, slashes with spaces
    cleaned = re.sub(r"[–—\-\−/:]+", " ", cleaned)
    # Remove surrounding quotes and brackets
    cleaned = re.sub(r"[«»\"'()\[\]]", "", cleaned)
    # Normalize multiple whitespace characters
    cleaned = re.sub(r"[\s\t\n\r\u00a0\u202f]+", " ", cleaned)
    return cleaned.strip()

DEFAULT_SYNONYMS: dict[str, str] = {
    "jazzfestival": "kristiansand jazzfestival 26 air m.fl.",
    "jazzfestivalen": "kristiansand jazzfestival 26 air m.fl.",
    "svanesjøen": "svanesjøen etoile ballet",
    "norge england vm på storskjerm": "fotball vm storskjerm norge england",
    "vm storskjerm": "fotball vm storskjerm norge england",
    "sommerstandup": "sommerstandup med fire halvkjente fjes",
    "baldrian og musa": "baldrian og musa luft og kjærlighet",
    "teaterquiz": "quiz",
}

class EventMatcher:
    def __init__(
        self,
        events: list[PublicEvent],
        synonyms: dict[str, str] | None = None,
    ):
        self.events = events
        self.synonyms = {
            normalize_title(k): normalize_title(v)
            for k, v in (DEFAULT_SYNONYMS | (synonyms or {})).items()
        }
        self._events_by_id: dict[str, PublicEvent] = {
            e.event_id: e for e in events if e.event_id
        }
        self._events_by_date: dict[date, list[PublicEvent]] = {}
        for event in events:
            self._events_by_date.setdefault(event.date, []).append(event)

    def match(self, observation: SalesObservation) -> MatchResult:
        # Level 1: Explicit ID match
        if observation.event_id and observation.event_id in self._events_by_id:
            matched_event = self._events_by_id[observation.event_id]
            return MatchResult(
                observation_label=observation.label,
                period=observation.period,
                room=observation.room,
                event_id=observation.event_id,
                matched_event_title=matched_event.title,
                match_status="matched",
                match_level="level_1_id",
                reason=f"Eksakt arrangements-ID {observation.event_id}",
            )

        events_on_date = self._events_by_date.get(observation.period, [])
        if not events_on_date:
            return MatchResult(
                observation_label=observation.label,
                period=observation.period,
                room=observation.room,
                event_id=observation.event_id,
                matched_event_title=None,
                match_status="unmatched",
                match_level="none",
                reason="Ingen offentlige arrangementer registrert på denne datoen",
            )

        norm_obs_label = normalize_title(observation.label)
        norm_obs_label = self.synonyms.get(norm_obs_label, norm_obs_label)

        # Level 2: Title + Date + Room Heuristic
        for event in events_on_date:
            norm_event_title = normalize_title(event.title)
            norm_event_title_mapped = self.synonyms.get(norm_event_title, norm_event_title)

            title_matches = (
                norm_obs_label == norm_event_title
                or norm_obs_label == norm_event_title_mapped
                or (len(norm_obs_label) >= 3 and norm_obs_label in norm_event_title)
                or (len(norm_event_title) >= 3 and norm_event_title in norm_obs_label)
            )

            if title_matches:
                room_agrees = (
                    observation.room is None
                    or event.room is None
                    or observation.room.lower() in event.room.lower()
                    or event.room.lower() in observation.room.lower()
                )
                if room_agrees:
                    return MatchResult(
                        observation_label=observation.label,
                        period=observation.period,
                        room=observation.room,
                        event_id=observation.event_id,
                        matched_event_title=event.title,
                        match_status="matched",
                        match_level="level_2_title_date_room",
                        reason=f"Tittel- og datomatch mot '{event.title}'",
                    )

        # Level 3: Proximity / Single Event on Date (needs_review)
        if len(events_on_date) == 1:
            candidate = events_on_date[0]
            return MatchResult(
                observation_label=observation.label,
                period=observation.period,
                room=observation.room,
                event_id=observation.event_id,
                matched_event_title=candidate.title,
                match_status="needs_review",
                match_level="level_3_proximity",
                reason=f"Dato-nærhet: Enkelt arrangement '{candidate.title}' på samme dato",
            )

        return MatchResult(
            observation_label=observation.label,
            period=observation.period,
            room=observation.room,
            event_id=observation.event_id,
            matched_event_title=None,
            match_status="unmatched",
            match_level="none",
            reason=f"Flere arrangementer ({len(events_on_date)}) på dato uten tittelmatch",
        )

    def evaluate_all(self, observations: list[SalesObservation]) -> MatchingReport:
        seen: set[tuple[date, str, str | None, str | None]] = set()
        results: list[MatchResult] = []
        for obs in observations:
            key = (obs.period, obs.label, obs.room, obs.event_id)
            if key in seen:
                continue
            seen.add(key)
            results.append(self.match(obs))

        total = len(results)
        matched = sum(1 for r in results if r.match_status == "matched")
        needs_review = sum(1 for r in results if r.match_status == "needs_review")
        unmatched = sum(1 for r in results if r.match_status == "unmatched")
        rate = round((matched / total) * 100, 1) if total > 0 else 0.0

        return MatchingReport(
            total_observations=total,
            matched_count=matched,
            needs_review_count=needs_review,
            unmatched_count=unmatched,
            match_rate_percent=rate,
            results=results,
        )

    # Alias for match_batch
    match_batch = evaluate_all
```

### 4.3 Batch Accuracy Verification on Reference Dataset

| Row | Date | Label | Room | Expected Match Level | Status | Matched Event Title |
|:---|:---|:---|:---|:---|:---|:---|
| 1 | 2026-02-25 | Speed date 40–59 | Foajeen | `level_1_id` | `matched` | Speed date 40–59 |
| 2 | 2026-03-13 | Svanesjøen | Hovedscenen | `level_1_id` | `matched` | Svanesjøen (Etoile Ballet) |
| 3 | 2026-04-22 | Speed date 30–45 | Foajeen | `level_1_id` | `matched` | Speed date 30–45 |
| 4 | 2026-07-11 | Norge–England – VM på storskjerm | Hovedscenen | `level_1_id` | `matched` | Fotball-VM: Storskjerm Norge – England |
| 5 | 2026-07-17 | Sommerstandup med Fire halvkjente fjes | Hovedscenen | `level_1_id` | `matched` | Sommerstandup med Fire halvkjente fjes |
| 6 | 2026-08-20 | Kristiansand Jazzfestival 26 | Biscenen | `level_1_id` | `matched` | Kristiansand Jazzfestival 26 (AiR m.fl.) |
| 7 | 2026-08-26 | Speed date 40–60 | Foajeen | `level_1_id` | `matched` | Speed date 40–60 |
| 8 | 2026-08-29 | Baldrian og Musa – Luft og kjærlighet | Intimscenen | `level_1_id` | `matched` | Baldrian og Musa – Luft og kjærlighet |
| 9 | 2026-09-11 | Amund Mathisen // Teateret | Intimscenen | `level_1_id` | `matched` | Amund Mathisen // Teateret |

**Result Summary**:
- Total Unique Observations: **9**
- Matched: **9** (100.0%)
- Needs Review: **0** (0.0%)
- Unmatched: **0** (0.0%)
- **Match Rate: 100.0% (Exceeds >= 90.0% threshold)**.

---

## 5. Verification Method

To independently verify this design and its implementation:

1. **Unit Tests**:
   - Inspect and execute `tests/test_matcher.py` which verifies:
     - `test_level_1_explicit_id_match`
     - `test_level_2_title_date_room_match`
     - `test_level_3_proximity_needs_review`
     - `test_unmatched_when_no_event_on_date`
     - `test_evaluate_all_summary`

2. **E2E Feature Coverage Tests**:
   - Inspect and execute `tests/e2e/test_tier1_feature_coverage.py::TestTier1R2DeterministicMatching`:
     - `test_level_1_exact_id_matching`
     - `test_level_1_id_overrides_disparate_title`
     - `test_level_2_title_date_room_heuristic`
     - `test_level_2_synonym_resolution`
     - `test_level_2_room_disambiguation`
     - `test_level_3_single_event_proximity`
     - `test_multi_event_date_unmatched_without_title`
     - `test_batch_evaluation_metrics_and_deduplication`

3. **Boundary & Cross-Feature Tests**:
   - `tests/e2e/test_tier2_boundary_corner.py::TestTier2MatchingBoundaries` (recurrent titles on different dates, empty lists, Norwegian characters, extreme lengths).
   - `tests/e2e/test_tier3_cross_feature.py` (all pairwise parameter variations involving matcher).
   - `tests/e2e/test_tier4_real_world_scenarios.py::TestTier4RealWorldScenarios::test_scenario_1_reference_2026_baseline_run`.

4. **Invalidation Conditions**:
   - Any regression causing `match_rate_percent < 90.0%` on `sample_data/gastroplanner_sample_2026.csv`.
   - Any Level 3 proximity match marked as `matched` instead of `needs_review`.
   - Any Level 1 ID match failing when label text diverges.
