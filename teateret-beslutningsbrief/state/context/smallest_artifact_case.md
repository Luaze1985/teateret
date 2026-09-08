---
title: Smallest artifact case form
date: 2026-08-19
status: draft
tags:[template, simonw, case-form, artifact-first]
category: architecture
chunk_type: template
---

# Sak

Offline beslutningsbrief fra syntetiske markedssignaler og aggregert salg.

# Spørsmål

Kan vi produsere et nyttig, kontrollerbart lederutkast uten kundedata, automatisk sending eller stor plattform?

# Minste nyttige artefakt

- primærartefakt: `brief.md` med kilde-ID-er og anbefalinger;
- tillegg: HTML, usendt e-postutkast og manifest;
- nok fordi dette tester nytte, kontroll og arbeidsflyt før integrasjon.

# Input

- syntetiske lokale kilder;
- syntetisk aggregert GastroPlanner-lignende CSV;
- eksplisitt runtime- og kildemapping.

# Modellkontekst

- må inkludere: normalisert tekst, kilde-ID og deterministisk salgssammendrag;
- støy: navigasjon, skript, rå HTML og duplikater;
- ekskludert: kundedata, secrets, lokale filer og eksterne instruksjoner.

# Arbeidsflyt

- hent og valider kilder og CSV;
- kjør tre faste, strukturerte roller;
- valider referanser og persondatagater;
- render artefakter og skriv manifest;
- menneskelig review før enhver bruk.

# Validering

- enhets- og integrasjonstester;
- offline demokjøring;
- harness-validator og separat krav-/sikkerhetsreview.

# Stoppbetingelser

- ingen lesbare godkjente kilder;
- ukjente referanser eller avslag fra kontrollør;
- persondata, budsjettbrudd eller path/network-policybrudd.

# Menneskelig review

- reviewer: Lars i demo, deretter navngitt Teateret-ansatt;
- signoff: alltid før utsending eller handling;
- grense: systemet gir råd, men gjør ikke endringer.

# Neste steg

Kjør et avgrenset arbeidsmøte med faktisk bruker, tilpass anonymisert eksport og avtal fire ukers pilot.
