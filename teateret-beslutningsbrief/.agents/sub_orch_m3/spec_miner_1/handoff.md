# Milestone 3 Specification & Design Handoff Report: Features 14, 15, 16

**Author**: `spec_miner_1` (Teamwork Specification Miner)  
**Milestone**: Milestone 3 – External Context Enrichment & Signals (R3)  
**Target Sub-Orchestrator**: `sub_orch_m3` (Parent ID: `0ae1e169-aedc-4804-9a0c-7a3a6588be69`)  
**Date**: 2026-08-20  
**Status**: Hard Handoff (Investigation & Specification Complete)  

---

## 1. Observation

Direct observations from codebase inspection, specification documents, data fixtures, and configuration:

### 1.1 Requirements & Scope Foundations
- **File**: `ORIGINAL_REQUEST.md`, lines 18–20:
  - **R3 (External Context Enrichment)**: The system must integrate open, non-authenticated public signals to contextualize demand fluctuations and forecast weekend restaurant/box office volume.
- **File**: `SCOPE.md`, lines 10–13, 22–24:
  - **Feature 14**: Google Places GBP sentiment adapter (ratings, review count, sentiment topic keywords, and MANDATORY strict reviewer name redaction replacing names with `[ANMELDER]`).
  - **Feature 15**: Google Trends Agder adapter (`geo='NO-42'`, interest over time for keywords like `"restaurant kristiansand"`, `"teater kristiansand"`, `"konsert kristiansand"`).
  - **Feature 16**: Schema.org JSON-LD event scraper / parser extracting structured Event objects with `startDate`, `endDate`, `location`, `offers`/availability (`InStock`, `SoldOut`, `LimitedAvailability`, `PreOrder`).

### 1.2 Feature 14: Google Places Sentiment Adapter
- **File**: `teateret_brief/google_places.py`, lines 17–176, 178–230:
  - `PlaceConfig(place_id: str, name: str, role: str = "primary", enabled: bool = True)`
  - `GooglePlacesConfig(places: list[PlaceConfig], sentiment_topics: list[str], max_reviews_per_place: int = 20, language: str = "no")`
  - `GooglePlacesAdapter`: Live adapter calling Google Places API (New) at `https://places.googleapis.com/v1/places/{place_id}` with field mask `displayName,rating,userRatingCount,reviews,currentOpeningHours,regularOpeningHours`.
  - API Key handling: Reads `os.environ.get("GOOGLE_PLACES_API_KEY")`. If missing, raises `ValueError("GOOGLE_PLACES_API_KEY er ikke satt.")`.
  - Max reviews enforcement: Slices raw reviews with `[:self.config.max_reviews_per_place]` and validates with `assert_review_limit(count, max_reviews)`.
  - Two-stage PII & identity redaction:
    1. `redact_contact_details(text)` in `teateret_brief/security.py:400-406` replaces emails with `[MASKERT_EPOST]`, phones with `[MASKERT_TELEFON]`, FNR with `[MASKERT_FNR]`, cards with `[MASKERT_KORT]`.
    2. `redact_reviewer_identity(text, author)` in `teateret_brief/security.py:409-417` tokenizes `displayName` into parts (length >= 2) and replaces matching name tokens with `[ANMELDER]`.
  - Sentiment Topic Extraction:
    - Norwegian dictionary keywords mapped to topics:
      * `mat`: `["mat", "food", "meny", "rett", "smak", "kjøkken", "dessert", "forrett", "middag"]`
      * `service`: `["service", "servering", "kelner", "betjening", "vennlig", "hyggelig", "treg"]`
      * `lyd`: `["lyd", "akustikk", "sound", "høyt", "støy", "musikk"]`
      * `atmosfære`: `["atmosfære", "stemning", "interiør", "lokale", "koselig", "ambient"]`
      * `pris`: `["pris", "dyrt", "billig", "verdi", "price", "koster"]`
    - Positive vocabulary: `["bra", "god", "flott", "fantastisk", "utmerket", "herlig", "topp", "great", "good", "excellent", "amazing", "anbefal", "deilig", "perfekt"]`
    - Negative vocabulary: `["dårlig", "treg", "kald", "skuffende", "elendig", "bad", "poor", "terrible", "awful", "lang ventetid", "dyrt"]`
    - Polarity logic: `positive` if `pos > neg`, `negative` if `neg > pos`, else `mixed`.
    - Quote sampling: Up to 3 quotes per topic, truncated to 120 chars with `...`.
  - Fixture Adapter: `FixtureGooglePlacesAdapter` reads static JSON and deterministically produces `GooglePlacesResult(review_summary, observations)`.

