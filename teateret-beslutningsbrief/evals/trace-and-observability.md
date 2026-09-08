---
title: "teateret-beslutningsbrief trace and observability model"
date: 2026-08-19
status: active
tags: [trace, observability, workflow_multi_agent]
category: architecture
chunk_type: process
---

# Formål

Gjøre hver kjøring forklarbar uten å lagre rå nettsidetekst, CSV-rader, prompts eller hemmeligheter.

# Selected Variants

- architecture: `sequential_handoff`
- agent pack: `coordinator_specialists`
- codebase profile: `python_service`

# Sporingslag

Lokal JSON i `runs/<run-id>/manifest.json`, `events.json` og ved behov `errors.json`. Ingen ekstern tracing i fase 1.

# Påkrevde hendelser

`run_started`, kildeforsøk/suksess/feil, rolle start/fullført/feil, output skrevet, PII-scan og endelig `run_completed`, `run_warning` eller `run_blocked`.

# Metadata

Run-ID, tider, status/stoppgrunn, config- og promptversjon, input-hash, kildestatus, kilde-URL/tid/hash, modell, kall/retry/tokens, output-hasher og advarsler.

# Kobling til validering

Run-ID finnes i alle tre artefakter og manifest. Output-hashene gjør det mulig å kontrollere filene mot kjøringen.

# Feilregel

Mangler manifest, kildeoversikt, output-hash eller stoppgrunn, er kjøringen ikke leverbar. Logger med rådata eller hemmeligheter skal behandles som en sikkerhetshendelse.
