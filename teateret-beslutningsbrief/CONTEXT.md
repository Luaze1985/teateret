---
title: "Kontekst for Teateret beslutningsbrief"
date: 2026-08-19
status: active
tags: [context, teateret, pilot]
category: project
chunk_type: context
---

# Nåværende tilstand

Repoet inneholder en lokal, privat prototype for en ukentlig beslutningsbrief til Teaterets ledelse. Demoen er testbar uten nettverk eller modell. Live-koden finnes, men er opt-in og skal ikke brukes på ekte data før avtalte personvern- og sikkerhetspunkter er lukket.

# Domenebegreper og glossary

- **Beslutningsbrief**: Ukentlig, aggregert rapport (Markdown/HTML/e-postutkast) til Teaterets ledelse med innsikt i program, kapasitet, kryssalg og markedsføring.
- **Claude LLM (Synteserolle)**: Sikker, deterministisk strukturert modell som analyserer ferdig validerte aggregater. Modellen har ingen direkte nettverkstilgang, verktøytilgang eller tilgang til rådata.
- **Deterministisk rør**: Rørledning der all innhenting, validering, aggregering og PII-sanering skjer i kode (Python/DuckDB) før modellvurdering.
- **MCP (Model Context Protocol)**: Protokoll for verktøy- og ressursdeling. Vurderes som mulig framtidig bro dersom GastroPlanner eller lokale datakilder tilbyr sikre MCP-grensesnitt for ad-hoc analyse.
- **GastroPlanner-kobling**: Integrasjonsflaten mot Teaterets restaurant- og arrangementssystem (CSV-eksport, REST-API eller eventuell webhook/MCP).
- **Koblingskompleksitet**: Graden av vanskelighet og risiko ved å koble arrangementsdata og restaurantdata. Nivå 1 (stabil felles ID), Nivå 2 (tittel + dato + rom heuristikk), Nivå 3 (uforenlige tidsvinduer/ufulle datasett).

# Beslutninger

- Første nytte er bedre program- og markedsbeslutninger, ikke automatisert publisering.
- Første GastroPlanner-kobling er aggregert CSV, ikke uverifisert API.
- Kun godkjente kilder; ingen generell «lytning til alt som sies».
- Tre smale roller med faste overleveringer; ingen fri agentflokk.
- E-post er et usendt utkast. En ansatt er alltid siste kontrollpunkt.
- Fase 1 skal være liten nok til å selges og leveres som en pilot rundt 10 000 kroner. Produksjonsintegrasjon prises separat.

# Åpne spørsmål før ekte pilot

- Hvilke eksportfelt tilbyr GastroPlanner-kontoen faktisk?
- Tilbyr GastroPlanner et åpent REST-API eller MCP-grensesnitt for Teateret?
- Bruker Teateret Microsoft 365, Google Workspace eller noe annet for e-post og filer?
- Hvilke 5–10 kilder ønsker Amir og markedsansvarlig å følge?
- Hvem eier ukentlig godkjenning, og hvor lenge skal kjøringsdata beholdes?
- Hvilke tre beslutninger skal briefen faktisk gjøre lettere?

