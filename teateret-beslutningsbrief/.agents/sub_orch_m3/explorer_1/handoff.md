# Handoff Report: Milestone 3 — Feature 10 (MET.no Weather Signal Adapter) & Feature 13 (External Signal 3-Tier Cache & Fallback Architecture)

**Agent:** explorer_1 (Milestone 3)  
**Date:** 2026-08-20  
**Parent:** 0ae1e169-aedc-4804-9a0c-7a3a6588be69  
**Status:** Hard Handoff (Investigation & Specification Complete)

---

## 1. Observation

### 1.1 Existing Codebase & Infrastructure
1. **Security & SSRF Guard (`teateret_brief/security.py`, lines 65–98):**
   - `SourcePolicy` validates all outgoing HTTP requests:
     - Scheme must be strictly `"https"` (lines 77–78).
     - Standard HTTPS port 443 only (lines 81–86).
     - Host must match `allowed_hosts` set (lines 87–88).
     - Resolver verifies IP address is globally routable (`ipaddress.ip_address(address).is_global`), blocking loopback (127.0.0.1), RFC1918 private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), and link-local addresses (lines 92–97).
2. **PII and Data Scrubbing (`teateret_brief/security.py`, lines 387–417):**
   - `scan_public_artifact`, `redact_contact_details`, and `redact_reviewer_identity` strip emails, phone numbers, FNR, and credit cards from external payloads.
3. **Current Fetcher Layer (`teateret_brief/fetcher.py`, lines 105–196):**
   - `SafeHttpFetcher`: basic HTML/RSS fetching using `httpx.Client` with `timeout=15.0`, `max_bytes=500_000`, and `SourcePolicy` validation.
   - `FixtureFetcher`: maps `source_id` to local files defined in configuration.
   - **Gap Identified:** There is currently no unified, reusable 3-Tier Cache & Fallback architecture supporting automatic disk TTL caching, header-based expiry, stale-on-error fallback, and deterministic static fixture fallbacks for structured JSON APIs (like MET.no).
4. **Current Models (`teateret_brief/models.py`, lines 54–88):**
   - `MarketSourceSystem` currently defined as `Literal["google_places", "google_trends", "schema_events"]` (line 54).
   - `MarketObservation` supports numerical metrics with `period: date`, `metric: str`, `value: float`, `unit: str`, `label: str`, `detail: dict | None`.
   - **Gap Identified:** Missing explicit models for `WeatherForecastSignal` and unified container `ExternalContextEnrichment`.
5. **Fixtures Directory (`sample_data/`):**
   - Contains `google_places_fixture.json`, `google_trends_fixture.json`, `schema_events_fixture.json`.
   - **Gap Identified:** Missing `met_no_sample.json` and a standardized `sample_data/fixtures/` structure for external signal fallback.

---

## 2. Logic Chain

1. **Compliance with MET.no Terms of Service & Open Data Policy:**
   - MET.no Locationforecast 2.0 API requires a custom `User-Agent` header containing application identification and contact information (`TeateretDecisionBrief/1.0 (kontakt@teateret.no)`).
   - Location coordinates for Kristiansand: Latitude `58.1467`, Longitude `7.9956`.
   - API endpoint: `https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=58.1467&lon=7.9956`.
   - MET.no specifies caching requirements: clients must respect `Expires` / `Cache-Control` headers (forecasts update roughly once per hour; repeated uncached calls violate ToS).

2. **Why a 3-Tier Fallback Architecture is Necessary (Feature 13):**
   - **Tier 1 (Live Safe HTTPS):** Fetches real-time open public signals when network and DNS are operational, protected by `SourcePolicy` SSRF/allowlist rules and strict timeouts.
   - **Tier 2 (Disk TTL Cache):** Eliminates unnecessary external calls, satisfies API rate limits/ToS, and enables resilient operation during transient network drops or slow internet. It uses atomic disk writing (`.tmp` + rename) and TTL evaluation (default 1h for weather). If live fetch fails, expired cache can serve as a stale fallback.
   - **Tier 3 (Deterministic Static Fixtures):** Guarantees zero-network offline execution, air-gapped demo runs, and 100% deterministic, repeatable CI/CD unit and integration testing via `sample_data/fixtures/met_no_sample.json`.

