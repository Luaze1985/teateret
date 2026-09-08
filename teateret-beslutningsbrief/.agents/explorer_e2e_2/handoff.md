# E2E Test Specification & Investigation Report: R3, R4 & Tier 4 Real-World Scenarios

**Author**: `explorer_e2e_2` (Teamwork Explorer Agent)  
**Date**: 2026-08-20  
**Target Milestone**: E2E Testing Track – Requirement 3 (External Signals), Requirement 4 (Brief Rendering & Security/Audit), and Tier 4 (Real-World Scenarios)  
**Status**: Hard Handoff (Investigation & Test Design Complete)

---

## 1. Observation

Direct observations from codebase inspection, architecture documents, schemas, and test infrastructures:

### 1.1 Scope & Requirement Reference
- **ORIGINAL_REQUEST.md** (lines 18–23, 27–41):
  - **R3 (External Context Enrichment)**: MET.no weather forecasts for Kristiansand, Agder school holiday calendar, major city event clashes, Google Places sentiment topics, and Google Trends Agder search interest.
  - **R4 (Automated Decision Brief Rendering & Security Audit)**: Capacity utilization, weekday program gaps, dining cross-sales correlation (+/- 2h window), Markdown/HTML/Email rendering with mandatory disclaimers, pre-flight PII scanning, SHA-256 cryptographic audit manifest, atomic staging directory, repo traversal confinement, network source policies, and CLI entrypoint (`--mode demo` and `--mode live`).
- **TEST_INFRA.md** (lines 8–58):
  - Requires 4 tiers of opaque-box tests:
    - **Tier 1**: Isolated feature coverage ($\ge 5$ tests per major feature area).
    - **Tier 2**: Boundary value analysis, edge cases, error injections ($\ge 5$ tests per feature area).
    - **Tier 3**: Cross-feature interactions and pairwise combinations ($\ge 15$ test suites).
    - **Tier 4**: Realistic end-to-end user workload scenarios ($\ge 6$ complete workflows).

### 1.2 R3: External Signals & Context Architecture Observed
1. **MET.no Weather Signal Specification**:
   - Location: Kristiansand center (`lat=58.1467`, `lon=7.9956`, `altitude=5`).
   - Endpoint: `https://api.met.no/weatherapi/locationforecast/2.0/compact`.
   - Mandatory User-Agent: `TeateretDecisionBrief/1.0 (https://teateret.no; post@teateret.no)`.
   - Response timeseries properties: `air_temperature` (°C), `precipitation_amount` (mm), `symbol_code` (e.g. `rain`, `heavyrain`, `clearsky_day`, `snow`).
   - Demand Modifiers:
     - Rain $> 5.0$ mm or Temp $< 10.0$ °C $\rightarrow$ `high_positive` indoor theater / warm bistro demand modifier.
     - Sunny $> 22.0$ °C (`clearsky_day`) $\rightarrow$ `negative` indoor auditoriums, `positive` outdoor Foajé terrace.
     - Storm warning $\rightarrow$ walk-in restaurant reduction warning.
2. **Agder School Holiday Calendar Specification**:
   - Standard holiday windows: Vinterferie (W8), Påskeferie (Easter), Sommerferie (late-June to mid-August), Høstferie (W40), Juleferie (late-Dec to early-Jan).
   - Demand flags:
     - `family_matinee_boost`: $+30\text{--}50\%$ demand for children/family shows (*Baldrian og Musa*, *Charlie og sjokoladefabrikken*).
     - `weekday_corporate_dip`: Drop in weekday corporate conference bookings during school holidays.
3. **Kristiansand City Event Clash Radar**:
   - Monitored venues & events: *Kilden Teater og Konserthus* (1.2 km, 1185/708 seats), *Q42* (400 m, 1300 seats), *Palmesus* (900 m, 40,000 capacity in July), *Kristiansand Jazzfestival* (0 m, co-located partner), *Punkt Festival* (0 m, partner), *IK Start* (2.5 km, 14,000 seats).
   - Clash heuristic: Match on same date within $\pm 3$ hours with demographic overlap $\rightarrow$ `overlap_severity` in `{"low", "medium", "high", "synergistic"}`.
4. **External Signals 3-Tier Cache & Fallback**:
   - Tier 1: Live Safe HTTPS request (Port 443, Public DNS IP, 15s timeout).
   - Tier 2: Disk TTL Cache (`.cache/external_signals/<sha256>.json`, TTL: Weather 3h, Holidays 30d, Clashes 24h).
   - Tier 3: Deterministic Static Fixtures (`sample_data/fixtures/` offline mode).
5. **Google Places & Google Trends Adapters**:
   - `teateret_brief/google_places.py` (lines 38–231): Google Places GBP ratings, review counts, 5 sentiment topics (`mat`, `service`, `lyd`, `atmosfære`, `pris`), reviewer name redaction (`[ANMELDER]`), PII redaction (`[MASKERT_EPOST]`, `[MASKERT_TELEFON]`), review cap (`assert_review_limit(count, 20)`).
   - `teateret_brief/google_trends.py` (lines 19–117): pytrends Agder (`NO-42`) search interest, trend direction (`rising` $> +15\%$, `falling` $< -15\%$, `stable`).
   - `teateret_brief/schema_events.py` (lines 30–198): Schema.org JSON-LD extractor parsing `@type: Event`, `startDate`, `location`, `offers.availability` (`tilgjengelig`, `utsolgt`, `få billetter`), `price`.

### 1.3 R4: Brief Rendering, Security Audit & CLI Architecture Observed
1. **Decision Brief Data Contract & Models** (`teateret_brief/models.py`, lines 114–153):
   - `Recommendation`: `id`, `action`, `rationale`, `source_ids`, `expected_value`, `effort` (`Literal["low", "medium", "high"]`).
   - `AnalysisOutput`: `recommendations: list[Recommendation] = Field(max_length=3)` (hard constraint of max 3 recommendations).
   - `Brief`: Combines `run_id`, `created_at`, `status`, `signals`, `recommendations` (max 3), `source_ids`, `sources`, `warnings`, `market_observations`, `review_summaries`.
