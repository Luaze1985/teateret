---
title: "teateret-beslutningsbrief evaluation model"
date: 2026-08-19
status: active
tags: [eval, workflow_multi_agent]
category: architecture
chunk_type: process
---

# Formål

Bekrefte at samme input gir samme datagrunnlag, at agentoverleveringer følger skjema, og at usikre eller sensitive resultater stoppes.

# Selected Variants

- architecture: `sequential_handoff`
- agent pack: `coordinator_specialists`
- codebase profile: `python_service`

# Evalueringsgrense

Fase 1 evaluerer offline-kjeden fra syntetisk kilde/CSV til tre usendte artefakter og manifest. Ekte markedskvalitet evalueres først med en menneskelig godkjent testpakke.

# Promptfoo

Ikke brukt i fase 1. Pydantic-kontrakter, mockede modellresponser og `unittest` dekker den lille prototypen. Promptfoo vurderes når et fast sett virkelige, anonymiserte eksempler finnes.

# Ragas

Ikke brukt: dette er ikke en RAG-løsning. Innføres bare dersom senere versjon henter svar fra en varig kunnskapsbase.

# Lagret bevis

- testresultat fra `unittest` og `pytest`;
- syntetisk demo under git-ignorert `runs/<id>/`;
- manifest med kilder, hasher, modellbruk og status;
- menneskelig vurdering av korrekthet, redigeringsbehov og faktisk nytte i pilot.

# Godkjenningsport

Alle tester og workspace-validatoren er grønne; ingen direkte personopplysninger; alle råd har gyldig kilde-ID; kontrollør har ikke avvist; artefaktene er tydelig usendt utkast.
