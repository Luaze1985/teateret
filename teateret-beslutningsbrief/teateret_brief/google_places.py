from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from .models import MarketObservation, ReviewSummary, SentimentTopic
from .security import redact_contact_details, redact_reviewer_identity, assert_review_limit


@dataclass(frozen=True)
class PlaceConfig:
    place_id: str
    name: str
    role: str = "primary"  # "primary" or "competitor"
    enabled: bool = True


@dataclass(frozen=True)
class GooglePlacesConfig:
    places: list[PlaceConfig]
    sentiment_topics: list[str]
    max_reviews_per_place: int = 20
    language: str = "no"


class GooglePlacesResult(BaseModel):
    review_summary: ReviewSummary
    observations: list[MarketObservation]


class GooglePlacesAdapter:
    """Live adapter – kaller Google Places API (New) med httpx."""
    
    FIELDS = "displayName,rating,userRatingCount,reviews,currentOpeningHours,regularOpeningHours"
    BASE_URL = "https://places.googleapis.com/v1/places"
    
    def __init__(self, config: GooglePlacesConfig, *, client: httpx.Client | None = None):
        self.config = config
        api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
        if not api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY er ikke satt.")
        self.client = client or httpx.Client(
            timeout=15.0,
            headers={
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": self.FIELDS,
            },
        )
    
    def fetch(self, place: PlaceConfig) -> GooglePlacesResult:
        response = self.client.get(f"{self.BASE_URL}/{place.place_id}")
        response.raise_for_status()
        data = response.json()
        return self._parse_response(data, place)
    
    def fetch_all(self) -> list[GooglePlacesResult]:
        results = []
        for place in self.config.places:
            if place.enabled:
                results.append(self.fetch(place))
        return results
    
    def _parse_response(self, data: dict, place: PlaceConfig) -> GooglePlacesResult:
        now = datetime.now(timezone.utc)
        today = date.today()
        rating = data.get("rating", 0.0)
        review_count = data.get("userRatingCount", 0)
        
        # Process reviews for sentiment
        raw_reviews = data.get("reviews", [])[:self.config.max_reviews_per_place]
        assert_review_limit(len(raw_reviews), self.config.max_reviews_per_place)
        sentiment_topics = self._analyze_sentiment(raw_reviews)
        
        review_summary = ReviewSummary(
            source_system="google_places",
            place_name=place.name,
            rating=max(1.0, min(5.0, rating)),
            total_reviews=review_count,
            fetched_at=now.isoformat(),
            sentiment_topics=sentiment_topics,
        )
        
        observations = [
            MarketObservation(
                period=today,
                source_system="google_places",
                metric="rating",
                value=rating,
                unit="score_1_5",
                label=place.name,
            ),
            MarketObservation(
                period=today,
                source_system="google_places",
                metric="review_count",
                value=float(review_count),
                unit="count",
                label=place.name,
            ),
        ]
        
        return GooglePlacesResult(
            review_summary=review_summary,
            observations=observations,
        )
    
    def _analyze_sentiment(self, reviews: list[dict]) -> list[SentimentTopic]:
        """Enkel nøkkelordbasert sentimentanalyse av anmeldelser."""
        # Map Norwegian topic keywords
        topic_keywords = {
            "mat": ["mat", "food", "meny", "rett", "smak", "kjøkken", "dessert", "forrett", "middag"],
            "service": ["service", "servering", "kelner", "betjening", "vennlig", "hyggelig", "treg"],
            "lyd": ["lyd", "akustikk", "sound", "høyt", "støy", "musikk"],
            "atmosfære": ["atmosfære", "stemning", "interiør", "lokale", "koselig", "ambient"],
            "pris": ["pris", "dyrt", "billig", "verdi", "price", "koster"],
        }
        positive_words = {"bra", "god", "flott", "fantastisk", "utmerket", "herlig", "topp", "great", "good", "excellent", "amazing", "anbefal", "deilig", "perfekt"}
        negative_words = {"dårlig", "treg", "kald", "skuffende", "elendig", "bad", "poor", "terrible", "awful", "lang ventetid", "dyrt"}
        
        topic_results: dict[str, dict] = {}
        for topic in self.config.sentiment_topics:
            if topic in topic_keywords:
                topic_results[topic] = {"positive": 0, "negative": 0, "mentions": 0, "quotes": []}
        
        for review in reviews:
            text_obj = review.get("text", review.get("originalText", {}))
            if isinstance(text_obj, dict):
                text = text_obj.get("text", "")
            else:
                text = str(text_obj)
            author = review.get("authorAttribution", {}).get("displayName", "")
            text, _ = redact_contact_details(text)
            text = redact_reviewer_identity(text, author)
            text_lower = text.lower()
            
            for topic, keywords in topic_keywords.items():
                if topic not in topic_results:
                    continue
                if any(kw in text_lower for kw in keywords):
                    topic_results[topic]["mentions"] += 1
                    has_positive = any(w in text_lower for w in positive_words)
                    has_negative = any(w in text_lower for w in negative_words)
                    if has_positive:
                        topic_results[topic]["positive"] += 1
                    if has_negative:
                        topic_results[topic]["negative"] += 1
                    if len(topic_results[topic]["quotes"]) < 3:
                        # Truncate quote
                        quote = text[:120] + "..." if len(text) > 120 else text
                        topic_results[topic]["quotes"].append(quote)
        
        sentiments = []
        for topic, data in topic_results.items():
            if data["mentions"] == 0:
                continue
            if data["positive"] > data["negative"]:
                sentiment = "positive"
            elif data["negative"] > data["positive"]:
                sentiment = "negative"
            else:
                sentiment = "mixed"
            sentiments.append(SentimentTopic(
                topic=topic,
                sentiment=sentiment,
                mention_count=data["mentions"],
                sample_quotes=data["quotes"],
            ))
        return sentiments


class FixtureGooglePlacesAdapter:
    """Deterministisk demo-adapter uten nettverkskall."""
    
    def __init__(self, fixture_path: Path, config: GooglePlacesConfig):
        self.fixture_path = fixture_path
        self.config = config
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture finnes ikke: {fixture_path}")
    
    def fetch(self, place: PlaceConfig) -> GooglePlacesResult:
        data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        return self._parse_fixture(data, place)
    
    def fetch_all(self) -> list[GooglePlacesResult]:
        results = []
        for place in self.config.places:
            if place.enabled:
                results.append(self.fetch(place))
        return results
    
    def _parse_fixture(self, data: dict, place: PlaceConfig) -> GooglePlacesResult:
        now = datetime.now(timezone.utc)
        today = date.today()
        
        review_summary = ReviewSummary(
            source_system="google_places",
            place_name=place.name,
            rating=data.get("rating", 4.5),
            total_reviews=data.get("total_reviews", 500),
            fetched_at=now.isoformat(),
            sentiment_topics=[
                SentimentTopic(**topic)
                for topic in data.get("sentiment_topics", [])
            ],
        )
        
        observations = [
            MarketObservation(
                period=today,
                source_system="google_places",
                metric=obs["metric"],
                value=obs["value"],
                unit=obs["unit"],
                label=place.name,
                detail=obs.get("detail"),
            )
            for obs in data.get("observations", [])
        ]
        
        return GooglePlacesResult(
            review_summary=review_summary,
            observations=observations,
        )
