---
title: "Bygg offline beslutningsbrief"
date: 2026-08-19
status: completed
tags:[task, workflow]
category: task
chunk_type: task-definition
---

# Mål

Bygg en testbar offline-prototype med syntetiske kilder, aggregert salg, tre faste roller og usendte artefakter.

# Kontekst

Oppgaven beviser arbeidsflyt og sikkerhetsgrenser før ekte GastroPlanner-data, modellkall, e-post eller skydrift.

# Input

- godkjent møte-/pilotplan fra Lars;
- canonical agentic workspace-harness i Hjernen;
- GitHub-vurdering dokumentert i `docs/research/github-reuse.md`.

# Acceptance Criteria

- [x] Offline-kjeden og artefaktene er implementert.
- [x] Strukturen følger `workflow_multi_agent` og `sequential_handoff`.
- [x] Tester, compileall, demo og lokal workspace-validator er kjørt.
- [x] Dokumentasjon og produksjonsgrenser er skrevet.

# Expected Output

- opprettet: Python-pakke, konfigurasjon, fixtures, tester og dokumentasjon;
- oppdatert: harness-kontekst og arbeidsflytkontrakter;
- neste: anonymisert eksport og kundegodkjent kildeliste.

# Verification

- kommandoer: se `README.md`;
- bevis: grønn testkjøring og `runs/final-verification*` lokalt;
- risiko: live-modus og leverandørintegrasjoner er ikke produksjonstestet.