2. **Multi-Format Rendering Engine** (`teateret_brief/render.py`, lines 8–179):
   - Mandatory disclaimer: `"UTKAST – IKKE SENDT – MÅ KONTROLLERES AV ET MENNESKE"`.
   - `render_markdown(brief)`: Markdown document with disclaimer blockquote, run status, review summaries, market signals, signals, recommendations, warnings, and source citations.
   - `render_html(brief)`: Self-contained styled HTML with warning banner (`<p class="draft">`), review summary cards, escaped HTML entities.
   - `render_email(brief)`: Plaintext email draft with subject line `Emne: UTKAST – ukentlig beslutningsbrief – <run_id>`, top 4 signals, prioritized actions with why/value/effort, warnings, and source links.
3. **Pre-Flight PII Scanner & Security Defenses** (`teateret_brief/security.py`, lines 30–211):
   - `RepoPaths`: Resolves relative paths against workspace root, rejects absolute paths, rejects `..` path escapes, and rejects symlinks pointing outside root.
   - `SourcePolicy`: HTTPS-only, port 443, no embedded credentials, domain allowlist, and public DNS IP validation (blocks loopback `127.0.0.1`, RFC 1918 private IPs, multicast, IPv6 loopback).
   - `scan_public_artifact(text)`: Scans all rendered artifacts for email and phone patterns before disk write. If detected, pipeline raises `ValueError`, blocks output publication, and sets `pii_scan_status: not_publishable`.
   - `safe_error_summary(exc)`: Masks sensitive exceptions to prevent PII leakage through error traces.
4. **Cryptographic Audit Manifest & Atomic Staging** (`teateret_brief/pipeline.py`, lines 102–389):
   - Staging isolation: Writes to `runs/.staging/<run_id>`, computes SHA-256 hashes of all artifacts, writes `manifest.json` and `events.json`, then atomically moves `runs/.staging/<run_id>` to `runs/<run_id>`.
   - On error: Cleans staging, writes `errors.json`, `events.json`, and `manifest.json` with `status: blocked` and `stop_reason`.
   - `manifest.json`: Records SHA-256 hashes of input payload (`input_sha256`), decision questions (`decision_questions_sha256`), source documents (`content_sha256`), and all generated outputs.
5. **CLI Entrypoint** (`teateret_brief/cli.py`, lines 28–193):
   - `--mode demo`: Offline execution with deterministic fixtures (`FixtureFetcher`, `FixtureRoles`, `FixtureGooglePlacesAdapter`, `FixtureGoogleTrendsAdapter`, `FixtureSchemaEventExtractor`). Exit code 0 for `completed` or `warning`, exit code 2 for `blocked`.
   - `--mode live`: Safety gated; rejects execution unless `runtime.yml` has `live_mode_enabled: true`, `--allow-live-network` and `--allow-live-model` are supplied, `--sales` is provided, and `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` are set.

---

## 2. Logic Chain & Detailed Test Specifications

### 2.1 R3: External Context Enrichment Test Specifications

```mermaid
flowchart TD
    subgraph ExternalSources["External Public Signals (R3)"]
        MET["MET.no Locationforecast 2.0 (Kristiansand 58.1467, 7.9956)"]
        HOL["Agder School Holiday Calendar (Skolerute)"]
        CLS["Kristiansand Event Clash Radar (Kilden, Q42, Palmesus)"]
        GBP["Google Places (GBP) Sentiment & Rating"]
        GT["Google Trends Agder (NO-42) Search Interest"]
        SCH["Schema.org JSON-LD Event Scraper"]
    end

    subgraph AdaptersAndCache["Adapters & 3-Tier Cache"]
        T1["Tier 1: Live HTTPS (SafeHttpFetcher / Adapters)"]
        T2["Tier 2: Disk TTL Cache (.cache/external_signals/)"]
        T3["Tier 3: Deterministic Static Fixtures (sample_data/fixtures/)"]
    end

    subgraph DataNormalization["Normalized Signal Observations"]
        WS["WeatherForecastSignal"]
        HS["SchoolHolidaySignal"]
        CS["CityEventClashSignal"]
        MO["MarketObservation & ReviewSummary"]
    end

    MET --> T1
    HOL --> T1
    CLS --> T1
    GBP --> T1
    GT --> T1
    SCH --> T1

    T1 -- "Failure / Offline" --> T2
    T2 -- "Expired / Missing" --> T3

    T1 --> WS & HS & CS & MO
    T2 --> WS & HS & CS & MO
    T3 --> WS & HS & CS & MO
```

#### Test Suite 3.1: MET.no Weather Forecast Integration
1. **`test_met_no_live_response_parsing_valid`**:
   - *Given*: Valid MET.no Locationforecast 2.0 compact JSON payload for Kristiansand.
   - *When*: Adapter parses timeseries data for date `2026-03-13`.
   - *Then*: Produces `WeatherForecastSignal` with `temperature_celsius`, `precipitation_mm`, `symbol_code`, and demand modifier.
   - *Assertions*: `signal.precipitation_mm >= 0.0`, `signal.symbol_code in ALLOWED_WEATHER_SYMBOLS`, `signal.rationale` is non-empty.
2. **`test_met_no_user_agent_header_enforcement`**:
   - *Given*: HTTP client configured for MET.no requests.
   - *When*: Request headers are inspected.
   - *Then*: `User-Agent` header matches `r"^TeateretDecisionBrief/\d+\.\d+ \(https://teateret\.no; [^@]+@[^)]+\)$"`.
