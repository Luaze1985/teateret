from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from .models import MarketObservation


@dataclass(frozen=True)
class GoogleTrendsConfig:
    keywords: list[str]
    geo: str = "NO-42"  # Agder
    timeframe: str = "today 3-m"  # Last 90 days
    max_keywords_per_call: int = 5


class GoogleTrendsAdapter:
    """Live adapter – bruker pytrends for Google Trends-data."""
    
    def __init__(self, config: GoogleTrendsConfig):
        self.config = config
    
    def fetch(self) -> list[MarketObservation]:
        try:
            from pytrends.request import TrendReq
        except ImportError:
            raise RuntimeError(
                "pytrends er ikke installert. Installer med: pip install 'teateret-brief[google]'"
            )
        
        pytrends = TrendReq(hl="no", tz=120, timeout=(10, 25))
        observations = []
        today = date.today()
        
        # Process keywords in batches of max_keywords_per_call
        for i in range(0, len(self.config.keywords), self.config.max_keywords_per_call):
            batch = self.config.keywords[i:i + self.config.max_keywords_per_call]
            try:
                pytrends.build_payload(
                    batch,
                    cat=0,
                    timeframe=self.config.timeframe,
                    geo=self.config.geo,
                )
                df = pytrends.interest_over_time()
                if df.empty:
                    continue
                
                # Get the most recent week's average for each keyword
                for keyword in batch:
                    if keyword in df.columns:
                        recent_value = float(df[keyword].iloc[-1])
                        observations.append(MarketObservation(
                            period=today,
                            source_system="google_trends",
                            metric="search_interest",
                            value=recent_value,
                            unit="relative_0_100",
                            label=keyword,
                            geography="agder",
                            detail={
                                "geo": self.config.geo,
                                "timeframe": self.config.timeframe,
                                "trend_direction": self._trend_direction(df[keyword]),
                            },
                        ))
            except Exception:
                # pytrends failures should never crash the pipeline
                continue
        
        return observations
    
    @staticmethod
    def _trend_direction(series) -> str:
        """Enkel trendretning basert på siste vs. foregående periode."""
        if len(series) < 2:
            return "stable"
        last = float(series.iloc[-1])
        prev = float(series.iloc[-2])
        if prev == 0:
            return "rising" if last > 0 else "stable"
        change = (last - prev) / prev
        if change > 0.15:
            return "rising"
        elif change < -0.15:
            return "falling"
        return "stable"


class FixtureGoogleTrendsAdapter:
    """Deterministisk demo-adapter uten nettverkskall."""
    
    def __init__(self, fixture_path: Path, config: GoogleTrendsConfig):
        self.fixture_path = fixture_path
        self.config = config
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture finnes ikke: {fixture_path}")
    
    def fetch(self) -> list[MarketObservation]:
        data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        today = date.today()
        observations = []
        for item in data.get("trends", []):
            observations.append(MarketObservation(
                period=today,
                source_system="google_trends",
                metric="search_interest",
                value=item["value"],
                unit="relative_0_100",
                label=item["keyword"],
                geography="agder",
                detail=item.get("detail"),
            ))
        return observations
