---
title: "teateret-beslutningsbrief Codex handoff"
date: 2026-08-19
status: active
tags: [codex, handoff, workflow_multi_agent]
category: architecture
chunk_type: handoff
---

# Formål

Gi neste Codex-tråd et smalt og sikkert arbeidsmønster.

# Selected Variants

- architecture: `sequential_handoff`
- agent pack: `coordinator_specialists`
- codebase profile: `python_service`

# Start-of-Thread Checklist

1. Les `AGENTS.md`, `CONTEXT.md` og `README.md`.
2. Les `state/context/working_context.md` og relevant oppgave.
3. Bekreft at live-modus fortsatt er deaktivert før endringer.
4. Avgrens én artefakt eller testhypotese.

# Write Scope Rules

- arbeid bare i repoet;
- ikke les ekte kundedata eller secrets;
- ingen installasjon, live-kall, sending, deploy, commit eller push uten godkjenning;
- oppdater kontekst ved endrede beslutninger.

# Validation Rules

```powershell
python -m unittest discover -s tests
```

Replace or extend the command set if the workspace needs additional validation.

Kjør også `python -m pytest`, `python -m compileall -q teateret_brief tests scripts` og `python scripts\validate_workspace.py`.

# Failure Handling

Stopp ved policybrudd, tvetydig dataeierskap, behov for ekte kundedata eller endring utenfor repoet. Skriv en kort blokkering med neste sikre steg.

# Done Criteria

Endringen er avgrenset, testbevis finnes, dokumentasjonen er konsistent og live-/menneskeportene er bevart.