3. **`test_met_no_demand_modifier_bva_classification`**:
   - *Boundary Values*:
     - Case A (Rain $> 5.0$ mm, Temp $< 10.0$ °C): `indoor_demand_modifier == "high_positive"`.
     - Case B (Rain $0.0$ mm, Temp $23.5$ °C, symbol `clearsky_day`): `indoor_demand_modifier == "negative"`, outdoor terrace rationale.
     - Case C (Rain $1.0$ mm, Temp $15.0$ °C, symbol `cloudy`): `indoor_demand_modifier == "neutral"`.
     - Case D (Severe wind $> 20.0$ m/s or storm symbol): Generates walk-in restaurant reduction warning.
4. **`test_met_no_http_304_not_modified_handling`**:
   - *Given*: Cache contains valid payload with `Last-Modified` timestamp.
   - *When*: Live request sends `If-Modified-Since` and server returns HTTP 304.
   - *Then*: Adapter returns cached payload without re-parsing or disk re-write, update cache timestamp.
5. **`test_met_no_http_error_degradation_to_cache_and_fixture`**:
   - *Given*: Live request raises `httpx.HTTPStatusError` (HTTP 503) or timeout.
   - *When*: Adapter executes fallback logic.
   - *Then*: Serves disk cache if within TTL; if cache missing, serves deterministic static fixture without raising uncaught exception.

#### Test Suite 3.2: Agder School Holiday Calendar Signal
1. **`test_school_holiday_detection_vacation_windows`**:
   - *Given*: Agder school calendar skolerute 2025/2026.
   - *When*: Dates evaluated:
     - `2026-02-23` (Vinterferie Uke 8) $\rightarrow$ `is_holiday=True`, `holiday_type="winter"`.
     - `2026-04-01` (Påskeferie) $\rightarrow$ `is_holiday=True`, `holiday_type="easter"`.
     - `2026-07-15` (Sommerferie) $\rightarrow$ `is_holiday=True`, `holiday_type="summer"`.
     - `2026-10-01` (Høstferie Uke 40) $\rightarrow$ `is_holiday=True`, `holiday_type="autumn"`.
     - `2026-12-28` (Juleferie) $\rightarrow$ `is_holiday=True`, `holiday_type="christmas"`.
   - *Then*: `family_matinee_boost == True`, `weekday_corporate_dip == True`.
2. **`test_school_holiday_regular_term_day`**:
   - *Given*: Regular school Wednesday (`2026-11-11`).
   - *When*: Adapter checks date.
   - *Then*: `is_holiday == False`, `holiday_type == "none"`, `family_matinee_boost == False`, `weekday_corporate_dip == False`.

#### Test Suite 3.3: Kristiansand City Event Clash Radar
1. **`test_city_clash_detection_kilden_major_theater_premiere`**:
   - *Given*: Teateret show *Svanesjøen* on Hovedscenen (`2026-03-13 19:00`) and Kilden staging major musical (`2026-03-13 19:30`).
   - *When*: Clash radar evaluates collision.
   - *Then*: Flags `CityEventClashSignal` with `venue_name="Kilden Teater og Konserthus"`, `venue_distance_km=1.2`, `overlap_severity="high"`.
2. **`test_city_clash_palmesus_festival_impact`**:
   - *Given*: Weekend of Palmesus (`2026-07-03` to `2026-07-04`, 40k guests, Bystranda 900m).
   - *When*: Clash radar evaluates date.
   - *Then*: Flags `overlap_severity="high"`, description notes heavy restaurant terrace surge and indoor theater vacancy risk.
3. **`test_city_clash_synergy_partner_festivals`**:
   - *Given*: Kristiansand Jazzfestival or Punkt Festival co-hosted at Teateret (`distance_km=0.0`).
   - *When*: Clash radar evaluates event.
   - *Then*: Flags `overlap_severity="synergistic"`, noting positive cross-attendance and dining synergy.
4. **`test_city_clash_no_conflict_quiet_day`**:
   - *Given*: Date with no external major events scheduled in Kristiansand.
   - *When*: Clash radar evaluates date.
   - *Then*: Returns empty `city_clashes` list, zero warnings.

#### Test Suite 3.4: 3-Tier Cache & Fault Isolation
1. **`test_3tier_cache_hit_bypasses_network`**:
   - *Given*: Cache file `.cache/external_signals/<hash>.json` exists with age $< \text{TTL}$.
   - *When*: Retrieval is triggered with mocked disabled network.
   - *Then*: Cache returns data instantly; network client is never invoked.
2. **`test_3tier_cache_miss_fetches_and_persists`**:
   - *Given*: Cache empty.
   - *When*: Live fetch succeeds.
   - *Then*: Writes payload to `.cache/external_signals/<hash>.json` with metadata timestamp.
3. **`test_3tier_corrupt_cache_graceful_recovery`**:
   - *Given*: Cache file exists with corrupted/truncated JSON (`{ "invalid_json": `).
   - *When*: Fetcher encounters corrupt cache.
   - *Then*: Discards corrupted cache, falls back to live fetch or static fixture, logs warning, does not crash.
4. **`test_3tier_complete_network_outage_fixture_fallback`**:
   - *Given*: All external URLs offline (DNS failure / 5xx error / network timeout).
   - *When*: Pipeline runs in offline/development mode.
   - *Then*: Loads static fixtures from `sample_data/fixtures/`, adds warning to `manifest.json`, pipeline completes with status `warning` (or `completed` if fixtures approved).

#### Test Suite 3.5: Google Places Sentiment, Trends & Schema.org Events
1. **`test_google_places_sentiment_scoring_accuracy`**:
   - *Given*: Reviews with positive dining phrases ("maten var fantastisk", "nydelig dessert") vs slow service ("lang ventetid", "treg betjening").
   - *When*: `_analyze_sentiment` processes reviews.
   - *Then*: `mat` topic classified as `positive`, `service` classified as `negative`.
