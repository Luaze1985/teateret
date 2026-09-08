from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .models import PublicEvent, SalesObservation


class MatchResult(BaseModel):
    observation_label: str
    period: date
    room: str | None = None
    event_id: str | None = None
    matched_event_title: str | None = None
    match_status: Literal["matched", "needs_review", "unmatched"]
    match_level: Literal["level_1_id", "level_2_title_date_room", "level_3_proximity", "none"]
    reason: str
    matched_event: PublicEvent | None = None
    observation: SalesObservation | None = None


class MatchingReport(BaseModel):
    total_observations: int
    matched_count: int
    needs_review_count: int
    unmatched_count: int
    match_rate_percent: float
    results: list[MatchResult]


# Interface alias for SCOPE.md and PROJECT.md compatibility
MatchReport = MatchingReport


def normalize_title(title: str) -> str:
    """Deterministic Norwegian text normalizer preserving æ, ø, å."""
    cleaned = unicodedata.normalize("NFC", title).lower().strip()
    # Normalize & to og for Norwegian matching
    cleaned = re.sub(r"\s*&\s*", " og ", cleaned)
    # Replace en-dash, em-dash, minus, slashes, colons with spaces
    cleaned = re.sub(r"[–—\-\−/:]+", " ", cleaned)
    # Remove surrounding quotes and brackets
    cleaned = re.sub(r"[«»\"'()\[\]]", "", cleaned)
    # Normalize multiple whitespace characters
    cleaned = re.sub(r"[\s\t\n\r\u00a0\u202f]+", " ", cleaned)
    return cleaned.strip()


_normalize_title = normalize_title


DEFAULT_SYNONYMS: dict[str, str] = {
    "jazzfestival": "kristiansand jazzfestival 26 air m.fl.",
    "jazzfestivalen": "kristiansand jazzfestival 26 air m.fl.",
    "kristiansand jazzfestival": "kristiansand jazzfestival 26 air m.fl.",
    "svanesjøen": "svanesjøen etoile ballet",
    "norge england vm på storskjerm": "fotball vm storskjerm norge england",
    "norge england": "fotball vm storskjerm norge england",
    "vm storskjerm": "fotball vm storskjerm norge england",
    "sommerstandup": "sommerstandup med fire halvkjente fjes",
    "baldrian og musa": "baldrian og musa luft og kjærlighet",
    "teaterquiz": "quiz",
}

ROOM_CAPACITIES: dict[str, int] = {
    "hovedscenen": 400,
    "biscenen": 148,
    "intimscenen": 90,
    "foajeen": 50,
    "restauranten": 80,
    "restaurant": 80,
}

ROOM_ALIASES: dict[str, str] = {
    "store sal": "hovedscenen",
    "storsalen": "hovedscenen",
    "teatersalen": "hovedscenen",
    "hovedscene": "hovedscenen",
    "lillesalen": "biscenen",
    "amfi": "biscenen",
    "black box": "biscenen",
    "biscene": "biscenen",
    "salong": "intimscenen",
    "intimscene": "intimscenen",
    "foaje": "foajeen",
    "lobby": "foajeen",
    "baren": "restauranten",
    "restaurant": "restauranten",
}


def _canonical_room(room: str | None) -> str | None:
    if not room:
        return None
    r = room.lower().strip()
    return ROOM_ALIASES.get(r, r)


def _rooms_agree(obs_room: str | None, event_room: str | None) -> bool:
    if not obs_room or not event_room:
        return True
    c_obs = _canonical_room(obs_room)
    c_evt = _canonical_room(event_room)
    if not c_obs or not c_evt:
        return True
    if c_obs in c_evt or c_evt in c_obs:
        return True
    obs_parts = {p.strip() for p in re.split(r"[/,&+]+", c_obs) if p.strip()}
    evt_parts = {p.strip() for p in re.split(r"[/,&+]+", c_evt) if p.strip()}
    if obs_parts & evt_parts:
        return True
    return False