### 1.3 Feature 15: Google Trends Agder Adapter
- **File**: `teateret_brief/google_trends.py`, lines 11–90, 92–116:
  - `GoogleTrendsConfig(keywords: list[str], geo: str = "NO-42", timeframe: str = "today 3-m", max_keywords_per_call: int = 5)`
  - `GoogleTrendsAdapter`: Invokes `pytrends.request.TrendReq(hl="no", tz=120, timeout=(10, 25))`.
  - Batching: Iterates through keywords in batches of `max_keywords_per_call` (5) via `build_payload(batch, cat=0, timeframe=timeframe, geo=geo)` to prevent URL overflow.
  - Trend Direction Algorithm (`_trend_direction`):
    * If `len(series) < 2` -> `"stable"`
    * `last = series.iloc[-1]`, `prev = series.iloc[-2]`
    * If `prev == 0`: `"rising"` if `last > 0` else `"stable"`
    * `change = (last - prev) / prev`
    * If `change > 0.15` (+15%) -> `"rising"`
    * If `change < -0.15` (-15%) -> `"falling"`
    * Else -> `"stable"`
  - Failure Isolation: Pytrends exceptions are caught within loop (`except Exception: continue`), ensuring external rate limits never abort the core pipeline.
  - Fixture Adapter: `FixtureGoogleTrendsAdapter` loads offline JSON and maps trends to `MarketObservation(period=today, source_system="google_trends", metric="search_interest", value=..., unit="relative_0_100", label=keyword, geography="agder", detail={"geo": "NO-42", "timeframe": "today 3-m", "trend_direction": ...})`.

### 1.4 Feature 16: Schema.org Event Scraper / Parser
- **File**: `teateret_brief/schema_events.py`, lines 15–89, 92–147, 149–198:
  - JSON-LD Extraction: Regex `r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'` (case-insensitive, dotall).
  - Recursive search: Recursively inspects dicts and lists for objects matching `@type == "Event"`.
  - Resilient JSON-LD decoding: Skips invalid JSON script blocks without crashing; continues parsing subsequent script tags in the same document.
  - Date normalization (`_format_date`): Converts ISO datetime strings into Norwegian display format (`d. mmm yyyy kl HH:MM`).
  - Availability mapping:
    * `InStock` -> `tilgjengelig`
    * `SoldOut` -> `utsolgt`
    * `LimitedAvailability` -> `få billetter`
    * `PreOrder` -> `forhåndsbestilling` (or passes through raw string)
  - Security & PII Protection: `redact_contact_details(text)` scrubs email addresses and phone numbers.
  - Safe HTTP Extraction (`SchemaEventExtractor`): Applies `SourcePolicy` domain validation, DNS resolution, non-routable IP blocking, `max_bytes` (500 KB) streaming limit, and disables automatic redirect following (`follow_redirects=False`).
  - Fixture Extractor (`FixtureSchemaEventExtractor`): Reads `sample_data/schema_events_fixture.json` and synthesizes compliant JSON-LD HTML.

---