3. **Demand Heuristics Formulation (Feature 10):**
   - Teateret operations encompass indoor stages (Hovedscenen: 380–400 cap, Biscenen: 100–150 cap, Intimscenen: 60 cap), an indoor restaurant/bistro/bar, and an outdoor terrace/Foajeen.
   - *Heuristic 1 (Rain / High Precipitation):* Precipitation $\ge 2.0\text{ mm}$ or rain symbol codes (`rain`, `heavyrain`, `rainshowers`, `sleet`, `snow`) $\rightarrow$ drives patrons indoors, boosting box office ticket sales and indoor bistro/café dining.
   - *Heuristic 2 (Cold / Low Temperature):* Temperature $< 10.0^\circ\text{C}$ (or $< 5.0^\circ\text{C}$) $\rightarrow$ stimulates indoor seating, hot food/beverage sales, and indoor stage events.
   - *Heuristic 3 (Sunny & Warm Summer):* Temperature $\ge 20.0^\circ\text{C}$ with clear/fair skies during summer $\rightarrow$ strong surge in outdoor terrace and Foajeen bar revenue, but may suppress early afternoon indoor theater attendance before 20:00.
   - *Heuristic 4 (Moderate / Neutral):* Stable conditions with mild temperature ($10\text{--}19^\circ\text{C}$) and dry weather $\rightarrow$ standard baseline demand.

---

## 3. Caveats & Edge Cases

1. **MET.no API Forecast Time Horizon & Granularity:**
   - Compact endpoint provides 1-hour resolution for 0–48 hours, and 6-hour resolution for 48 hours to 10 days.
   - For decision briefs targeting specific weekend dates or 7-day outlooks, the adapter must extract and aggregate forecasts for the evening dining/show window (16:00–22:00 local time) or full-day representative values.
2. **Timezone Offset (UTC vs CET/CEST):**
   - MET.no timeseries entries use UTC ISO-8601 strings (`Z`). In Kristiansand (Europe/Oslo), offset is UTC+1 (winter CET) or UTC+2 (summer CEST). Aggregation must group timeseries into local calendar dates.
3. **SSRF Allowlist Management:**
   - `api.met.no` must be included in `SourcePolicy.allowed_hosts`. In live mode, DNS resolution must verify the IP address is public.
4. **Cache Directory Permissions:**
   - Disk TTL cache directory (e.g. `.cache/external_signals/`) must be auto-created. If write permission fails, it must gracefully degrade to in-memory/fixture fallback without crashing the pipeline.

---

## 4. Conclusion & Detailed Technical Specifications

### 4.1 Data Models (`teateret_brief/models.py`)

Extend `MarketSourceSystem` and add external signal Pydantic models:

```python
# In teateret_brief/models.py:

MarketSourceSystem = Literal[
    "google_places",
    "google_trends",
    "schema_events",
    "met_no",
    "school_holidays",
    "city_clashes",
]

class WeatherForecastSignal(BaseModel):
    """Værvarsel og etterspørselsheuristikk fra MET.no for Kristiansand."""
    period: date
    symbol_code: str = Field(min_length=1, description="MET.no værsymbol, f.eks. 'rain', 'clearsky_day'")
    temperature_c: float = Field(description="Gjennomsnitts- eller representativ temperatur i Celsius")
    precipitation_mm: float = Field(ge=0.0, description="Forventet nedbørsmengde i mm")
    wind_speed_mps: float = Field(ge=0.0, description="Vindhastighet i m/s")
    demand_impact: str = Field(min_length=1, description="Menneskelig/maskinell tolkning av etterspørselseffekt")
    impact_category: Literal["boost_indoor", "boost_outdoor", "neutral", "dampen_early"] = "neutral"
    confidence: float = Field(ge=0.0, le=1.0, default=0.85)
    source_tier: Literal["live", "cache", "fixture"] = "fixture"


class ExternalContextEnrichment(BaseModel):
    """Samlet ekstern kontekst for beslutningsgrunnlag (Milestone 3)."""
    period: date
    weather: WeatherForecastSignal | None = None
    school_holiday: Any | None = None          # SchoolHolidaySignal
    city_clashes: list[Any] = Field(default_factory=list)  # list[CityEventClashSignal]
    places_sentiment: ReviewSummary | None = None
    trends: list[MarketObservation] = Field(default_factory=list)
    scraped_events: list[SourceDocument] = Field(default_factory=list)
```

---

### 4.2 Feature 13: 3-Tier Cache & Fallback Architecture (`teateret_brief/fetcher.py`)

#### Design & Class Structure

