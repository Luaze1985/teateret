---
title: "teateret-beslutningsbrief production readiness checklist"
date: 2026-08-19
status: prototype-only
tags: [readiness, checklist, workflow_multi_agent]
category: delivery
chunk_type: checklist
---

# Produksjonsklarhet

Offline-prototypen er ferdig. Punktene under er bevisst åpne før bruk av ekte data eller automatisk drift.

## Workspace

- [x] Workspace-struktur og variantfiler er validert lokalt.
- [x] Input, output og kjøringsmapper er skilt.
- [ ] Ekte kilder og anonymisert eksport er godkjent av Teateret.

## Architecture

- [x] Input-, output- og rollekontrakter er eksplisitte.
- [x] Menneskelig kontroll og stoppgrenser er eksplisitte.
- [x] E-post, scheduler, dashboard og sosial lytting er utenfor kjernen.

## Evaluation

- [x] Offline sikkerhets- og flyttester finnes.
- [x] Promptfoo/Ragas er vurdert og ikke nødvendig i fase 1.
- [ ] Et menneskelig evaluert, anonymisert kundesett finnes.

## Observability

- [x] Lokale trace-hendelser, manifest og output-hasher finnes.
- [x] Kildefeil, blokkering og fallback er gjennomgåbare.
- [ ] Produksjonsovervåking, varsling og backup er avtalt.

## Personvern og drift

- [ ] Databehandleravtale, behandlingssted og lagringstid er avklart.
- [ ] E-postidentitet og mottaker-allowlist er konfigurert.
- [ ] Kill switch, tilgangsstyring og recovery er testet i valgt sky.
- [ ] Navngitt Teateret-ansatt har godkjent fireukers pilot.
