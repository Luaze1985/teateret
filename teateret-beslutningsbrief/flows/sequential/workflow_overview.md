---
title: "teateret-beslutningsbrief workflow overview"
date: 2026-08-19
status: draft
tags:[workflow, plan, workflow_multi_agent]
category: architecture
chunk_type: template
---

# Mål

Produsere et kort, kildebelagt og usendt beslutningsutkast fra godkjente markedskilder og aggregert salgsdata.

# Roller

- kildeleser: identifiserer signaler med kilde-ID;
- analytiker: foreslår maksimalt tre handlinger;
- kontrollør: godkjenner eller stopper grunnlaget;
- pipeline: validerer og renderer deterministisk.

# Rekkefølge

1. Valider konfigurasjon, filstier og aggregert CSV.
2. Hent hver godkjente kilde isolert.
3. Kjør kildeleser med strukturert output.
4. Summer salg deterministisk og kjør analytiker.
5. Kjør kontrollør og valider alle referanser.
6. Skann output for direkte personopplysninger.
7. Skriv usendte artefakter og revisjonsmanifest atomisk.

# Kontroller

- menneskelig kontroll kreves før all utsending;
- kildefeil gir advarsel, ingen kilder gir blokkert kjøring;
- modellfeil får høyst ett retry;
- kall-, token- og inputgrenser stopper videre modellbruk;
- manifest og hendelser skrives for hver kjøring.