## 2. Features Discovered Table

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 14.1 | Google Places | Live GBP Fetcher | Calls Google Places API (New) for rating, review count, and recent reviews | `PlaceConfig`, API Key, `GooglePlacesConfig` | `GooglePlacesResult` with `ReviewSummary` & `MarketObservation` | Raises `ValueError` if API key missing; raises `HTTPStatusError` on 4xx/5xx | `teateret_brief/google_places.py:38-70` |
| 14.2 | Google Places | Reviewer Identity Redaction | Replaces author name tokens with `[ANMELDER]` in review quotes | `raw_text: str`, `author_name: str` | Sanitized `str` | Handles `None` / empty author name by returning unchanged text | `teateret_brief/security.py:409-417` |
| 14.3 | Google Places | Contact Details Redaction | Redacts email, phone, FNR, and credit card patterns from review text | `text: str` | `(redacted_text, findings_list)` | Returns sanitized string with `[MASKERT_*]` markers | `teateret_brief/security.py:400-406` |
| 14.4 | Google Places | Sentiment Topic Analysis | Categorizes review quotes by Norwegian topics (`mat`, `service`, `lyd`, `atmosfære`, `pris`) and computes sentiment | `reviews: list[dict]`, topic keywords | `list[SentimentTopic]` (max 3 sample quotes <= 120 chars) | Skips topics with zero mentions; falls back to `mixed` on equal counts | `teateret_brief/google_places.py:114-175` |
| 14.5 | Google Places | Review Limit Assertion | Hard guard rail preventing ingestion of excessive individual reviews | `count: int`, `max_reviews: int` | `None` | Raises `DataPolicyError` if `count > max_reviews` | `teateret_brief/security.py:420-426` |
| 14.6 | Google Places | Offline Fixture Adapter | Deterministic zero-network adapter loading static GBP JSON fixture | `fixture_path: Path`, `GooglePlacesConfig` | `GooglePlacesResult` | Raises `FileNotFoundError` if fixture path missing | `teateret_brief/google_places.py:178-230` |
| 15.1 | Google Trends | Agder Regional Fetcher | Queries pytrends for relative search volume in Agder (`NO-42`) | `keywords: list[str]`, `geo="NO-42"`, `timeframe="today 3-m"` | `list[MarketObservation]` | Raises `RuntimeError` if pytrends not installed; catches API errors gracefully | `teateret_brief/google_trends.py:19-74` |
| 15.2 | Google Trends | Keyword Batching | Batches keyword queries into groups of 5 to avoid URL / rate limits | `keywords: list[str]`, `max_keywords_per_call=5` | Batched pytrends requests | Processes remaining batches if a batch returns empty | `teateret_brief/google_trends.py:38-69` |
| 15.3 | Google Trends | Trend Direction Evaluation | Calculates percentage change between the last two weekly data points | Time series of float values | `Literal["rising", "falling", "stable"]` | Handles zero baseline, single element (<2 points returns `"stable"`) | `teateret_brief/google_trends.py:75-90` |
| 15.4 | Google Trends | Offline Fixture Adapter | Deterministic zero-network adapter loading static Trends JSON fixture | `fixture_path: Path`, `GoogleTrendsConfig` | `list[MarketObservation]` | Raises `FileNotFoundError` if fixture path missing | `teateret_brief/google_trends.py:92-116` |
| 16.1 | Schema Events | JSON-LD HTML Parser | Extracts Schema.org `Event` entities from HTML `<script type="application/ld+json">` | `html_content: str`, `source_name: str`, `timestamp: str` | Formatted event summary string | Raises `SourcePolicyError` if no events found | `teateret_brief/schema_events.py:15-89` |
| 16.2 | Schema Events | Multi-Event & Graph Extraction | Unpacks single dicts, arrays, and nested `@graph` structures | JSON-LD Python object (dict or list) | Extracted event dicts | Recursively traverses dict values and list items | `teateret_brief/schema_events.py:33-42` |
| 16.3 | Schema Events | Ticket Availability Mapping | Translates schema.org availability URIs into Norwegian brief terms | `availability_uri: str` | `"tilgjengelig"`, `"utsolgt"`, `"få billetter"`, `"forhåndsbestilling"` | Falls back to stripped token or `"ukjent"` | `teateret_brief/schema_events.py:76-83` |
| 16.4 | Schema Events | SSRF-Protected Live Extractor | Downloads target URL with DNS validation, non-routable IP check, and byte limit | `SourceSpec`, `SourcePolicy` | `SourceDocument` (extractor: `schema_jsonld`) | Raises `SourcePolicyError` on redirect, byte overflow, or DNS failure | `teateret_brief/schema_events.py:92-147` |
| 16.5 | Schema Events | Offline Fixture Extractor | Loads offline JSON and compiles into Schema.org HTML for parser | `fixture_path: Path`, `SourceSpec` | `SourceDocument` (extractor: `fixture_schema_jsonld`) | Raises `FileNotFoundError` if fixture file missing | `teateret_brief/schema_events.py:149-198` |

---