2. **`test_google_places_pii_and_reviewer_name_redaction`**:
   - *Given*: Review: `"Ola Nordmann her! Kontakt meg på ola@example.com eller tlf 99887766. Maten var herlig."` with author `"Ola Nordmann"`.
   - *When*: Redaction runs.
   - *Then*: Quotes contain `[ANMELDER]`, `[MASKERT_EPOST]`, `[MASKERT_TELEFON]`, and zero occurrences of `"Ola"`, `"Nordmann"`, `"ola@example.com"`, or `"99887766"`.
3. **`test_google_places_review_count_cap_enforced`**:
   - *Given*: Google Places API returns 50 reviews.
   - *When*: Adapter parses response with `max_reviews_per_place = 20`.
   - *Then*: Slices to 20 reviews; asserts `assert_review_limit(20, 20)` succeeds.
4. **`test_google_trends_agder_direction_classification`**:
   - *Given*: Keyword series `[40, 50]` (+25% increase) vs `[50, 40]` (-20% decrease) vs `[50, 52]` (+4% change).
   - *When*: `_trend_direction` calculates trend.
   - *Then*: Returns `"rising"`, `"falling"`, and `"stable"` respectively.
5. **`test_schema_events_sold_out_flagging`**:
   - *Given*: JSON-LD event with `offers.availability = "https://schema.org/SoldOut"`.
   - *When*: `parse_jsonld_events` extracts event.
   - *Then*: Output contains `"Billettstatus: utsolgt"`.

---

### 2.2 R4: Brief Rendering, Security Audit, Manifest & CLI Test Specifications

```mermaid
flowchart TD
    subgraph DataInputs["Verified Ingestion & Analytics"]
        SO["SalesObservation (GastroPlanner)"]
        EM["EventMatcher (ADR 0002 3-Level)"]
        AN["Analytics (Capacity & Cross-Sales)"]
        EX["ExternalContextEnrichment"]
    end

    subgraph PipelineFlow["Brief Pipeline Coordinator"]
        ROLES["Roles (Reader -> Analyst -> Verifier)"]
        BREC["Brief Model (Max 3 Recommendations)"]
        REND["Render Engine (Markdown / HTML / Email)"]
        PII["Pre-Flight PII Scanner (Zero PII Gate)"]
        HASH["SHA-256 Hasher (Inputs, Questions, Artifacts)"]
    end

    subgraph AtomicPersistence["Atomic Staging & Audit Trail"]
        STG["runs/.staging/<run_id>/"]
        CHK["Validation Gate (PII Scan + Manifest Integrity)"]
        FIN["runs/<run_id>/ (brief.md, brief.html, email.txt, manifest.json)"]
    end

    SO & EM & AN & EX --> ROLES
    ROLES --> BREC
    BREC --> REND
    REND --> PII
    PII -- "Pass" --> STG
    STG --> HASH --> CHK
    CHK -- "Atomic Replace" --> FIN
```

#### Test Suite 4.1: Capacity Utilization & Dark Weekday Gaps
1. **`test_capacity_utilization_sellout_detection`**:
   - *Given*: Show with 380 sold tickets out of 400 capacity (95.0%).
   - *When*: Analytics evaluates capacity.
   - *Then*: Flags show as `high_demand_sellout` ($\ge 90\%$).
2. **`test_capacity_utilization_vacancy_alert`**:
   - *Given*: Show with 290 sold tickets out of 350 capacity (82.8%, 60 open seats) or underperforming show with 40 sold out of 148 (27.0%).
   - *When*: Analytics evaluates capacity.
   - *Then*: Flags vacancy alert with exact unsold count and revenue opportunity.
3. **`test_dark_weekday_gap_analysis`**:
   - *Given*: Weekly schedule with active shows on Fri/Sat/Sun, but Tue/Wed have 0 scheduled events across all stages.
   - *When*: Analytics runs gap detection.
   - *Then*: Identifies dark Tuesday/Wednesday gap and suggests low-threshold event concepts (speed dating, pub quiz, acoustic open mic).
4. **`test_dining_cross_sales_ratio_calculation`**:
   - *Given*: Event with 380 tickets, 120 table reservations, 65 package menus.
   - *When*: Analytics computes dining cross-sales correlation.
   - *Then*: Calculates table attachment ratio $= 120/380 = 31.6\%$, package attachment ratio $= 65/380 = 17.1\%$, explicitly classified as *nærhetskorrelasjon* (needs_review / Level 3 proximity).

#### Test Suite 4.2: Prioritized Recommendations Engine
1. **`test_recommendations_bounded_to_max_three`**:
   - *Given*: Analyst attempts to return 4 recommendations.
   - *When*: Pydantic validates `AnalysisOutput(recommendations=[rec1, rec2, rec3, rec4])`.
   - *Then*: Raises `ValidationError` (enforcing max 3 recommendations constraint).
2. **`test_recommendations_unique_ids_enforced`**:
   - *Given*: Analyst returns two recommendations with ID `"rec-1"`.
   - *When*: Pydantic validates `AnalysisOutput`.
   - *Then*: Raises `ValueError("Anbefalings-ID-er må være unike.")`.
3. **`test_recommendations_source_provenance_validation`**:
   - *Given*: Analyst recommendation references `source_ids=["unknown-source"]` not in fetched documents.
   - *When*: Pipeline validates analyst output.
   - *Then*: Raises `ValueError("Analytiker returnerte ukjent kilde-ID.")` and transitions run to `status: blocked`.