def load_public_events(source_path: Path | str | None = None) -> list[PublicEvent]:
    """Parse authoritative arrangementsdata-2025-2026.md to extract all 129 verified events."""
    if source_path is None:
        candidates = [
            Path("docs/research/arrangementsdata-2025-2026.md"),
            Path(__file__).resolve().parent.parent / "docs" / "research" / "arrangementsdata-2025-2026.md",
        ]
        for cand in candidates:
            if cand.exists():
                source_path = cand
                break

    if source_path is None or not Path(source_path).exists():
        return []

    path = Path(source_path)
    content = path.read_text(encoding="utf-8")
    events: list[PublicEvent] = []

    # Table rows pattern: | **2026-02-25** | 18:00 | Speed date 40–59 | Temakveld | Foajeen | [teateret.no](...) |
    row_pattern = re.compile(
        r"\|\s*\*\*(\d{4}-\d{2}-\d{2}(?:[–—\-]\d{2})?)\*\*\s*\|\s*([^|]*)\|\s*([^|]+)\|\s*([^|]*)\|\s*([^|]+)\|\s*([^|]*)\|"
    )

    date_counts: dict[str, int] = {}

    for line in content.splitlines():
        match = row_pattern.search(line)
        if not match:
            continue

        raw_date = match.group(1).strip()
        time_str = match.group(2).strip() or None
        title_str = match.group(3).strip()
        category_str = match.group(4).strip() or None
        room_str = match.group(5).strip() or None
        kilde_str = match.group(6).strip() or None

        # Clean title quotes
        title_clean = re.sub(r"^[«\"']+|[»\"']+$", "", title_str).strip()

        # Parse date and multi-day range
        start_date: date
        end_date: date | None = None
        if "–" in raw_date or "—" in raw_date or (len(raw_date) > 10 and "-" in raw_date[10:]):
            parts = re.split(r"[–—\-]", raw_date)
            if len(parts) >= 4:
                year, month, start_day, end_day = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
                start_date = date(year, month, start_day)
                end_date = date(year, month, end_day)
            else:
                try:
                    start_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
                    end_day_int = int(raw_date[11:])
                    end_date = date(start_date.year, start_date.month, end_day_int)
                except Exception:
                    start_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
        else:
            try:
                start_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
            except ValueError:
                continue

        # Extract source URL
        source_url: str | None = None
        if kilde_str:
            url_m = re.search(r"\((https?://[^)]+)\)", kilde_str)
            if url_m:
                source_url = url_m.group(1)
            elif kilde_str.startswith("http"):
                source_url = kilde_str

        # Show times
        show_times = re.findall(r"\b\d{1,2}:\d{2}\b", time_str or "")

        # Infer capacity
        cap: int | None = None
        if room_str:
            norm_r = room_str.lower()
            if "hovedscenen" in norm_r:
                cap = 400
            elif "biscenen" in norm_r:
                cap = 148
            elif "intimscenen" in norm_r:
                cap = 90
            elif "foaje" in norm_r:
                cap = 50
            elif "restaurant" in norm_r:
                cap = 80

        # Deterministic Event ID: EVT-YYMMDD
        date_key = start_date.strftime("%y%m%d")
        date_counts[date_key] = date_counts.get(date_key, 0) + 1
        event_id = f"EVT-{date_key}"

        events.append(
            PublicEvent(
                event_id=event_id,
                date=start_date,
                end_date=end_date,
                time=time_str,
                show_times=show_times,
                title=title_clean,
                room=room_str,
                capacity=cap,
                category=category_str,
                source_url=source_url,
            )
        )

    return events


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
        self._events_by_id: dict[str, PublicEvent] = {}
        self._events_list_by_id: dict[str, list[PublicEvent]] = {}
        self._events_by_date: dict[date, list[PublicEvent]] = {}

        for event in events:
            if event.event_id:
                eid_clean = event.event_id.strip()
                if eid_clean not in self._events_by_id:
                    self._events_by_id[eid_clean] = event
                    self._events_by_id[eid_clean.upper()] = event
                    self._events_by_id[eid_clean.lower()] = event
                self._events_list_by_id.setdefault(eid_clean.upper(), []).append(event)

            # Multi-day date indexing
            if event.end_date and event.end_date >= event.date:
                curr = event.date
                while curr <= event.end_date:
                    self._events_by_date.setdefault(curr, []).append(event)
                    curr = curr + timedelta(days=1)
            else:
                self._events_by_date.setdefault(event.date, []).append(event)

    def match(self, observation: SalesObservation) -> MatchResult:
        # Nivå 1: Direkte ID-match (ADR 0002)
        if observation.event_id:
            eid = observation.event_id.strip()
            candidates = self._events_list_by_id.get(eid.upper(), [])
            if candidates:
                # Disambiguate if multiple events share same ID
                matched_event = candidates[0]
                if len(candidates) > 1 and observation.room:
                    for cand in candidates:
                        if _rooms_agree(observation.room, cand.room):
                            matched_event = cand
                            break
                return MatchResult(
                    observation_label=observation.label,
                    period=observation.period,
                    room=observation.room,
                    event_id=observation.event_id,
                    matched_event_title=matched_event.title,
                    match_status="matched",
                    match_level="level_1_id",
                    reason=f"Eksakt arrangements-ID {observation.event_id}",
                    matched_event=matched_event,
                    observation=observation,
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
                matched_event=None,
                observation=observation,
            )

        norm_obs_label = normalize_title(observation.label)
        mapped_obs_label = self.synonyms.get(norm_obs_label, norm_obs_label)

        # Nivå 2: Tittel + Dato + Rom Heuristikk (ADR 0002)
        candidate_matches: list[tuple[PublicEvent, bool]] = []
        for event in events_on_date:
            norm_event_title = normalize_title(event.title)
            mapped_event_title = self.synonyms.get(norm_event_title, norm_event_title)

            exact_title = (
                norm_obs_label == norm_event_title
                or mapped_obs_label == norm_event_title
                or norm_obs_label == mapped_event_title
                or mapped_obs_label == mapped_event_title
            )
            substr_title = (
                (len(norm_obs_label) >= 3 and norm_obs_label in norm_event_title)
                or (len(norm_event_title) >= 3 and norm_event_title in norm_obs_label)
                or (len(mapped_obs_label) >= 3 and mapped_obs_label in norm_event_title)
                or (len(norm_event_title) >= 3 and norm_event_title in mapped_obs_label)
                or (len(mapped_obs_label) >= 3 and mapped_obs_label in mapped_event_title)
                or (len(mapped_event_title) >= 3 and mapped_event_title in mapped_obs_label)
            )

            if exact_title or substr_title:
                room_agrees = _rooms_agree(observation.room, event.room)
                if room_agrees:
                    candidate_matches.append((event, exact_title))

        if candidate_matches:
            exact_cands = [c for c, is_ex in candidate_matches if is_ex]
            best_event = exact_cands[0] if exact_cands else candidate_matches[0][0]
            return MatchResult(
                observation_label=observation.label,
                period=observation.period,
                room=observation.room,
                event_id=observation.event_id,
                matched_event_title=best_event.title,
                match_status="matched",
                match_level="level_2_title_date_room",
                reason=f"Tittel- og datomatch mot '{best_event.title}'",
                matched_event=best_event,
                observation=observation,
            )

        # Nivå 3: Tids- og romnærhet / estimert korrelasjon (needs_review) (ADR 0002)
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
                matched_event=candidate,
                observation=observation,
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
            matched_event=None,
            observation=observation,
        )

    def evaluate_all(self, observations: list[SalesObservation]) -> MatchingReport:
        # Dedup observations by (period, label, room, event_id) to count unique event records
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
