# Handoff Report: Milestone 3 — Feature 11 (Agder School Holiday Signal Adapter) & Feature 12 (Kristiansand City Event Clash Radar)

**Agent ID**: `explorer_2`  
**Milestone**: Milestone 3 (External Context Enrichment & Signals - R3)  
**Parent Agent**: `0ae1e169-aedc-4804-9a0c-7a3a6588be69` (sub_orch_m3)  
**Date**: 2026-08-20  
**Status**: Complete Investigation & Architecture Specification  

---

## 1. Observation

Direct observations from codebase inspection, research documents, and architecture requirements:

1. **Scope & Architectural Boundaries** (`.agents/sub_orch_m3/SCOPE.md` lines 15–37):
   - Feature 11 requires an Agder School Holiday Signal Adapter covering Vinterferie (Uke 8), Påskeferie, Sommerferie (Uke 26–33), Høstferie (Uke 40), Juleferie, and demand multiplier flags (family/matinee vs corporate/evening).
   - Feature 12 requires a Kristiansand City Event Clash Radar monitoring major local venues: Kilden Teater og Konserthus, Q42, Palmesus festival, Ravnedalen Live, Dark Season festival, and Dyreparken seasonal spikes with distance in km, expected attendance, target demographic overlap, and discrete clash severity (`low`, `medium`, `high`, `critical`).
   - Both features feed into `ExternalContextEnrichment` aggregate model alongside Weather, Places Sentiment, Google Trends, and Scraped Events.

2. **Existing Models & Architecture** (`teateret_brief/models.py` lines 42–89, 140–153):
   - `MarketObservation` and `ReviewSummary` models are implemented for M1/M2.
   - Signal interfaces require strict typing, Pydantic v2 validation, zero PII leakage, and deterministic fallback via static fixtures in `sample_data/fixtures/`.

3. **Domain & Local Knowledge Context** (`docs/research/arrangementsdata-2025-2026.md` lines 28–34, 223–242; `docs/research/teateret-utvidede-use-cases-og-forretningsmuligheter.md` lines 35–86):
   - Teateret (Kongens gate 2) has 4 stages: Hovedscenen (350–450 cap), Biscenen (148 cap), Intimscenen (67–90 cap), Foajeen/Restauranten (50–150 cap).
   - High-yield demographic segments:
     - Family / Matinees: Baldrian og Musa, KBUT children's theater, Saturday afternoon family shows.
     - Adult Culture / Evening: Standup tours, KrsImpro, CBRC blues/rock club, jazz/Punkt festivals.
     - Corporate / B2B: Julebord dining, weekday seminars, conference buyouts (e.g. Demokratiuka, Syntaks, GeoAI).
   - Local competitor venues and geographic coordinates:
     - **Teateret** (Reference Hub): Kongens gate 2, 4610 Kristiansand (`lat: 58.1467, lon: 7.9956`)
     - **Kilden Teater og Konserthus**: Sjølystveien 2, 4610 Kristiansand (`lat: 58.1402, lon: 7.9998`, $d \approx 1.1\text{ km}$) — 1185 cap Concert Hall, 708 cap Theater Hall. Major high-culture / musical competitor.
     - **Q42 Arena**: Dronningens gate 42, 4610 Kristiansand (`lat: 58.1481, lon: 7.9922`, $d \approx 0.4\text{ km}$) — 1300 cap auditorium in downtown Kvadraturen. National comedy tours, major conferences.
     - **Palmesus Festival**: Bystranda (`lat: 58.1450, lon: 8.0090`, $d \approx 1.0\text{ km}$) — 35 000 attendance in early July (Week 27). Massive citywide hotel/restaurant blockage.
     - **Ravnedalen Live**: Ravnedalen Naturpark, Grim (`lat: 58.1600, lon: 7.9730`, $d \approx 2.5\text{ km}$) — 5 000 cap outdoor festival in mid-July (Week 28/29). Direct evening adult music competition.
     - **Dark Season Festival**: Downtown Kristiansand (`lat: 58.1467, lon: 7.9956`, $d \approx 0.3\text{ km}$) — Late October club festival (3 000–5 000 across venues). Direct overlap with Biscenen/CBRC.
     - **Dyreparken / Kaptein Sabeltann**: Dyreparkveien, 4609 Kristiansand (`lat: 58.1810, lon: 8.1520`, $d \approx 11.5\text{ km}$) — 5 000–12 000 daily visitors during summer/autumn holidays; draws massive family tourist volume into the region.