#### Test Suite 4.3: Multi-Format Brief Rendering & Mandatory Disclaimers
1. **`test_render_markdown_exact_disclaimer_and_structure`**:
   - *Given*: Verified `Brief` object.
   - *When*: `render_markdown(brief)` executes.
   - *Then*: 
     - First blockquote contains verbatim `> UTKAST – IKKE SENDT – MÅ KONTROLLERES AV ET MENNESKE`.
     - Contains headers `# Ukentlig beslutningsbrief for Teateret`, `Run-ID: <id>`, `Status: <status>`, `## Signaler`, `## Anbefalte handlinger`, `## Kilder`.
     - Lists all recommendations with action, rationale, expected value, effort, and source links.
2. **`test_render_html_escaping_and_draft_banner`**:
   - *Given*: Brief containing special characters (`<script>`, `&`, `"`) in claims or actions.
   - *When*: `render_html(brief)` executes.
   - *Then*:
     - HTML begins with `<!doctype html><html lang="no">`.
     - Contains `<p class="draft"><strong>UTKAST – IKKE SENDT – MÅ KONTROLLERES AV ET MENNESKE</strong></p>`.
     - All user/source strings are HTML escaped (`&lt;script&gt;`).
3. **`test_render_email_subject_and_structure`**:
   - *Given*: Verified `Brief` object.
   - *When*: `render_email(brief)` executes.
   - *Then*:
     - Line 1: `Emne: UTKAST – ukentlig beslutningsbrief – <run_id>`.
     - Line 3: `UTKAST – IKKE SENDT – MÅ KONTROLLERES AV ET MENNESKE`.
     - Contains top 4 signals, prioritized actions with `Hvorfor:`, `Verdi/innsats:`, `Kilder:`.
4. **`test_rendering_content_synchronization_across_formats`**:
   - *Given*: Generated `brief.md`, `brief.html`, and `email.txt`.
   - *When*: Comparing extracted recommendations and claims across all 3 files.
   - *Then*: Exact same recommendation IDs, actions, and source citations appear in all three artifacts.

#### Test Suite 4.4: Pre-Flight Output PII Scanning
1. **`test_preflight_pii_scanner_blocks_email_leak`**:
   - *Given*: Recommendation rationale inadvertently includes `"Kontakt bookingansvarlig på ole@teateret.no"`.
   - *When*: Pipeline executes pre-flight scan `scan_public_artifact`.
   - *Then*: Raises `ValueError("Genererte artefakter inneholder direkte kontaktopplysninger.")`, purges staging, creates `errors.json`, and records `status: blocked` with `pii_scan_status: not_publishable`.
2. **`test_preflight_pii_scanner_blocks_phone_leak`**:
   - *Given*: Recommendation action includes `"Ring artistkontakt på +47 99887766"`.
   - *When*: Pipeline executes pre-flight scan.
   - *Then*: Hard blocks output publication.
3. **`test_preflight_pii_scanner_clean_pass_on_legitimate_content`**:
   - *Given*: Brief containing dates (`2026-03-13`), Norwegian kroner (`185 000,00 NOK`), public artist names, and stage names.
   - *When*: Pre-flight scan executes.
   - *Then*: Returns `findings = []`, scan status passes.

#### Test Suite 4.5: Cryptographic Audit Manifest (`manifest.json`)
1. **`test_manifest_sha256_output_integrity`**:
   - *Given*: Completed pipeline run directory `runs/<run_id>/`.
   - *When*: Manifest is parsed and every output file (`brief.md`, `brief.html`, `email.txt`) is read from disk and hashed with SHA-256.
   - *Then*: Disk SHA-256 matches the hash recorded in `manifest["outputs"]` with 100% byte precision.
2. **`test_manifest_input_hash_determinism`**:
   - *Given*: Identical source list, document content hashes, sales observations, and decision questions.
   - *When*: Input hash is computed via `_hash_payload`.
   - *Then*: Generates identical 64-character hex string across independent pipeline runs.
3. **`test_manifest_audit_fields_completeness`**:
   - *Given*: `manifest.json`.
   - *When*: Inspected for compliance fields.
   - *Then*: Contains `run_id`, `started_at`, `finished_at`, `status`, `config_version`, `prompt_versions`, `decision_questions`, `decision_questions_sha256`, `input_sha256`, `sources_attempted`, `sources_succeeded`, `source_records` (with content SHA-256 and extractor name), `model`, `call_count`, `token_usage`, `outputs`, `pii_scan_status`.
4. **`test_manifest_zero_pii_guarantee`**:
   - *Given*: Serialized `manifest.json`.
   - *When*: Scanned with `_EMAIL_RE` and `_PHONE_RE`.
   - *Then*: Zero matches detected.

#### Test Suite 4.6: Atomic Staging Directory Persistence
1. **`test_atomic_staging_clean_move_on_success`**:
   - *Given*: Successful pipeline run.
   - *When*: Run completes.
   - *Then*: `runs/<run_id>` exists, `runs/.staging/<run_id>` is removed, output files are accessible.
2. **`test_staging_cleanup_on_unhandled_failure`**:
   - *Given*: Unhandled exception during verification or artifact writing.
   - *When*: Pipeline catches exception and invokes `_finish_blocked`.
   - *Then*: Incomplete drafts are deleted; `runs/<run_id>` contains only `errors.json`, `events.json`, and `manifest.json`.
3. **`test_invalid_run_id_path_injection_rejected`**:
   - *Given*: Malicious run IDs (`"../escape"`, `"../../root"`, `"/absolute"`, `"-start"`, `"end-"`, `"invalid space"`).
   - *When*: Pipeline receives run ID.
   - *Then*: Raises `ValueError("Ugyldig run-ID.")` before creating any staging directories.
4. **`test_duplicate_run_id_rejected`**:
   - *Given*: An existing run directory `runs/run-101`.
   - *When*: Pipeline invoked with `run_id="run-101"`.
   - *Then*: Raises `FileExistsError("Run finnes allerede: run-101")`.