```python
# Proposed Architecture for TieredSignalFetcher & DiskCacheStore

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal
import httpx

from .security import SourcePolicy, SourcePolicyError


@dataclass(frozen=True)
class CacheEntry:
    key: str
    url: str
    cached_at: float
    ttl_seconds: float
    payload: dict[str, Any]

    @property
    def is_fresh(self) -> bool:
        return (time.time() - self.cached_at) < self.ttl_seconds


class DiskCacheStore:
    """Tier 2: Disk TTL cache med atomisk skriving og feiltoleranse."""

    def __init__(self, cache_dir: Path, default_ttl_seconds: float = 3600.0):
        self.cache_dir = cache_dir
        self.default_ttl_seconds = default_ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        sanitized = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        prefix = "".join(c for c in key if c.isalnum() or c in ("-", "_"))[:24]
        return self.cache_dir / f"{prefix}_{sanitized}.json"

    def get(self, key: str, *, allow_stale: bool = False) -> tuple[dict[str, Any] | None, bool]:
        """Returnerer (payload, is_stale). Dersom ingen gyldig cache finnes, returneres (None, False)."""
        path = self._get_path(key)
        if not path.exists():
            return None, False
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            entry = CacheEntry(
                key=raw["key"],
                url=raw["url"],
                cached_at=raw["cached_at"],
                ttl_seconds=raw["ttl_seconds"],
                payload=raw["payload"],
            )
            if entry.is_fresh:
                return entry.payload, False
            if allow_stale:
                return entry.payload, True
            return None, False
        except Exception:
            return None, False

    def put(self, key: str, url: str, payload: dict[str, Any], ttl_seconds: float | None = None) -> None:
        path = self._get_path(key)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        entry_data = {
            "key": key,
            "url": url,
            "cached_at": time.time(),
            "ttl_seconds": ttl,
            "payload": payload,
        }
        tmp_path = path.with_suffix(".tmp")
        try:
            tmp_path.write_text(json.dumps(entry_data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp_path, path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)


class TieredSignalFetcher:
    """3-Tier Fetcher Engine:
    - Tier 1: Live Safe HTTPS (med SSRF guard, timeout, ToS User-Agent)
    - Tier 2: Disk TTL Cache (med stale fallback)
    - Tier 3: Deterministic Static Fixture
    """

    def __init__(
        self,
        policy: SourcePolicy,
        cache_store: DiskCacheStore | None = None,
        *,
        client: httpx.Client | None = None,
        timeout_seconds: float = 10.0,
        user_agent: str = "TeateretDecisionBrief/1.0 (kontakt@teateret.no)",
    ):
        self.policy = policy
        self.cache_store = cache_store
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": self.user_agent},
        )

    def fetch_json(
        self,
        url: str,
        *,
        mode: Literal["live", "cache", "fixture"] = "fixture",
        fixture_path: Path | None = None,
        cache_key: str | None = None,
        ttl_seconds: float = 3600.0,
    ) -> tuple[dict[str, Any], Literal["live", "cache", "fixture"]]:
        key = cache_key or url

        # Tier 3: Hvis mode=='fixture', last direkte fra statisk fil
        if mode == "fixture":
            if not fixture_path or not fixture_path.exists():
                raise FileNotFoundError(f"Fixture-fil finnes ikke: {fixture_path}")
            data = json.loads(fixture_path.read_text(encoding="utf-8"))
            return data, "fixture"

        # Tier 2: Sjekk Disk Cache først (om mode=='cache' eller 'live')
        if self.cache_store:
            cached_data, is_stale = self.cache_store.get(key, allow_stale=(mode == "cache"))
            if cached_data is not None and not is_stale:
                return cached_data, "cache"

        # Tier 1: Live Safe HTTPS Fetch
        if mode == "live":
            try:
                approved = self.policy.validate(url)
                response = self.client.get(
                    approved.url,
                    headers={"User-Agent": self.user_agent},
                )
                response.raise_for_status()
                data = response.json()

                # Skriv til Tier 2 Disk Cache
                if self.cache_store:
                    self.cache_store.put(key, url, data, ttl_seconds=ttl_seconds)

                return data, "live"
            except Exception as exc:
                # Fallback: Dersom Tier 1 feiler, prøv Tier 2 (stale cache)
                if self.cache_store:
                    stale_data, _ = self.cache_store.get(key, allow_stale=True)
                    if stale_data is not None:
                        return stale_data, "cache"

        # Siste fallback til Tier 3 (Fixture) dersom tilgjengelig
        if fixture_path and fixture_path.exists():
            data = json.loads(fixture_path.read_text(encoding="utf-8"))
            return data, "fixture"

        raise RuntimeError(f"Kunne ikke hente data for {url} (Tier 1, 2 og 3 feilet).")
```