---

## 2. Logic Chain

1. **Feature 11: Agder School Holiday Adapter Design**:
   - School holidays in Norway (specifically Agder county / Kristiansand kommune) follow standard national/county calendars:
     - **Vinterferie**: Always ISO Week 8 in Agder (e.g. 2025-02-17 to 2025-02-23, 2026-02-16 to 2026-02-22).
     - **Påskeferie**: From Palm Monday through 2. påskedag (Easter Monday) (e.g. 2025-04-14 to 2025-04-21, 2026-03-30 to 2026-04-06).
     - **Sommerferie**: From late June (~Week 26) to mid-August (~Week 33) (e.g. 2025-06-21 to 2025-08-17, 2026-06-20 to 2026-08-16).
     - **Høstferie**: Always ISO Week 40 in Agder (e.g. 2025-09-29 to 2025-10-05, 2026-09-28 to 2026-10-04).
     - **Juleferie**: From ~Dec 20/22 to ~Jan 2/4 (e.g. 2025-12-20 to 2026-01-04, 2026-12-19 to 2027-01-03).
     - **Public Holidays & Bridge Days**: Kristi Himmelfartsdag, Inneklemt fredag, 1. mai, 17. mai, 2. pinsedag.
   - **Demand Multiplier Heuristics**:
     - When `is_school_holiday == True`:
       - `family_demand_multiplier`: **1.8x** (standard holidays) / **2.0x** (summer peak) / **1.5x** (Christmas). High daytime activity; families seek puppet theater, matinees, cafe visits.
       - `corporate_demand_multiplier`: **0.4x** (standard holidays) / **0.2x** (summer July shutdown) / **0.3x** (Easter/Christmas). Businesses close; corporate dinners and weekday conferences halt.
     - Pre-Christmas Julebord Season (Nov 15 – Dec 18):
       - `is_school_holiday`: False
       - `corporate_demand_multiplier`: **1.6x** (peak B2B julebord bookings)
       - `family_demand_multiplier`: **1.1x**
     - Regular school term (standard weekday/weekend):
       - `family_demand_multiplier`: **1.0x**
       - `corporate_demand_multiplier`: **1.0x**

2. **Feature 12: Kristiansand City Event Clash Radar Design**:
   - A competing city event affects Teateret based on four deterministic factors:
     1. **Attendance Volume ($A$)**: Larger crowds draw more aggregate attention, transport capacity, and dining footfall. Formulated as $\alpha = \log_{10}(\max(10, A))$.
     2. **Geographic Proximity ($d$) in km**: Events right in Kvadraturen (Q42, Dark Season) or nearby (Kilden, Palmesus) have stronger direct friction than events 11.5 km away (Dyreparken). Formulated via distance attenuation: $\beta = \frac{1}{1 + 0.35 \times d}$.
     3. **Target Demographic Overlap ($\gamma \in [0.0, 1.0]$)**:
        - `adult_culture_music` vs Kilden (0.85), Q42 (0.80), Ravnedalen Live (0.75), Dark Season (0.70).
        - `family_kids` vs Dyreparken (0.85), Kilden family shows (0.90), Palmesus (0.10).
        - `young_adults_party` vs Palmesus (0.90), Dark Season (0.60).
        - `corporate_business` vs Q42 conferences (0.85).
     4. **Time Slot Proximity ($\delta \in [0.4, 1.0]$)**:
        - Same slot (e.g. evening vs evening): $\delta = 1.0$
        - Different slot on same date (e.g. matinee vs evening concert): $\delta = 0.4$
   - **Clash Score Formula**:
     $$\text{ClashScore} = 1.25 \times \alpha \times \beta \times \gamma \times \delta$$
   - **Discrete Severity Thresholds**:
     - $\text{ClashScore} \ge 3.5 \implies$ `"critical"` (Severe clash: Palmesus weekend, major Kilden arena premiere, Q42 sold-out national comedy). Action: Avoid competing major premiere; cross-sell pre/post dining.
     - $2.3 \le \text{ClashScore} < 3.5 \implies$ `"high"` (Strong competition: Ravnedalen Live, Dark Season headliner, KSO symphony concert). Action: Target distinct counter-programming or adjust timing.
     - $1.2 \le \text{ClashScore} < 2.3 \implies$ `"medium"` (Noticeable draw: Dyreparken seasonal day, mid-sized conference). Action: Standard operations, potential family spillover.
     - $\text{ClashScore} < 1.2 \implies$ `"low"` (Negligible clash: small distant event, distinct demographic).