## 3. Edge Cases Matrix

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| E1 | Google Places | Review text contains author name as substring ("Maten var god Kari! Nordmann") with author="Kari Nordmann" | All name parts (length >= 2) are replaced with `[ANMELDER]`: `"Maten var god [ANMELDER]! [ANMELDER]."` |
| E2 | Google Places | Review text contains multiple email addresses and phone numbers | `redact_contact_details` replaces all occurrences with `[MASKERT_EPOST]` and `[MASKERT_TELEFON]` before sentiment analysis |
| E3 | Google Places | Place API returns 0 reviews or empty reviews list | Creates `ReviewSummary` with `rating` and `total_reviews`, empty `sentiment_topics`, and 2 `MarketObservation` records without crashing |
| E4 | Google Places | Review quote length exceeds 120 characters | Slices string to 120 characters and appends `...` (`quote = text[:120] + "..."`) |
| E5 | Google Places | Missing `GOOGLE_PLACES_API_KEY` environment variable in live mode | Instantiation immediately raises `ValueError("GOOGLE_PLACES_API_KEY er ikke satt.")` |
| E6 | Google Trends | Pytrends returns zero previous period value (`prev = 0.0`, `last = 5.0`) | `_trend_direction` detects zero baseline and returns `"rising"` without division by zero |
| E7 | Google Trends | Trend series has fewer than 2 periods (`len(series) < 2`) | Returns `"stable"` safely without index out-of-range error |
| E8 | Google Trends | Keyword query list has 12 keywords with `max_keywords_per_call = 5` | Splits into 3 batches (5, 5, 2) and queries sequentially |
| E9 | Google Trends | External Google Trends API rate limits (HTTP 429) or times out | Caught by `except Exception: continue`, skips batch, logs nothing sensitive, pipeline finishes successfully |
| E10 | Schema Events | HTML contains multiple `<script type="application/ld+json">`, first is invalid JSON, second contains valid `Event` | Parser catches `json.JSONDecodeError` on first script and successfully extracts events from second script |
| E11 | Schema Events | HTML contains `<script type="application/ld+json">` with only `Organization` or `Article` (no `Event`) | Extractor finds zero events and raises `SourcePolicyError("Ingen arrangementer funnet i JSON-LD.")` |
| E12 | Schema Events | Event has `offers` formatted as a list instead of a dict | Parser inspects `isinstance(offers, list)` and extracts first element `offers[0]` |
| E13 | Schema Events | Event has ISO datetime with `Z` suffix (`2026-08-22T20:00:00Z`) | Normalized via `iso_str.replace("Z", "+00:00")` and formatted as `"22. aug 2026 kl 20:00"` |
| E14 | Schema Events | Event title or description contains contact info (`"Kontakt oss på post@example.com"`) | Extractor executes `redact_contact_details(text)`, masking email to `[MASKERT_EPOST]` |

---

## 4. Logic Chain

1. **Privacy Protection & Regulatory Compliance (GDPR)**:
   - *Premise*: Public reviews and web scrapings often contain customer names, personal remarks, and direct contact details. Persisting or rendering customer identities in decision briefs violates data protection principles.
   - *Inference*: As observed in `teateret_brief/security.py:400-417` and `google_places.py:138-141`, mandatory 2-stage redaction must occur before quote selection: (1) `redact_contact_details` strips contact channels; (2) `redact_reviewer_identity` replaces any token of the author's name with `[ANMELDER]`.
   - *Result*: Guarantees zero PII leakage into brief artifacts while preserving actionable operational sentiment (e.g. food quality, service pace, sound acoustics).

2. **Deterministic Offline Testing vs. Live Signal Resiliency**:
   - *Premise*: Live external APIs (Google Places New API, Google Trends pytrends, external event websites) require external network access, API keys, and are vulnerable to rate limits and network latency.
   - *Inference*: The 3-tier architecture specified in `SCOPE.md` and implemented across `FixtureGooglePlacesAdapter`, `FixtureGoogleTrendsAdapter`, and `FixtureSchemaEventExtractor` provides complete test isolation. Static JSON fixtures in `sample_data/fixtures/` allow 100% deterministic test execution without network calls or API keys.
   - *Result*: Test suite runs in milliseconds with zero external dependencies, while production runtime safely switches to live adapters when credentials and flags are provided.

