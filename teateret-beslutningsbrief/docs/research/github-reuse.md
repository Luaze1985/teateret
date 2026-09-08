---
title: "GitHub-gjenbruk vurdert for Teateret"
date: 2026-08-19
status: researched
tags: [github, open-source, architecture]
category: research
chunk_type: findings
---

# Konklusjon

Ingen restaurant- eller teaterpakke bør bli kjernen i piloten. Teateret har allerede billett-, restaurant- og publiseringssystemer. Vi gjenbruker små, modne byggeklosser og lar eksisterende systemer være kilder til sannhet.

# Aktuelt å gjenbruke

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework): mulig produksjonsretning hvis Teateret bruker Microsoft 365/Azure. Workflows, kontrollpunkter og menneskelig godkjenning passer behovet, men er unødvendig tungt i offline-piloten.
- [changedetection.io](https://github.com/dgtlmoon/changedetection.io): aktuelt i fase 2 for endringer på en liten liste godkjente arrangementsider. Må avgrenses mot vilkår, robots, feilsignaler og prompt-injection.
- [DuckDB](https://github.com/duckdb/duckdb): valgfri, lokal analyse av CSV/Parquet. Koden faller tilbake til vanlig Python i piloten.
- [Trafilatura](https://github.com/adbar/trafilatura): valgfritt bedre tekstuttrekk fra nettsider. Standardbiblioteket er fallback.
- [Activepieces](https://github.com/activepieces/activepieces): mulig rask orkestrering senere, men Community Edition har svakere tilgangs- og revisjonsfunksjoner enn ønsket for kundedata.
- [Metabase](https://github.com/metabase/metabase): mulig dashboard når en e-postbrief ikke er nok. Ikke nødvendig i første leveranse.

# Kun inspirasjon

- [pretix](https://github.com/pretix/pretix) har en god arrangement-/ordre-modell, men skal ikke erstatte Tixly.
- [TastyIgniter](https://github.com/tastyigniter/TastyIgniter) viser restaurantdomener, men skal ikke parallellføre GastroPlanner.
- [Huginn](https://github.com/huginn/huginn) kan samle signaler, men gir mer gammel og kompleks driftsflate enn piloten trenger.
- [RSSHub](https://github.com/DIYgod/RSSHub) kan normalisere enkelte åpne feeds, men tredjepartsruter kan knekke og må behandles som ustabile.

# Bevisst avvist i fase 1

- «Fri agentflokk» med verktøy og selvvalgte mål.
- Generell overvåking av Facebook, Instagram eller TikTok uten offisiell tilgang.
- Nytt CRM, billettsystem, restaurantplattform eller datavarehus.
- AutoGen for nybygg; Microsoft anbefaler nyere Agent Framework.

Researchen er et teknisk beslutningsgrunnlag, ikke en lisensjuridisk gjennomgang. Versjoner, lisenser og driftsvilkår må verifiseres igjen før produksjonsvalg.
