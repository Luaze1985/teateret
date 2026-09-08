# Scope: Milestone 3 — External Context Enrichment & Signals (R3)

## Architecture
Milestone 3 implements the external context and signals layer for Teateret Weekly Decision Brief Engine:
- `teateret_brief/fetcher.py`: 3-Tier Safe Fetcher (Tier 1: Live HTTPS with timeout/domain allowlist/SSRF guard, Tier 2: Disk TTL cache, Tier 3: Deterministic static fixtures).
- `teateret_brief/weather_and_calendar.py`:
  - MET.no weather adapter (location: Kristiansand lat 58.1467, lon 7.9956, proper User-Agent header, demand heuristic scoring).
  - Agder school holiday calendar adapter (Vinterferie Uke 8, Påskeferie, Sommerferie Uke 26-33, Høstferie Uke 40, Juleferie; family/matinee vs corporate demand tags).
  - Kristiansand City Event Clash Radar (major venues: Kilden, Q42, Palmesus, Ravnedalen Live, Dark Season; clash severity and distance/demographic scoring).
- `teateret_brief/google_places.py`: Google Places GBP sentiment adapter (ratings, review count, topic keywords, strict reviewer name redactor replacing names with `[ANMELDER]`).
- `teateret_brief/google_trends.py`: Google Trends Agder adapter (`geo='NO-42'`, interest over time for keywords like "restaurant Kristiansand", "teater Kristiansand", "konsert Kristiansand").
- `teateret_brief/schema_events.py`: Schema.org JSON-LD event scraper / parser extracting structured Event objects with startDate, endDate, location, offers/availability.
- Static fixtures in `sample_data/fixtures/` for zero-network deterministic operation and testing.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 10 | MET.no Weather Signal Adapter | Weather forecast integration (Kristiansand 58.1467, 7.9956) with custom User-Agent and caching | M3 | survey_explorer_1 |
| 11 | Agder School Holiday Signal Adapter | Holiday calendar (Uke 8, Påske, Sommer, Uke 40, Jul) for family matinee vs corporate demand | M3 | survey_explorer_1 |
| 12 | Kristiansand City Event Clash Adapter | Clash radar for Kilden, Q42, Palmesus, festivals with distance and demographic overlap | M3 | survey_explorer_1 |
| 13 | External Signal 3-Tier Cache & Fallback | Live Safe HTTP -> Disk TTL Cache -> Deterministic Static Fixtures | M3 | survey_explorer_1 |
| 14 | Google Places Sentiment Adapter | GBP ratings, review count, and sentiment topic extraction with reviewer redaction `[ANMELDER]` | M3 | survey_miner_1 |
| 15 | Google Trends Agder Adapter | Regional Agder (`NO-42`) search interest trends for entertainment/dining keywords | M3 | survey_miner_1 |
| 16 | Schema.org Event Scraper | JSON-LD event scraper extracting structured calendar events with ticket availability | M3 | survey_miner_1 |

## Interface Contracts
### External Signals Models & Aggregator
- `WeatherForecastSignal`: `period: date`, `symbol_code: str`, `temperature_c: float`, `precipitation_mm: float`, `wind_speed_mps: float`, `demand_impact: str`, `confidence: float`
- `SchoolHolidaySignal`: `period: date`, `is_holiday: bool`, `holiday_name: str | None`, `week_number: int | None`, `family_demand_multiplier: float`, `corporate_demand_multiplier: float`
- `CityEventClashSignal`: `period: date`, `venue_name: str`, `event_name: str`, `distance_km: float`, `expected_attendance: int`, `clash_severity: Literal["low", "medium", "high", "critical"]`, `demographic_overlap: str`
- `GooglePlacesSignal`: `rating: float`, `total_reviews: int`, `recent_sentiment_topics: list[str]`, `sample_reviews: list[str]` (all names redacted to `[ANMELDER]`)
- `GoogleTrendsSignal`: `geo: str` ("NO-42"), `keyword: str`, `relative_interest: int`, `trend_direction: Literal["up", "down", "stable"]`
- `SchemaEventItem`: `title: str`, `start_date: datetime`, `end_date: datetime | None`, `venue_name: str`, `ticket_status: Literal["InStock", "SoldOut", "PreOrder", "Unknown"]`
- `ExternalContextEnrichment`: `period: date`, `weather: WeatherForecastSignal | None`, `school_holiday: SchoolHolidaySignal | None`, `city_clashes: list[CityEventClashSignal]`, `places_sentiment: GooglePlacesSignal | None`, `trends: list[GoogleTrendsSignal]`, `scraped_events: list[SchemaEventItem]`
- `fetch_external_context(target_date: date, mode: Literal["live", "cache", "fixture"] = "fixture", fixture_dir: Path | None = None) -> ExternalContextEnrichment`

## Code Layout Ownership for M3
- `teateret_brief/fetcher.py`
- `teateret_brief/weather_and_calendar.py`
- `teateret_brief/google_places.py`
- `teateret_brief/google_trends.py`
- `teateret_brief/schema_events.py`
- `sample_data/fixtures/` (met_no_sample.json, holidays_agder_2025_2026.json, city_events_kristiansand.json, google_places_sample.json, google_trends_sample.json, schema_events_sample.json)
- `tests/test_weather_and_calendar.py`
- `tests/test_fetcher.py`
- `tests/test_google_places.py`
- `tests/test_google_trends.py`
- `tests/test_schema_events.py`
