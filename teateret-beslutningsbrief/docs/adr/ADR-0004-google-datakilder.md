---
title: "ADR-0004: Google-datakilder for markedssignaler"
date: 2026-08-20
status: accepted
tags: [google, places, trends, schema, markedssignaler, adapter]
category: adr
---

# ADR-0004: Google-datakilder for markedssignaler

## Kontekst

Teaterets beslutningsbrief har to eksisterende datakildetyper:
1. **Nettkilder** (SafeHttpFetcher → SourceDocument)
2. **GastroPlanner CSV** (csv_adapter → SalesObservation)

Ledelsen trenger markedssignaler fra Google for å vurdere gjestetilfredshet,
regional etterspørsel og konkurrentaktivitet. Disse dataene er gratis og
offentlig tilgjengelige.

## Beslutning

Vi introduserer tre nye adaptere:

### 1. Google Places-adapter (`google_places.py`)
- Henter GBP-data (rating, anmeldelsesvolum, sentiment) via Google Places API (New)
- API-nøkkel i miljøvariabel, aldri hardkodet
- $200/mnd gratis kreditt dekker behovet (~5 kall/uke)
- PII-sanering: `redact_contact_details` → `redact_reviewer_identity` i denne rekkefølgen

### 2. Schema.org Event-skraper (`schema_events.py`)
- Parser JSON-LD `<script type="application/ld+json">` fra offentlige sider
- Bruker SourcePolicy for URL-validering og egress-kontroll
- Returnerer SourceDocument med strukturert event-tekst

### 3. Google Trends-adapter (`google_trends.py`)
- Bruker `pytrends` (uoffisielt) for regional søkeinteresse
- Wrappet med fixture-fallback slik at pipelinen aldri krasjer ved pytrends-feil
- Valgfri avhengighet: `pip install teateret-brief[google]`

## Nøkkelbeslutninger

### Hvorfor `MarketObservation` er separat fra `SalesObservation`
- `SalesObservation` representerer interne, verifiserte driftstall fra GastroPlanner
- `MarketObservation` er eksterne markedssignaler med lavere konfidensgrad
- Separasjonen gjør det klart i briefen og manifestet hvilke data som er interne vs. eksterne

### Hvorfor adapter-mønster fremfor direkte API-kall
- Konsistens med `SafeHttpFetcher`/`FixtureFetcher`-mønsteret
- Fixture-first: Alle adaptere har en `Fixture*`-klasse for offline testing
- Isolert feilhåndtering: Én Google-kilde som feiler stopper ikke pipelinen

### Hvorfor pytrends er akseptabelt
- Det er den eneste frie tilgangen til Google Trends-data
- Vi wrapper det med try/except og fixture-fallback
- Ved API-endring logges feilen som `source_failed`, men briefen genereres fortsatt

### PII-håndtering av Google Reviews
- Redaksjonsrekkefølge: E-post/telefon maskeres **først**, deretter forfatternavn
- Maks 20 anmeldelser per sted (konfigurerbart)
- Aggregerte sentimenttall lagres, ikke individuelle anmeldelser

## Konsekvenser

- **Positiv:** Ledelsen får ukentlig markedsinnsikt uten manuell innsats
- **Positiv:** Fixture-modus fungerer uten API-nøkler
- **Negativ:** pytrends kan bryte ved Google-endringer (mitigert av fallback)
- **Negativ:** Google Places API krever gratis Google Cloud-prosjekt
