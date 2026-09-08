---
title: "Review: formålet med piloten"
date: 2026-08-19
status: draft
tags: [review, pilot, purpose, ask-matt]
category: review
chunk_type: findings
---

# Funn

## 1. Formålet er formulert fire ulike steder, med fire ulike løfter

- `CONTEXT.md`: «Første nytte er bedre program- og markedsbeslutninger, ikke automatisert publisering.»
- `state/context/use_case_brief.md`: «ukentlig, kildebelagt brief om programtrender og egne aggregerte salgssignaler».
- `docs/implementation-plan.md`: «kort, kildebelagt ukesutkast … Piloten skal passe inn i e-postarbeidsflyten, men ikke sende selv.»
- `state/context/smallest_artifact_case.md`: «Kan vi produsere et nyttig, kontrollerbart lederutkast uten kundedata …?»

Bare den siste er falsifiserbar, og den spør om maskineriet — ikke om Teaterets beslutninger.
Formålet er i praksis definert som «produsere en brief», ikke «gjøre beslutning X lettere».

## 2. Hullet er allerede navngitt i repoet, men ikke lukket

`CONTEXT.md` under «Åpne spørsmål før ekte pilot»: *«Hvilke tre beslutninger skal briefen faktisk gjøre lettere?»*

Dette spørsmålet er bærende. Uten svar har `docs/implementation-plan.md` sitt
måleopplegg — «kjør fire ukentlige utkast og mål lesetid, redigeringsbehov og
handlinger» — ingen suksesskriterium. Man kan ikke måle om en brief førte til en
bedre beslutning når beslutningen ikke er navngitt. De samme stoppkriteriene
(«ikke fører til bedre beslutninger») er da heller ikke testbare.

## 3. Demo-outputen viser hullet konkret

`runs/demo-verification/brief.md`:

> rec-1: Vurder om det ferskeste lokale signalet bør møtes med et avgrenset program- eller markedstiltak.
> Forventet verdi: Gi Amir ett konkret tiltak å vurdere

Det er en anbefaling om å vurdere å vurdere noe. Dette er fixture-sporet uten
modellkall (`"model": "fixture-no-model"` i `runs/demo-verification/manifest.json`),
så prosaen vil bli bedre med en levende modell. Men *formen* kommer fra
`agents/analytiker.md`, som krever «maksimalt tre konkrete handlinger … forklare
forventet verdi og angi innsats» uten å si hvilken klasse beslutninger de skal
mate. En modell fyller malen med bedre språk; den fyller ikke inn den manglende
beslutningslisten.

## 4. Resten av repoet er konsistent og i god stand

Sikkerhetsgrenser, rollekontrakt, stoppbetingelser og menneskelig kontrollpunkt
sier det samme i `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/data-policy.md` og
`outputs/production-readiness-checklist.md`. Live-modus er sperret bevisst.
Ingen motsetninger funnet der. Fase 1 er bygget.

# Anbefalt neste steg

`/grill-with-docs`, avgrenset til ett spørsmål: **hvilke tre beslutninger skal
briefen gjøre lettere?**

Grunn: det finnes en kodebase og en `CONTEXT.md` med levende beslutnings- og
åpne-spørsmål-seksjoner — nettopp den flaten skillen vedlikeholder. Blokkeringen
ligger oppstrøms for kode, så `/to-spec` og `/implement` er feil. `/research` er
også feil: GastroPlanner-eksport og M365-vs-Workspace besvares ved å spørre
Teateret, ikke ved å lese primærkilder.

De fire andre åpne spørsmålene i `CONTEXT.md` (eksportfelt, e-postplattform,
kildeliste, eierskap/lagringstid) er logistikk og kan avklares i samme
kundesamtale.

# Ikke besvart her

Hvilke tre beslutninger det faktisk er. Repoet inneholder ingen input fra
Teateret; alt jeg skriver om det ville vært oppspinn i review-form.