#### Test Suite 4.7: Security RepoPaths & Network SourcePolicy
1. **`test_repopaths_blocks_traversal_and_absolute_paths`**:
   - *Given*: `RepoPaths(workspace_root)`.
   - *When*: Evaluates `/etc/passwd`, `C:\Windows\System32`, `../secret.yml`, `runs/../../outside.txt`.
   - *Then*: Raises `PathPolicyError`.
2. **`test_repopaths_blocks_external_symlinks`**:
   - *Given*: Symlink inside workspace pointing to a directory outside workspace root.
   - *When*: `input_path` or `output_path` resolves symlink.
   - *Then*: Raises `PathPolicyError("Symlink forlater det bekreftede repoet.")`.
3. **`test_sourcepolicy_blocks_non_https_and_credentials`**:
   - *Given*: `SourcePolicy(allowed_hosts={"example.com"})`.
   - *When*: Evaluates `http://example.com`, `ftp://example.com`, `https://user:pass@example.com`.
   - *Then*: Raises `SourcePolicyError`.
4. **`test_sourcepolicy_blocks_non_standard_ports`**:
   - *Given*: `https://example.com:8443/program` or `https://example.com:8080/events`.
   - *When*: Validated against SourcePolicy.
   - *Then*: Raises `SourcePolicyError("Bare standard HTTPS-port er tillatt.")`.
5. **`test_sourcepolicy_ssrf_blocks_private_and_loopback_ips`**:
   - *Given*: Allowed host `example.com` whose DNS resolves to `127.0.0.1`, `10.0.0.1`, `192.168.1.1`, `172.16.0.1`, `169.254.169.254` (AWS metadata), or `::1`.
   - *When*: `policy.validate("https://example.com/api")` resolves addresses.
   - *Then*: Raises `SourcePolicyError("Kilden peker til en privat eller reservert adresse.")`.
6. **`test_sourcepolicy_allows_verified_public_https`**:
   - *Given*: Allowed host `api.met.no` resolving to global public IP `157.249.44.221`.
   - *When*: Validated against SourcePolicy.
   - *Then*: Returns `ApprovedUrl(url="https://api.met.no/...", host="api.met.no")`.

#### Test Suite 4.8: CLI Execution Modes (`--mode demo` and `--mode live`)
1. **`test_cli_demo_mode_full_offline_pipeline`**:
   - *Given*: CLI invoked with `--mode demo --sales sample_data/gastroplanner_sample_2026.csv`.
   - *When*: CLI runs in temporary environment.
   - *Then*: Completes with exit code 0; outputs stdout `STATUS: COMPLETED`, `RUN: <id>`, `OUTPUT: <dir>`; creates `brief.md`, `brief.html`, `email.txt`, `manifest.json`.
2. **`test_cli_demo_mode_with_all_signal_flags`**:
   - *Given*: CLI invoked with `--google-places --google-trends --schema-events`.
   - *When*: Pipeline executes with fixtures.
   - *Then*: `brief.md` includes sections for Google Reviews, Google Trends, and Schema Events.
3. **`test_cli_live_mode_safety_gate_disabled_in_runtime`**:
   - *Given*: Default `config/runtime.yml` with `live_mode_enabled: false`.
   - *When*: CLI invoked with `--mode live --allow-live-network --allow-live-model`.
   - *Then*: Exits immediately with `SystemExit` containing message `"Live-modus er deaktivert i runtime-konfigurasjonen"`.
4. **`test_cli_live_mode_safety_gate_missing_allow_flags`**:
   - *Given*: `runtime.yml` has `live_mode_enabled: true`.
   - *When*: CLI invoked without `--allow-live-network` or `--allow-live-model`.
   - *Then*: Exits with `SystemExit("Live-modus krever både --allow-live-network og --allow-live-model.")`.
5. **`test_cli_live_mode_safety_gate_missing_api_keys`**:
   - *Given*: Live mode enabled and allow flags present, but `ANTHROPIC_API_KEY` is not set in environment.
   - *When*: CLI runs.
   - *Then*: Exits with `SystemExit("ANTHROPIC_API_KEY og ANTHROPIC_MODEL må settes i miljøet.")`.

---

## 3. Tier 4: Real-World Workload Scenarios (End-to-End User Workflows)

These scenarios represent end-to-end operational workflows executed by theater leadership (Amir) and system operators at Teateret Kristiansand.

```
+----------------------------------------------------------------------------------------------------+
|                                  Tier 4 Real-World Workload Matrix                                 |
+----+--------------------------------------------+-----------------------+--------------------------+
| #  | Scenario Name                              | Period / Context      | Key Signals & Dynamics   |
+----+--------------------------------------------+-----------------------+--------------------------+
| 1  | High-Season Spring Sellout & Dining Peak   | March 2026 (Weekend)  | Heavy Rain + 95% Sold    |
| 2  | Low-Season Dark Weekday Gap Activation     | April 2026 (Midweek)  | Dark Tue/Wed + Quiz Trend|
| 3  | Agder School Holiday Family Matinee Surge  | Oct 2026 (Høstferie)  | School Vacation + Rain   |
| 4  | Major City Clash Storm (Palmesus / Kilden) | July 2026 (Summer)    | 40k Festival + 60 Vacant |
| 5  | Source Network Outage & Cache Degradation  | Operational Incident  | HTTP 503 + TTL Fallback  |
| 6  | Adversarial PII Injection Ingestion Block  | Security Defense      | Injected FNR / Emails    |
+----+--------------------------------------------+-----------------------+--------------------------+
```

### Scenario 1: High-Season Spring Weekend Sellout & Cross-Sales Peak (March 2026)
- **Business Context**: On Friday `2026-03-13`, Teateret stages *Svanesjøen* on Hovedscenen (capacity 400) and *Restaurantkveld* in Foajeen.
- **External Signals**:
  - MET.no: Heavy cold rain (12.5 mm, 4.2°C) $\rightarrow$ `high_positive` indoor theater & bistro modifier.
  - School Calendar: Regular school term.
  - City Clash: No colliding major premieres at Kilden or Q42.
  - Google Places: 4.6 rating with positive dining/ambiance sentiment.
