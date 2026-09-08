---
title: "teateret-beslutningsbrief architecture handoff"
date: 2026-08-19
status: implemented
tags: [architecture, handoff, workflow_multi_agent]
category: architecture
chunk_type: handoff
---

# Formål

Fastlegge kontrakten for den lokale beslutningsbriefen. Den realiserte arkitekturen er dokumentert i `docs/architecture.md`.

# Selected Variants

- architecture: `sequential_handoff`
- agent pack: `coordinator_specialists`
- codebase profile: `python_service`

# Runtime-grense

Én eksplisitt CLI-kjøring leser repo-bundne input, produserer én run-mappe og gjør ingen eksterne handlinger. Live-modus er deaktivert.

# Input

- runtime- og kildekonfigurasjon;
- godkjente lokale fixtures eller allowlistede HTTPS-kilder;
- aggregert CSV som følger eksplisitt mapping;
- run-ID og modus fra CLI.

# Output

- `brief.md`, `brief.html`, `email.txt` ved godkjent/warning-run;
- `manifest.json`, `events.json` og eventuelt `errors.json`;
- ingen e-postsending, publisering eller ekstern state.

# State

Kun run-avgrensede filer: status, tidsstempel, input-/output-hasher, kildebevis, modellbruk, advarsler og stoppgrunn.

# Steg

Valider → hent/normaliser → kildeleser → deterministisk salgssammendrag → analytiker → kontrollør → PII-port → render/manifest.

# Godkjenning og stopp

Menneskelig godkjenning kreves før utsending. Ingen kilder, policybrudd, ukjente ID-er, kontrollør-avslag eller budsjettbrudd stopper artefaktene.

# Evaluering og spor

Syntetiske fixtures skal dekke samme kontrakter hver gang. Manifestet skal forklare kilder, modellbruk, status og filer uten rådata.

# Handoff

Implementert og testet offline. Neste eier trenger bare anonymisert eksport, kildeliste og kundens beslutningsspørsmål.