3. **Data Model Specifications**:
   ```python
   # In teateret_brief/models.py or teateret_brief/weather_and_calendar.py

   HolidayType = Literal[
       "vinterferie",
       "paskeferie",
       "sommerferie",
       "hostferie",
       "juleferie",
       "public_holiday",
       "bridge_day",
       "none",
   ]

   ClashSeverity = Literal["low", "medium", "high", "critical"]
   EventDemographic = Literal[
       "adult_culture_music",
       "standup_comedy",
       "family_kids",
       "young_adults_party",
       "corporate_business",
       "broad_public",
   ]

   class SchoolHolidaySignal(BaseModel):
       period: date
       is_holiday: bool
       holiday_name: str | None = None
       week_number: int
       holiday_type: HolidayType = "none"
       family_demand_multiplier: float = Field(ge=0.0, le=5.0)
       corporate_demand_multiplier: float = Field(ge=0.0, le=5.0)
       season_tag: str = Field(min_length=1)

   class CityEventItem(BaseModel):
       event_id: str
       event_name: str
       venue_name: str
       start_date: date
       end_date: date
       time_slot: Literal["matinee", "evening", "all_day"] = "evening"
       distance_km: float = Field(ge=0.0)
       expected_attendance: int = Field(ge=0)
       target_demographic: EventDemographic
       description: str | None = None

   class CityEventClashSignal(BaseModel):
       period: date
       venue_name: str
       event_name: str
       distance_km: float
       expected_attendance: int
       target_demographic: EventDemographic
       demographic_overlap: float = Field(ge=0.0, le=1.0)
       time_slot: Literal["matinee", "evening", "all_day"]
       clash_score: float = Field(ge=0.0)
       clash_severity: ClashSeverity
       impact_summary: str
       mitigation_recommendation: str | None = None
   ```

4. **Static Fixture Specification (2025–2026)**:
   - `sample_data/fixtures/holidays_agder_2025_2026.json`: Complete calendar covering all Agder school holiday periods, Easter dates, summer weeks 26–33, autumn week 40, Christmas periods, and public holidays across 2025 and 2026.
   - `sample_data/fixtures/city_events_kristiansand.json`: Comprehensive 2025–2026 registry of external city events across Kilden (Konsertsalen/Teatersalen), Q42, Palmesus (Bystranda), Ravnedalen Live, Dark Season Festival, Dyreparken (Kaptein Sabeltann / Halloween), Demokratiuka, and Kristiansand Jazzfestival.

---

## 3. Caveats

1. **Movable Feast Calculations**: Easter dates vary year-to-year. The adapter combines explicit rule-based algorithms (e.g. Anonymous Gregorian algorithm for Easter Sunday and derived public holidays) with explicit static fixtures for 2025–2026 to ensure 100% deterministic reproducibility during testing and offline operation.
2. **Dynamic Attendance Variance**: Expected attendance for competing city events represents peak estimates from ticket allocations and venue capacities. When live API feeds are unavailable, the static fixture data provides verified realistic baselines.
3. **No Direct Web Scraping of External Ticketing Sites**: To prevent fragility, SSRF risks, and copyright/rate-limiting issues, the Clash Radar relies on structured static event calendars, schema.org JSON-LD event items, and verified local cultural event registries rather than raw unstructured web scraping.

---

## 4. Conclusion & Actionable Design

### Feature 11: Agder School Holiday Signal Adapter Specification
- **Module**: `teateret_brief/weather_and_calendar.py`
- **Class**: `AgderSchoolHolidayAdapter`
- **Public Methods**:
  - `get_holiday_signal(target_date: date) -> SchoolHolidaySignal`
  - `get_holiday_signals_for_range(start_date: date, end_date: date) -> list[SchoolHolidaySignal]`
  - `is_julebord_season(target_date: date) -> bool` (detects Nov 15 – Dec 18 corporate peak)