- **GastroPlanner Input**:
  - `EVT-260313`: 380 tickets sold (95.0% capacity), 120 table reservations, 65 package menus, 185,000.00 NOK gross revenue.
- **End-to-End Execution Flow**:
  1. GastroPlanner CSV parsed with zero PII.
  2. Level 1 ID match connects `EVT-260313` to *Svanesjøen* in 129-event database.
  3. Analytics computes 95% capacity utilization and 31.6% table attachment ratio.
  4. Reader/Analyst/Verifier roles synthesize findings into 3 prioritized recommendations:
     - Rec 1: Increase kitchen and bar staffing by 2 shifts to handle the 120 reserved tables and walk-in rain traffic.
     - Rec 2: Release 20 standing-room / bar-view tickets for Hovedscenen to monetize remaining sellout demand.
     - Rec 3: Direct pre-show dining guests toward Foajé lounge to maximize beverage turnover before curtain call.
  5. Markdown, HTML, and Email rendered with mandatory disclaimer.
  6. Pre-flight PII scanner passes with 0 findings.
  7. SHA-256 manifest generated and atomic staging moves to `runs/<run_id>`.
- **Verifications**: Status `completed`, 3 recommendations, SHA-256 verified, zero PII.

### Scenario 2: Low-Season Dark Weekday Gap & Local Audience Activation (April 2026)
- **Business Context**: Midweek April `2026-04-21` (Tuesday) and `2026-04-22` (Wednesday).
- **External Signals**:
  - MET.no: Mild spring weather (14.0°C, partly cloudy).
  - Google Trends Agder: Rising search interest (+28%) for "quiz kristiansand" and "standup sørlandet".
  - Calendar: Dark weekdays with 0 scheduled ticketed shows on Hovedscenen, Biscenen, or Intimscenen.
- **GastroPlanner Input**:
  - `2026-04-22`: Speed dating 30–45 in Foajeen (`EVT-260422`, 38/40 sold, 16,200.00 NOK), but main auditoriums are unutilized.
- **End-to-End Execution Flow**:
  1. Ingestion maps Foajeen speed dating; analytics flags Hovedscenen, Biscenen, and Intimscenen as dark on Tue/Wed.
  2. Analytics calculates 0 NOK auditorium revenue for midweek slots.
  3. Pipeline synthesizes market trend with stage vacancy:
     - Rec 1: Launch recurring Wednesday culture/general quiz in Biscenen (148 cap) to capture verified Agder search demand.
     - Rec 2: Host open acoustic songwriter night or podcast recording in Intimscenen (67 cap) on dark Tuesdays.
     - Rec 3: Offer combined "Speed Date + Bistro Dinner" package to increase average spend per speed-dating attendee from 426 NOK to 750 NOK.
  4. All 3 artifacts generated with consistent recommendations.
- **Verifications**: Identifies dark stage gaps; recommendations bounded to 3; audit manifest clean.

### Scenario 3: Agder School Holiday Matinee & Family Dining Surge (October 2026 - Høstferie Uke 40)
- **Business Context**: School autumn vacation (Høstferie, Week 40).
- **External Signals**:
  - Agder Skolerute: `is_holiday=True`, `holiday_type="autumn"`, `family_matinee_boost=True`, `weekday_corporate_dip=True`.
  - MET.no: Rainy 7.5°C $\rightarrow$ families seek indoor activities.
- **GastroPlanner Input**:
  - Children's theater *Baldrian og Musa* in Intimscenen (65/70 sold, 92.8%), family dining preorders (35 pancake packages).
- **End-to-End Execution Flow**:
  1. Holiday signal correlates with high family show occupancy.
  2. Analytics flags weekday corporate booking slump and children's show sellout.
  3. Executive recommendations:
     - Rec 1: Schedule second afternoon matinee of *Baldrian og Musa* at 14:00 to absorb overflow family demand.
     - Rec 2: Bundle family theater tickets with child-friendly bistro packages.
     - Rec 3: Pause B2B corporate marketing outreach during Week 40 due to corporate vacation dip.
  4. Brief generated with disclaimer and cryptographic manifest.
- **Verifications**: Holiday boost correctly recognized; recommendations actionable and tailored for Amir.

### Scenario 4: Major City Clash Storm Event (Palmesus / Kilden Festival Collision - July 2026)
- **Business Context**: Weekend `2026-07-17` during Palmesus beach festival (40k guests at Bystranda, 900m) and Kilden Summer Premiere.
- **External Signals**:
  - Clash Radar: Flags Palmesus (`overlap_severity="high"`, Bystranda 900m) and Kilden (`overlap_severity="medium"`).
  - MET.no: Sunny summer evening (25.5°C, `clearsky_day`).
- **GastroPlanner Input**:
  - `EVT-260717`: *Sommerstandup* on Hovedscenen (290/350 sold, 82.8%, 60 open seats), but Foajeen & Restaurant terrace revenue surges with 150 table bookings (98,500.00 NOK).
- **End-to-End Execution Flow**:
  1. System detects clash between Palmesus party crowd and indoor theater show.
  2. Analytics flags 60 unsold standup seats alongside massive terrace dining volume.
  3. Recommendations:
     - Rec 1: Reassign 3 front-of-house staff from auditorium ushering to outdoor terrace bar service.
     - Rec 2: Launch same-day social media flash offer for the 60 remaining standup seats targeting local theatergoers avoiding festival crowds.
     - Rec 3: Introduce festival pre-drink and late-night tapas menu in Foajeen to capture walking traffic along Kongens gate.
  4. Output files written to atomic staging and moved to final run directory.