---

### 4.3 Feature 10: MET.no Weather Signal Adapter (`teateret_brief/weather_and_calendar.py`)

#### Implementation Details & Demand Heuristic Algorithm

```python
# In teateret_brief/weather_and_calendar.py

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal
import httpx

from .fetcher import DiskCacheStore, TieredSignalFetcher
from .models import MarketObservation, WeatherForecastSignal
from .security import SourcePolicy


@dataclass(frozen=True)
class MetNoConfig:
    lat: float = 58.1467
    lon: float = 7.9956
    altitude_m: int = 10
    user_agent: str = "TeateretDecisionBrief/1.0 (kontakt@teateret.no)"
    endpoint: str = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
    cache_ttl_seconds: float = 3600.0


def evaluate_weather_demand_impact(
    target_date: date,
    temp_c: float,
    precip_mm: float,
    wind_mps: float,
    symbol_code: str,
) -> tuple[str, Literal["boost_indoor", "boost_outdoor", "neutral", "dampen_early"]]:
    """Heuristisk vurdering av værforholdenes innvirkning på Teaterets scene- og restaurantetterspørsel."""
    is_summer = target_date.month in (6, 7, 8)
    rain_symbols = {
        "rain", "heavyrain", "lightrain", "rainshowers", "heavyrainshowers_day",
        "heavyrainshowers_night", "sleet", "snow", "sleetshowers_day", "snowshowers_day"
    }
    sunny_symbols = {"clearsky_day", "fair_day", "partlycloudy_day"}

    # Heuristikk 1: Regn og kraftig nedbør
    if precip_mm >= 2.0 or any(s in symbol_code for s in ("rain", "sleet", "snow")):
        return (
            f"Nedbør ({precip_mm:.1f} mm, '{symbol_code}') driver gjester innendørs. "
            f"Øker etterspørsel etter teatersalene (Hovedscenen, Biscenen) og bordbestillinger i kafé/bistro.",
            "boost_indoor",
        )

    # Heuristikk 2: Kaldt og guffent vær (< 10°C eller sterk vind)
    if temp_c < 10.0 or (temp_c < 14.0 and wind_mps >= 8.0):
        return (
            f"Kjølig vær ({temp_c:.1f}°C, vind {wind_mps:.1f} m/s) stimulerer innendørs kulturkvelder "
            f"og servering av varme måltider og drikke.",
            "boost_indoor",
        )

    # Heuristikk 3: Sol og sommervarme (>= 20°C og sommermåned)
    if is_summer and temp_c >= 20.0 and symbol_code in sunny_symbols:
        return (
            f"Sol og varmt sommervær ({temp_c:.1f}°C, '{symbol_code}') gir sterkt trykk på "
            f"uteservering, terrasse og Foajeen, men kan dempe tidlig billettsalg til mørke teatersaler før kl 20:00.",
            "boost_outdoor",
        )

    # Heuristikk 4: Nøytralt / Moderate forhold
    return (
        f"Milde og stabile værforhold ({temp_c:.1f}°C, {precip_mm:.1f} mm nedbør). Nøytral etterspørselseffekt.",
        "neutral",
    )


class MetNoWeatherAdapter:
    """Live/Tiered adapter for MET.no Locationforecast 2.0."""

    def __init__(
        self,
        config: MetNoConfig = MetNoConfig(),
        cache_dir: Path | None = None,
        *,
        client: httpx.Client | None = None,
        policy: SourcePolicy | None = None,
    ):
        self.config = config
        self.policy = policy or SourcePolicy(
            allowed_hosts={"api.met.no"},
        )
        self.cache_store = DiskCacheStore(cache_dir, default_ttl_seconds=config.cache_ttl_seconds) if cache_dir else None
        self.fetcher = TieredSignalFetcher(
            policy=self.policy,
            cache_store=self.cache_store,
            client=client,
            user_agent=self.config.user_agent,
        )

    def fetch_forecast(
        self,
        target_date: date,
        *,
        mode: Literal["live", "cache", "fixture"] = "fixture",
        fixture_path: Path | None = None,
    ) -> tuple[WeatherForecastSignal, list[MarketObservation]]:
        url = f"{self.config.endpoint}?lat={self.config.lat}&lon={self.config.lon}"
        cache_key = f"met_no_{self.config.lat}_{self.config.lon}"

        data, tier_used = self.fetcher.fetch_json(
            url,
            mode=mode,
            fixture_path=fixture_path,
            cache_key=cache_key,
            ttl_seconds=self.config.cache_ttl_seconds,
        )

        return self._parse_forecast_data(data, target_date, tier_used)

    def _parse_forecast_data(
        self,
        data: dict[str, Any],
        target_date: date,
        tier_used: Literal["live", "cache", "fixture"],
    ) -> tuple[WeatherForecastSignal, list[MarketObservation]]:
        timeseries = data.get("properties", {}).get("timeseries", [])
        if not timeseries:
            raise ValueError("MET.no svar inneholder ingen tidsseriedata.")

        # Filtrer timeseries for target_date
        target_iso = target_date.isoformat()
        day_points = [
            point for point in timeseries
            if point.get("time", "").startswith(target_iso)
        ]

        if not day_points:
            # Fallback til første tilgjengelige punkt hvis eksakt dato ikke finnes
            day_points = timeseries[:12]

        # Beregn representative verdier (f.eks. kveldstid 16-21 eller dagssnitt)
        temps = [p["data"]["instant"]["details"]["air_temperature"] for p in day_points if "air_temperature" in p.get("data", {}).get("instant", {}).get("details", {})]
        winds = [p["data"]["instant"]["details"]["wind_speed"] for p in day_points if "wind_speed" in p.get("data", {}).get("instant", {}).get("details", {})]
        
        # Nedbørsummering
        precip_vals = []
        for p in day_points:
            p_data = p.get("data", {})
            next_1h = p_data.get("next_1_hours", {}).get("details", {}).get("precipitation_amount")
            next_6h = p_data.get("next_6_hours", {}).get("details", {}).get("precipitation_amount")
            if next_1h is not None:
                precip_vals.append(next_1h)
            elif next_6h is not None:
                precip_vals.append(next_6h / 6.0)

        # Symbol code (velg mest representative fra ettermiddag/kveld eller første)
        symbol_code = "cloudy"
        for p in day_points:
            p_data = p.get("data", {})
            sym = (
                p_data.get("next_1_hours", {}).get("summary", {}).get("symbol_code")
                or p_data.get("next_6_hours", {}).get("summary", {}).get("symbol_code")
                or p_data.get("next_12_hours", {}).get("summary", {}).get("symbol_code")
            )
            if sym:
                symbol_code = sym
                if any(k in sym for k in ("rain", "sun", "clear")):
                    break

        avg_temp = round(sum(temps) / len(temps), 1) if temps else 15.0
        tot_precip = round(sum(precip_vals), 1) if precip_vals else 0.0
        avg_wind = round(sum(winds) / len(winds), 1) if winds else 3.5

        demand_text, category = evaluate_weather_demand_impact(
            target_date=target_date,
            temp_c=avg_temp,
            precip_mm=tot_precip,
            wind_mps=avg_wind,
            symbol_code=symbol_code,
        )

        signal = WeatherForecastSignal(
            period=target_date,
            symbol_code=symbol_code,
            temperature_c=avg_temp,
            precipitation_mm=tot_precip,
            wind_speed_mps=avg_wind,
            demand_impact=demand_text,
            impact_category=category,
            confidence=0.90 if tier_used == "live" else 0.80,
            source_tier=tier_used,
        )

        observations = [
            MarketObservation(
                period=target_date,
                source_system="met_no",
                metric="temperature_c",
                value=avg_temp,
                unit="celsius",
                label="Kristiansand Værtemperatur",
                geography="local",
                detail={"symbol_code": symbol_code, "category": category},
            ),
            MarketObservation(
                period=target_date,
                source_system="met_no",
                metric="precipitation_mm",
                value=tot_precip,
                unit="mm",
                label="Kristiansand Nedbør",
                geography="local",
                detail={"demand_impact": demand_text},
            ),
        ]

        return signal, observations


class FixtureMetNoWeatherAdapter:
    """100% deterministisk adapter for testing og offline-kjøring."""

    def __init__(self, fixture_path: Path, config: MetNoConfig = MetNoConfig()):
        self.fixture_path = fixture_path
        self.config = config
        self.adapter = MetNoWeatherAdapter(config=config)

    def fetch_forecast(self, target_date: date) -> tuple[WeatherForecastSignal, list[MarketObservation]]:
        return self.adapter.fetch_forecast(
            target_date=target_date,
            mode="fixture",
            fixture_path=self.fixture_path,
        )
```

