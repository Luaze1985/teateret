from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .models import SourceDocument, SourceSpec
from .security import SourcePolicy, SourcePolicyError, redact_contact_details

_JSON_LD_PATTERN = re.compile(
    r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', 
    re.IGNORECASE | re.DOTALL
)

def _format_date(iso_str: str) -> str:
    if not iso_str:
        return "Ukjent tid"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        months = ["jan", "feb", "mar", "apr", "mai", "jun", "jul", "aug", "sep", "okt", "nov", "des"]
        return f"{dt.day}. {months[dt.month-1]} {dt.year} kl {dt.hour:02d}:{dt.minute:02d}"
    except Exception:
        return iso_str

def parse_jsonld_events(html_content: str, source_name: str, timestamp: str) -> str:
    events = []
    
    def extract_events(data: Any):
        if isinstance(data, dict):
            if data.get("@type") == "Event":
                events.append(data)
            for value in data.values():
                extract_events(value)
        elif isinstance(data, list):
            for item in data:
                extract_events(item)

    for match in _JSON_LD_PATTERN.finditer(html_content):
        try:
            script_content = match.group(1).strip()
            if not script_content:
                continue
            parsed = json.loads(script_content)
            extract_events(parsed)
        except json.JSONDecodeError:
            continue
            
    if not events:
        raise SourcePolicyError("Ingen arrangementer funnet i JSON-LD.")

    lines = [f"Arrangementer fra {source_name} (hentet {timestamp}):"]
    
    for event in events:
        name = event.get("name", "Ukjent navn")
        
        start_date = event.get("startDate", "")
        start_date_str = _format_date(start_date)

        location = event.get("location", {})
        if isinstance(location, dict):
            loc_name = location.get("name", "Ukjent sted")
        else:
            loc_name = "Ukjent sted"

        offers = event.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        elif not isinstance(offers, dict):
            offers = {}
            
        availability = offers.get("availability", "").split("/")[-1]
        availability_map = {
            "InStock": "tilgjengelig",
            "SoldOut": "utsolgt",
            "LimitedAvailability": "få billetter"
        }
        avail_str = availability_map.get(availability, availability) or "ukjent"
        
        price = offers.get("price", "Ukjent")
        currency = offers.get("priceCurrency", "NOK")
        
        lines.append(f'- "{name}" | {start_date_str} | {loc_name} | Billettstatus: {avail_str} | {price} {currency}')

    return "\n".join(lines)


class SchemaEventExtractor:
    def __init__(
        self,
        policy: SourcePolicy,
        *,
        client: httpx.Client | None = None,
        max_bytes: int = 500_000,
        timeout_seconds: float = 15.0,
    ):
        self.policy = policy
        self.max_bytes = max_bytes
        self.client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": "TeateretDecisionBrief/0.1"},
        )

    def extract(self, source: SourceSpec) -> SourceDocument:
        approved = self.policy.validate(str(source.url))
        with self.client.stream("GET", approved.url, follow_redirects=False) as response:
            if 300 <= response.status_code < 400:
                raise SourcePolicyError("Redirect ble blokkert; ny URL må godkjennes manuelt.")
            response.raise_for_status()
            
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > self.max_bytes:
                    raise SourcePolicyError("Kilden er større enn tillatt grense.")
                chunks.append(chunk)
            content = b"".join(chunks)

        html = content.decode("utf-8", errors="replace")
        fetched_at = datetime.now(timezone.utc).isoformat()
        
        try:
            timestamp_short = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        except Exception:
            timestamp_short = fetched_at
            
        text = parse_jsonld_events(html, source.name, timestamp_short)
        redacted_text, _ = redact_contact_details(text)

        return SourceDocument(
            source_id=source.id,
            url=approved.url,
            title=f"Schema Events fra {source.name}",
            published_at=None,
            fetched_at=fetched_at,
            text=redacted_text,
            content_sha256=hashlib.sha256(content).hexdigest(),
            extractor="schema_jsonld",
        )


class FixtureSchemaEventExtractor:
    def __init__(self, fixture_path: Path):
        self.fixture_path = fixture_path

    def extract(self, source: SourceSpec) -> SourceDocument:
        if not self.fixture_path.exists():
            raise FileNotFoundError(f"Fixture-fil finnes ikke: {self.fixture_path}")
            
        content = self.fixture_path.read_bytes()
        
        fixture_data = json.loads(content)
        jsonld_events = []
        for e in fixture_data.get("events", []):
            jsonld_events.append({
                "@type": "Event",
                "name": e.get("name"),
                "startDate": e.get("startDate"),
                "endDate": e.get("endDate"),
                "location": {"@type": "Place", "name": e.get("location")},
                "offers": {
                    "@type": "Offer",
                    "availability": f"https://schema.org/{e.get('availability')}",
                    "price": e.get("price"),
                    "priceCurrency": e.get("priceCurrency")
                }
            })
        
        mock_html = f'''<html><body>
        <script type="application/ld+json">
        {json.dumps(jsonld_events)}
        </script>
        </body></html>'''
        
        fetched_at = datetime.now(timezone.utc).isoformat()
        timestamp_short = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        
        text = parse_jsonld_events(mock_html, source.name, timestamp_short)
        redacted_text, _ = redact_contact_details(text)
        
        return SourceDocument(
            source_id=source.id,
            url=str(source.url),
            title=f"Schema Events fra {source.name}",
            published_at=None,
            fetched_at=fetched_at,
            text=redacted_text,
            content_sha256=hashlib.sha256(content).hexdigest(),
            extractor="fixture_schema_jsonld",
        )