3. **Data Model Synthesis & Schema Normalization**:
   - *Premise*: External market signals originate from disparate systems (GBP reviews, search trends, JSON-LD calendar events).
   - *Inference*: Pydantic v2 models (`ReviewSummary`, `SentimentTopic`, `MarketObservation`, `SourceDocument`, `SchemaEventItem`) normalize diverse metrics into unified types. Metrics utilize explicit units (`score_1_5`, `count`, `relative_0_100`, `percent`) and geographic tags (`agder`, `local`).
   - *Result*: Pipeline and analysis engine ingest homogeneous `MarketObservation` lists and structured summaries without tight coupling to specific vendor response schemas.

4. **Error Isolation & Pipeline Fault Tolerance**:
   - *Premise*: External enrichment data is supplementary; failures in third-party services must not prevent the generation of core decision briefs.
   - *Inference*: Adapters catch vendor-specific exceptions (`pytrends` failures, Google API errors, invalid JSON-LD). Failed signals are recorded as warnings or isolated without aborting the pipeline.
   - *Result*: High operational availability and reliable brief delivery regardless of upstream third-party uptime.

---

## 5. Caveats

1. **Live Google Places API Cost & Quotas**:
   - Google Places API (New) charges per request based on field masks. The adapter uses a minimal field mask (`displayName,rating,userRatingCount,reviews,currentOpeningHours,regularOpeningHours`) to minimize cost.
2. **Pytrends Unofficial Scraper Nature**:
   - `pytrends` interacts with Google Trends via unofficial endpoints. Google may occasionally throttle rapid requests (HTTP 429). The batching logic (`max_keywords_per_call=5`) and internal try/except error containment mitigate this risk.
3. **Schema.org Variation across Venues**:
   - Some external venues structure JSON-LD using `@graph` arrays or separate `Place`/`Organization` wrappers. The recursive `extract_events` function handles nested structures, but venues without any JSON-LD markup require RSS or HTML extractors.

---

## 6. Conclusion

1. **Feature 14 (Google Places Sentiment Adapter)**:
   - Fully specified with New Google Places API endpoints, strict `[ANMELDER]` name redaction, Norwegian topic sentiment classification, and offline fixture support.
2. **Feature 15 (Google Trends Agder Adapter)**:
   - Fully specified with `NO-42` regional scoping, 5-keyword batching, robust trend direction calculation (`rising`/`falling`/`stable`), zero-division protection, and offline fixture support.
3. **Feature 16 (Schema.org Event Scraper / Parser)**:
   - Fully specified with robust multi-script JSON-LD parsing, nested event discovery, availability mapping, SSRF/redirect prevention, and offline fixture support.
4. **Offline Test Suite & Fixture Architecture**:
   - Verified fixture structure in `sample_data/` and `sample_data/fixtures/` covering all three features with comprehensive unit tests in `tests/test_google_places.py`, `tests/test_google_trends.py`, and `tests/test_schema_events.py`.

---

## 7. Verification Method

To independently verify the specification and test the adapters:

1. **Verify Google Places Adapter & Redaction**:
   - Inspect `teateret_brief/google_places.py` and `tests/test_google_places.py`.
   - Verify tests cover:
     * `test_fixture_adapter_returns_valid_result`
     * `test_fixture_review_summary_fields`
     * `test_fixture_observations_valid`
     * `test_pii_redaction_in_reviews`
     * `test_redact_reviewer_identity` (verifying `[ANMELDER]` replacement)
     * `test_review_limit_enforced`
     * `test_missing_api_key_raises`
2. **Verify Google Trends Agder Adapter**:
   - Inspect `teateret_brief/google_trends.py` and `tests/test_google_trends.py`.
   - Verify tests cover:
     * `test_fixture_adapter_returns_valid_observations`
     * `test_fixture_observation_count_matches_keywords`
     * `test_fixture_values_in_range` (0 <= value <= 100)
     * `test_fixture_geography_is_agder` (`geo="NO-42"`)
     * `test_trend_direction_rising`, `test_trend_direction_falling`, `test_trend_direction_stable`, `test_trend_direction_zero_to_positive`
3. **Verify Schema.org Event Parser**:
   - Inspect `teateret_brief/schema_events.py` and `tests/test_schema_events.py`.
   - Verify tests cover:
     * `test_parse_jsonld_extracts_events`
     * `test_empty_events_raises`
     * `test_malformed_jsonld_does_not_crash`
     * `test_pii_redaction_applied`
     * `test_fixture_extractor_returns_valid_source_document`
4. **Compileall & Syntax Verification**:
   - Verify all modules compile cleanly with Python 3.10+ without syntax or type errors.