- **Verifications**: Clash severity flagged in brief; staffing adjustment recommended; manifest verified.

### Scenario 5: External Source Network Failure & Graceful Degradation
- **Business Context**: Operational execution during live external outage (MET.no returns HTTP 503; VisitSørlandet RSS feed times out).
- **External Signals**:
  - Live fetch fails $\rightarrow$ 3-tier cache retrieves cached weather data (2 hours old, within 3h TTL).
  - Pipeline logs `source_errors`: `[{"source_id": "met-no", "error": "Kildepolicyen avviste forespørselen eller innholdet."}]`.
- **End-to-End Execution Flow**:
  1. SafeHttpFetcher catches network exceptions via `safe_error_summary`.
  2. Cached signals and verified sales data supplied to Reader and Analyst roles.
  3. Pipeline assigns brief status `"warning"` due to source errors.
  4. Output files `brief.md`, `brief.html`, `email.txt` generated, containing a prominent `## Varsler` section explaining the source degradation.
  5. `errors.json` written alongside `manifest.json`.
- **Verifications**: Exit code 0 (warning status); `errors.json` exists; zero unhandled crashes; manifest lists `sources_failed`.

### Scenario 6: Adversarial PII Injection & Malicious CSV Column Gate
- **Business Context**: An unvetted export containing customer personal data is submitted to the engine.
- **Input Data**:
  - CSV contains forbidden header `Kundenavn`, email column `E-post`, and cell values containing Norwegian national identity numbers (`123456 78901`).
- **End-to-End Execution Flow**:
  1. Ingestion layer executes `assert_aggregated_csv`.
  2. Detects forbidden column `kundenavn` and raises `DataPolicyError("Person- eller fritekstfelt er ikke tillatt: kundenavn, e_post")`.
  3. Pipeline immediately executes `_finish_blocked`.
  4. Staging directory purged; no customer-facing drafts (`brief.md`, `brief.html`, `email.txt`) are created.
  5. `runs/<run_id>` contains only `errors.json`, `events.json`, and `manifest.json` with `status: blocked` and `pii_scan_status: not_publishable`.
- **Verifications**: Exit code 2; zero PII leakage; audit manifest records blocked status and stop reason.

---

## 4. Caveats

1. **Network Isolation in Automated Testing**:
   - In CI/CD and offline development environments, live HTTP calls to MET.no, Google Places, and external websites must be disabled by default. Tests must use `FixtureFetcher`, `FixtureRoles`, `FixtureGooglePlacesAdapter`, and `FixtureGoogleTrendsAdapter` or mocked `httpx.Client`.
2. **MET.no Terms of Service Compliance**:
   - Live calls to MET.no must always carry a valid identifying `User-Agent` with contact information. Unit tests must assert this header is present in every outgoing request.
3. **GDPR Aggregation Boundary**:
   - The engine must strictly reject individual customer reservation records or free-text notes. Even in test fixtures, mock data must represent aggregated counts and totals, never individual customer names.
4. **Read-Only Investigation Protocol**:
   - This document is an investigative test design report. No production codebase files have been modified.

---

## 5. Conclusion

1. **R3 (External Signals)** is fully specified with clear models, caching tiers, and test suites covering MET.no weather forecasts, Agder school holiday calendar (skolerute), Kristiansand city event clash radar, Google Places GBP sentiment topics, Google Trends Agder search interest, and Schema.org JSON-LD event scrapers.
2. **R4 (Automated Brief Rendering & Security Audit)** is fully specified with exhaustive test suites covering capacity utilization, dark weekday gap analysis, max-3 prioritized recommendations, Markdown/HTML/Email rendering with mandatory human-in-the-loop disclaimers, pre-flight PII scanning, SHA-256 cryptographic audit manifests, atomic staging persistence, RepoPaths traversal confinement, SourcePolicy SSRF guards, and CLI execution modes.
3. **Tier 4 Real-World Workload Scenarios** provide 6 complete, realistic end-to-end user workflows spanning high-season sellouts, dark weekday gap activation, school holiday matinee surges, city clash storms, source network outages, and adversarial PII injection defenses.
4. The test specifications satisfy all requirements of `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `TEST_INFRA.md`, providing a direct blueprint for the E2E test implementation track.

---

## 6. Verification Method

To independently verify the test design and execute the test suites:

### 6.1 Automated Test Execution
Run the full test suite from the repository root:
```bash
python -m pytest tests/
```
*Expected Result*: 100% of unit, integration, and E2E tests pass with zero failures.

### 6.2 Syntax and Compilation Verification
Verify zero syntax or bytecode compilation errors across the entire codebase:
```bash
python -m compileall teateret_brief tests
```
*Expected Result*: Clean compile with exit code 0.

### 6.3 Deterministic Demo Execution
Execute the CLI in demo mode with all external signal flags:
```bash
python -m teateret_brief.cli --mode demo --sales sample_data/gastroplanner_sample_2026.csv --google-places --google-trends --schema-events
```
*Expected Result*: Returns `STATUS: COMPLETED`, creates `runs/<run_id>/` with `brief.md`, `brief.html`, `email.txt`, `manifest.json`, and `events.json`.

### 6.4 Key Artifacts for Inspection
- `teateret_brief/pipeline.py`: Pipeline coordinator, staging isolation, manifest generation.
- `teateret_brief/render.py`: Multi-format rendering engine with mandatory disclaimers.
- `teateret_brief/security.py`: `RepoPaths`, `SourcePolicy`, `assert_aggregated_csv`, `scan_public_artifact`.
- `teateret_brief/google_places.py`: Google Places adapter with reviewer redaction and review limits.
- `teateret_brief/google_trends.py`: Google Trends Agder adapter.
- `teateret_brief/schema_events.py`: Schema.org JSON-LD extractor.