- **Deterministic Multipliers**:
  | Scenario | `is_holiday` | `family_multiplier` | `corporate_multiplier` | `season_tag` |
  |---|---|---|---|---|
  | Standard Term Weekday | False | 1.0x | 1.0x | `standard_term` |
  | Vinterferie (Uke 8) | True | 1.8x | 0.5x | `vinterferie_uke8` |
  | Påskeferie (Palmehelg–2.påskedag) | True | 1.8x | 0.4x | `paskeferie` |
  | Sommerferie (Uke 26–33) | True | 2.0x | 0.2x | `sommerferie_uke26_33` |
  | Høstferie (Uke 40) | True | 1.8x | 0.5x | `hostferie_uke40` |
  | Juleferie (Dec 20 – Jan 4) | True | 1.5x | 0.3x | `juleferie` |
  | Julebord Season (Nov 15 – Dec 18) | False | 1.1x | 1.6x | `julebord_season` |
  | Public Holiday / Kristi Himmelfart | True | 1.5x | 0.3x | `public_holiday` |

### Feature 12: Kristiansand City Event Clash Radar Specification
- **Module**: `teateret_brief/weather_and_calendar.py`
- **Class**: `CityEventClashRadar`
- **Public Methods**:
  - `detect_clashes(target_date: date, teateret_genre: EventDemographic = "adult_culture_music", time_slot: Literal["matinee", "evening", "all_day"] = "evening") -> list[CityEventClashSignal]`
  - `get_max_clash_severity(clashes: list[CityEventClashSignal]) -> ClashSeverity`
  - `calculate_clash_score(event: CityEventItem, teateret_genre: EventDemographic, time_slot: str) -> tuple[float, ClashSeverity, float]`
- **Key Local Venues Included**:
  1. *Kilden Teater og Konserthus* ($1.1\text{ km}$, 1185/708 seats)
  2. *Q42 Arena* ($0.4\text{ km}$, 1300 seats)
  3. *Palmesus Festival* ($1.0\text{ km}$, 35 000 visitors)
  4. *Ravnedalen Live* ($2.5\text{ km}$, 5 000 visitors/day)
  5. *Dark Season Festival* ($0.3\text{ km}$, 4 000 visitors)
  6. *Dyreparken Summer/Halloween* ($11.5\text{ km}$, 7 500–12 000 visitors/day)
  7. *Demokratiuka Kristiansand* ($0.0–1.1\text{ km}$, 2 000 visitors/day)

### Static Fixture Structures
1. `sample_data/fixtures/holidays_agder_2025_2026.json`:
   Contains exact date ranges for all school holidays in Agder for 2025 and 2026 with metadata on week numbers and default demand impacts.
2. `sample_data/fixtures/city_events_kristiansand.json`:
   Contains 25+ verified major city events across 2025–2026 with venue names, geographic distances from Teateret, attendance figures, primary demographic tags, and dates.

---

## 5. Verification Method

To independently verify the implementation when built:

1. **Unit Test Command**:
   ```bash
   python -m pytest tests/test_weather_and_calendar.py -v
   ```
2. **Specific Verification Assertions**:
   - `test_agder_vinterferie_multiplier_2025`: Verify date `2025-02-19` returns `is_holiday=True`, `holiday_type="vinterferie"`, `family_demand_multiplier=1.8`, `corporate_demand_multiplier=0.5`.
   - `test_agder_hostferie_multiplier_2026`: Verify date `2026-09-30` returns `is_holiday=True`, `holiday_type="hostferie"`, `week_number=40`.
   - `test_julebord_season_detection`: Verify date `2026-11-25` returns `is_holiday=False`, `corporate_demand_multiplier=1.6`, `season_tag="julebord_season"`.
   - `test_city_event_clash_palmesus`: Verify date `2026-07-03` triggers Palmesus clash with `clash_severity="critical"`, `distance_km=1.0`, `expected_attendance=35000`.
   - `test_city_event_clash_q42_standup`: Verify date `2026-04-24` against Teateret standup triggers `clash_severity="high"` or `"critical"` due to 0.4 km proximity and 1300 attendance.
   - `test_city_event_clash_dyreparken_family_filter`: Verify family show (e.g. Baldrian & Musa) on `2026-07-15` shows high demographic overlap with Dyreparken, but adult evening show shows low clash severity.
   - `test_zero_pii_in_signals`: Verify no attendee or reviewer personal information is present in generated signals.

3. **Compilation & Type Check**:
   ```bash
   python -m compileall teateret_brief tests
   ```
