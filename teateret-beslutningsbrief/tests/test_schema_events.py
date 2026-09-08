from __future__ import annotations

from pathlib import Path

import pytest

from teateret_brief.models import SourceDocument, SourceSpec
from teateret_brief.security import SourcePolicyError
from teateret_brief.schema_events import (
    FixtureSchemaEventExtractor,
    parse_jsonld_events,
)

@pytest.fixture
def sample_html_with_events():
    return """
    <html>
    <head>
      <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Test Event 1",
        "startDate": "2026-08-25T19:00:00+02:00",
        "location": {
          "@type": "Place",
          "name": "Scene 1"
        },
        "offers": {
          "@type": "Offer",
          "price": "200",
          "priceCurrency": "NOK",
          "availability": "https://schema.org/InStock"
        }
      }
      </script>
    </head>
    <body>
        <script type="application/ld+json">
        [
          {
            "@type": "Event",
            "name": "Test Event 2 Kontakt oss: post@example.com",
            "startDate": "2026-08-26T20:00:00+02:00",
            "location": {
              "@type": "Place",
              "name": "Scene 2"
            },
            "offers": {
              "@type": "Offer",
              "price": "300",
              "priceCurrency": "NOK",
              "availability": "https://schema.org/SoldOut"
            }
          }
        ]
        </script>
    </body>
    </html>
    """

def test_parse_jsonld_extracts_events(sample_html_with_events):
    text = parse_jsonld_events(sample_html_with_events, "TestKilde", "2026-08-20 12:00")
    
    assert 'Arrangementer fra TestKilde' in text
    assert '- "Test Event 1" | 25. aug 2026 kl 19:00 | Scene 1 | Billettstatus: tilgjengelig | 200 NOK' in text
    assert '- "Test Event 2 Kontakt oss: post@example.com" | 26. aug 2026 kl 20:00 | Scene 2 | Billettstatus: utsolgt | 300 NOK' in text

def test_empty_events_raises():
    with pytest.raises(SourcePolicyError, match="Ingen arrangementer funnet i JSON-LD"):
        parse_jsonld_events("<html><body><p>No events</p></body></html>", "Test", "2026")

def test_malformed_jsonld_does_not_crash():
    html = """
    <script type="application/ld+json">
    { invalid json ]
    </script>
    <script type="application/ld+json">
    {
      "@type": "Event",
      "name": "Valid Event"
    }
    </script>
    """
    text = parse_jsonld_events(html, "Test", "2026")
    assert "Valid Event" in text

def test_pii_redaction_applied():
    from teateret_brief.security import redact_contact_details
    html = """
    <script type="application/ld+json">
    {
      "@type": "Event",
      "name": "Secret Event at +4799999999 or secret@test.no",
      "startDate": "2026-08-25T19:00:00+02:00"
    }
    </script>
    """
    text = parse_jsonld_events(html, "Test", "2026")
    redacted, _ = redact_contact_details(text)
    assert "secret@test.no" not in redacted
    assert "[MASKERT_EPOST]" in redacted
    assert "+4799999999" not in redacted
    assert "[MASKERT_TELEFON]" in redacted

def test_fixture_extractor_returns_valid_source_document():
    fixture_path = Path("sample_data/schema_events_fixture.json")
    if not fixture_path.exists():
        pytest.skip("Fixture not found")
        
    extractor = FixtureSchemaEventExtractor(fixture_path)
    source = SourceSpec(
        id="test_schema",
        name="Test Teater",
        url="https://example.com/events",
        region="local",
        topic="events"
    )
    
    doc = extractor.extract(source)
    assert isinstance(doc, SourceDocument)
    assert doc.source_id == "test_schema"
    assert doc.extractor == "fixture_schema_jsonld"
    assert "Arrangementer fra Test Teater" in doc.text
    assert "Latter på lørdag" in doc.text
    assert "Billettstatus: tilgjengelig" in doc.text

def test_extractor_field_is_correct():
    # Tested within the fixture test above
    pass