---

### 4.4 Fixture Schema Specification (`sample_data/fixtures/met_no_sample.json`)

To ensure standard MET.no response simulation, `met_no_sample.json` mirrors the official compact format:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [7.9956, 58.1467, 10]
  },
  "properties": {
    "meta": {
      "updated_at": "2026-08-20T08:00:00Z",
      "units": {
        "air_temperature": "celsius",
        "precipitation_amount": "mm",
        "wind_speed": "m/s"
      }
    },
    "timeseries": [
      {
        "time": "2026-08-20T12:00:00Z",
        "data": {
          "instant": {
            "details": {
              "air_temperature": 18.5,
              "relative_humidity": 72.0,
              "wind_speed": 4.2
            }
          },
          "next_1_hours": {
            "summary": { "symbol_code": "rain" },
            "details": { "precipitation_amount": 3.2 }
          },
          "next_6_hours": {
            "summary": { "symbol_code": "rain" },
            "details": { "precipitation_amount": 8.5 }
          }
        }
      },
      {
        "time": "2026-08-20T18:00:00Z",
        "data": {
          "instant": {
            "details": {
              "air_temperature": 16.0,
              "relative_humidity": 80.0,
              "wind_speed": 5.1
            }
          },
          "next_1_hours": {
            "summary": { "symbol_code": "heavyrain" },
            "details": { "precipitation_amount": 4.5 }
          }
        }
      }
    ]
  }
}
```

---

## 5. Verification Method

### 5.1 Test Plan & Commands

To independently verify the implementation, write unit and integration tests under `tests/test_weather_and_calendar.py` and `tests/test_fetcher.py`.

#### Specific Test Cases for `tests/test_weather_and_calendar.py`:
1. `test_met_no_fixture_adapter_parsing`:
   - Validates that `FixtureMetNoWeatherAdapter` loads `sample_data/fixtures/met_no_sample.json`.
   - Checks that `WeatherForecastSignal` is populated with `period`, `temperature_c`, `precipitation_mm`, and `symbol_code`.
   - Checks that 2 `MarketObservation` objects (`temperature_c`, `precipitation_mm`) are emitted with `source_system="met_no"`.
2. `test_demand_heuristics_rain`:
   - Inputs high precipitation (e.g. 5.0 mm, `heavyrain`).
   - Asserts `demand_impact` recommends boosting indoor theaters and bistro dining (`impact_category == "boost_indoor"`).
3. `test_demand_heuristics_sunny_summer`:
   - Inputs $22.0^\circ\text{C}$, 0.0 mm, `clearsky_day`, July date.
   - Asserts `demand_impact` highlights outdoor terrace & Foajeen demand (`impact_category == "boost_outdoor"`).
4. `test_demand_heuristics_cold_winter`:
   - Inputs $2.0^\circ\text{C}$, wind 10.0 m/s.
   - Asserts `demand_impact` highlights warm meals and indoor stage events (`impact_category == "boost_indoor"`).
5. `test_met_no_user_agent_header`:
   - Verifies `MetNoWeatherAdapter` always sets `User-Agent: TeateretDecisionBrief/1.0 (kontakt@teateret.no)`.

#### Specific Test Cases for `tests/test_fetcher.py`:
1. `test_tiered_fetcher_tier1_live_success`:
   - Mocks live HTTPS 200 response with fake client.
   - Verifies data returned is marked `"live"` and written to disk cache.
2. `test_tiered_fetcher_tier2_cache_hit`:
   - Pre-populates `DiskCacheStore`.
   - Verifies subsequent call returns cached payload (`"cache"`) without invoking HTTP client.
3. `test_tiered_fetcher_tier1_failure_stale_fallback`:
   - Simulates HTTP 500 or network timeout on live fetch.
   - Verifies fetcher returns stale cache payload (`"cache"`) with zero crash.
4. `test_tiered_fetcher_tier3_fixture_fallback`:
   - In offline mode or when cache is missing, verifies static fixture is returned (`"fixture"`).
5. `test_ssrf_blocking_in_tiered_fetcher`:
   - Tests request against `https://127.0.0.1/` or `https://169.254.169.254/`.
   - Verifies `SourcePolicyError` is raised and private IPs are blocked.

### 5.2 Verification Command
```bash
python -m pytest tests/test_weather_and_calendar.py tests/test_fetcher.py -v
```
