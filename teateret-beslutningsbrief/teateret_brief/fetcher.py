from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from html.parser import HTMLParser
from xml.etree import ElementTree

import httpx

from .models import SourceDocument, SourceSpec
from .security import SourcePolicy, SourcePolicyError, redact_contact_details


class _ReadableHtmlParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.title_depth = 0
        self.title_parts: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.casefold()
        if tag in {"script", "style", "nav", "noscript", "svg"}:
            self.skip_depth += 1
        if tag == "title":
            self.title_depth += 1

    def handle_endtag(self, tag):
        tag = tag.casefold()
        if tag in {"script", "style", "nav", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title" and self.title_depth:
            self.title_depth -= 1

    def handle_data(self, data):
        text = " ".join(data.split())
        if not text:
            return
        if self.title_depth:
            self.title_parts.append(text)
        if not self.skip_depth and not self.title_depth:
            self.parts.append(text)


def _extract_html(content: bytes) -> tuple[str, str, str]:
    html = content.decode("utf-8", errors="replace")
    parser = _ReadableHtmlParser()
    parser.feed(html)
    title = " ".join(parser.title_parts).strip() or "Uten tittel"
    fallback = "\n".join(parser.parts).strip()
    try:
        import trafilatura  # type: ignore

        extracted = trafilatura.extract(
            html,
            output_format="txt",
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
    except ImportError:
        extracted = None
    text = (extracted or fallback).strip()
    if not text:
        raise SourcePolicyError("Nettsiden inneholdt ingen lesbar tekst.")
    return title, text, "trafilatura" if extracted else "stdlib_html"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _first_text(element, names: set[str]) -> str | None:
    for child in element.iter():
        if _local_name(child.tag) in names and child.text and child.text.strip():
            return child.text.strip()
    return None


def _extract_feed(content: bytes) -> tuple[str, str, str | None]:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise SourcePolicyError("RSS/Atom-kilden er skadet eller ugyldig.") from exc
    title = _first_text(root, {"title"}) or "Uten tittel"
    entries = [item for item in root.iter() if _local_name(item.tag) in {"item", "entry"}]
    parts: list[str] = []
    published_at: str | None = None
    for entry in entries[:50]:
        entry_title = _first_text(entry, {"title"})
        description = _first_text(entry, {"description", "summary", "content"})
        published = _first_text(entry, {"pubdate", "published", "updated"})
        if published_at is None and published:
            published_at = published
        if entry_title:
            parts.append(entry_title)
        if description:
            parts.append(description)
    if not parts:
        raise SourcePolicyError("RSS/Atom-kilden inneholdt ingen elementer.")
    return title, "\n".join(parts), published_at


class SafeHttpFetcher:
    def __init__(
        self,
        policy: SourcePolicy,
        *,
        client=None,
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

    def fetch(self, source: SourceSpec) -> SourceDocument:
        approved = self.policy.validate(str(source.url))
        with self.client.stream("GET", approved.url, follow_redirects=False) as response:
            if 300 <= response.status_code < 400:
                raise SourcePolicyError("Redirect ble blokkert; ny URL må godkjennes manuelt.")
            response.raise_for_status()
            try:
                declared_size = int(response.headers.get("content-length", "0"))
            except ValueError:
                declared_size = 0
            if declared_size > self.max_bytes:
                raise SourcePolicyError("Kilden er større enn tillatt grense.")
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > self.max_bytes:
                    raise SourcePolicyError("Kilden er større enn tillatt grense.")
                chunks.append(chunk)
            content = b"".join(chunks)
            content_type = response.headers.get("content-type", "").casefold()
        if "rss" in content_type or "atom" in content_type or "xml" in content_type:
            title, text, published_at = _extract_feed(content)
            extractor = "stdlib_feed"
        else:
            title, text, extractor = _extract_html(content)
            published_at = None
        text, _ = redact_contact_details(text)
        return SourceDocument(
            source_id=source.id,
            url=approved.url,
            title=title,
            published_at=published_at,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            text=text,
            content_sha256=hashlib.sha256(content).hexdigest(),
            extractor=extractor,
        )


class FixtureFetcher:
    def __init__(self, fixture_paths: dict[str, str], repo_paths):
        self.fixture_paths = fixture_paths
        self.repo_paths = repo_paths

    def fetch(self, source: SourceSpec) -> SourceDocument:
        relative = self.fixture_paths.get(source.id)
        if not relative:
            raise FileNotFoundError(f"Ingen fixture for kilde {source.id}")
        path = self.repo_paths.input_path(relative)
        content = path.read_bytes()
        if path.suffix.casefold() in {".xml", ".rss", ".atom"}:
            title, text, published_at = _extract_feed(content)
            extractor = "fixture_feed"
        elif path.suffix.casefold() == ".json":
            from .schema_events import FixtureSchemaEventExtractor

            return FixtureSchemaEventExtractor(path).extract(source)
        else:
            title, text, base_extractor = _extract_html(content)
            published_at = None
            extractor = f"fixture_{base_extractor}"
        text, _ = redact_contact_details(text)
        return SourceDocument(
            source_id=source.id,
            url=str(source.url),
            title=title,
            published_at=published_at,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            text=text,
            content_sha256=hashlib.sha256(content).hexdigest(),
            extractor=extractor,
        )
