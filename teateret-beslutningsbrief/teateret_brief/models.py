from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


Confidence = Literal["confirmed", "indication", "insufficient"]
RunStatus = Literal["completed", "warning", "blocked", "failed"]


class PublicEvent(BaseModel):
    """Offentlig kultur- eller fagarrangement på Teateret."""

    event_id: str | None = None
    date: date
    end_date: date | None = None
    time: str | None = None
    show_times: list[str] = Field(default_factory=list)
    title: str = Field(min_length=1)
    room: str | None = None
    capacity: int | None = None
    category: str | None = None
    source_url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _handle_field_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data_dict = dict(data)
            if "start_date" in data_dict and "date" not in data_dict:
                data_dict["date"] = data_dict["start_date"]
            if "start_time" in data_dict and "time" not in data_dict:
                data_dict["time"] = data_dict["start_time"]
            if "format" in data_dict and "category" not in data_dict:
                data_dict["category"] = data_dict["format"]
            return data_dict
        return data

    @property
    def start_date(self) -> date:
        return self.date

    @property
    def start_time(self) -> str | None:
        return self.time


class CrossSalesCorrelation(BaseModel):
    """Kryssalg-korrelasjon mellom sceneoppsetning og restaurant/bar."""

    event_id: str | None = None
    event_title: str
    event_date: date
    room: str | None = None
    tickets_sold: float = 0.0
    capacity: float = 0.0
    capacity_utilization_pct: float = 0.0
    table_reservations_2h: float = 0.0
    preorder_packages_2h: float = 0.0
    dining_revenue_nok: float = 0.0
    cross_sales_ratio: float = 0.0  # table_reservations_2h / tickets_sold
    preorder_conversion_pct: float = 0.0  # preorder_packages_2h / tickets_sold * 100
    preorder_table_conversion_pct: float = 0.0  # preorder_packages_2h / table_reservations_2h * 100
    revenue_per_ticket_nok: float = 0.0  # dining_revenue_nok / tickets_sold
    correlation_confidence: Literal["confirmed", "indication"] = "indication"

    @property
    def ticket_sales(self) -> float:
        return self.tickets_sold

    @property
    def table_covers_2h(self) -> int:
        return int(self.table_reservations_2h)

    @property
    def preorder_revenue_2h(self) -> float:
        return self.dining_revenue_nok


class SourceSpec(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1)
    url: HttpUrl
    region: Literal["local", "national", "reference"]
    topic: str = Field(min_length=1)
    enabled: bool = True


class SourceDocument(BaseModel):
    source_id: str
    url: str
    title: str
    published_at: str | None = None
    fetched_at: str
    text: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extractor: str


class SourceReference(BaseModel):
    source_id: str
    title: str
    url: str
    published_at: str | None = None
    fetched_at: str


class SalesObservation(BaseModel):
    period: date
    label: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    value: float
    unit: str = Field(min_length=1)
    source_system: str = "GastroPlanner"
    room: str | None = None
    event_id: str | None = None
    match_status: Literal["matched", "needs_review", "unmatched"] = "matched"


MarketSourceSystem = Literal["google_places", "google_trends", "schema_events"]


class MarketObservation(BaseModel):
    """Numerisk markedssignal fra ekstern kilde (ikke GastroPlanner)."""

    period: date
    source_system: MarketSourceSystem
    metric: str = Field(min_length=1)
    value: float
    unit: str = Field(min_length=1)
    label: str = Field(min_length=1)
    geography: str = "local"
    detail: dict | None = None


class SentimentTopic(BaseModel):
    """Aggregert sentiment per tema fra anmeldelser."""

    topic: str = Field(min_length=1)
    sentiment: Literal["positive", "mixed", "negative"]
    mention_count: int = Field(ge=0)
    sample_quotes: list[str] = Field(default_factory=list, max_length=3)


class ReviewSummary(BaseModel):
    """Aggregert anmeldelsesoppsummering – aldri individuelle anmeldelser med PII."""

    source_system: Literal["google_places", "tripadvisor"]
    place_name: str = Field(min_length=1)
    rating: float = Field(ge=1.0, le=5.0)
    total_reviews: int = Field(ge=0)
    fetched_at: str
    sentiment_topics: list[SentimentTopic] = Field(default_factory=list)


class Signal(BaseModel):
    id: str
    claim: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    geography: str
    confidence: Confidence

    @field_validator("source_ids")
    @classmethod
    def unique_sources(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class ReaderOutput(BaseModel):
    signals: list[Signal]

    @model_validator(mode="after")
    def unique_signal_ids(self):
        ids = [item.id for item in self.signals]
        if len(ids) != len(set(ids)):
            raise ValueError("Signal-ID-er må være unike.")
        return self


class Recommendation(BaseModel):
    id: str
    action: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    expected_value: str = Field(min_length=1)
    effort: Literal["low", "medium", "high"]


class AnalysisOutput(BaseModel):
    recommendations: list[Recommendation] = Field(max_length=3)

    @model_validator(mode="after")
    def unique_recommendation_ids(self):
        ids = [item.id for item in self.recommendations]
        if len(ids) != len(set(ids)):
            raise ValueError("Anbefalings-ID-er må være unike.")
        return self


class VerificationOutput(BaseModel):
    status: Literal["pass", "warn", "fail"]
    approved_recommendation_ids: list[str]
    warnings: list[str]


class Brief(BaseModel):
    run_id: str
    created_at: datetime
    status: RunStatus
    title: str = "Ukentlig beslutningsbrief for Teateret"
    signals: list[Signal]
    recommendations: list[Recommendation] = Field(max_length=3)
    source_ids: list[str]
    sources: list[SourceReference]
    warnings: list[str]
    market_observations: list[MarketObservation] = Field(default_factory=list)
    review_summaries: list[ReviewSummary] = Field(default_factory=list)


class PipelineResult(BaseModel):
    run_id: str
    status: RunStatus
    run_dir: Path
    stop_reason: str | None = None

    model_config = {"arbitrary_types_allowed": True}
