---
title: "Kontraktsassistent — quick wins uten KI"
date: 2026-09-06
status: draft
tags: [quick-wins, leieavtale, ingen-ki]
category: research
chunk_type: overview
---

# Kontraktsassistent — quick wins uten KI

Dette er ren prosess/skjema-forenkling for leieavtale-workflowen, ingen
språkmodell involvert. Den KI-baserte delen (utkast fra limt-inn e-post)
ligger som en skill i `.agents/skills/leieavtale-utkast/SKILL.md` — i
repoet, ikke som en personlig Claude-konto-skill, slik at den følger
kundeprosjektet uansett hvem som jobber i det. Se
`docs/research/kontrakt-automatisering-vurdering.md` for helhetsbildet.

## Filer

- `innhentingsskjema.md` — de 6-7 feltene som faktisk varierer per kontrakt.
  Send/bruk dette i stedet for å plukke info ut av en e-postkjede.
- `sjekkliste-frister.md` — de tre fristene i avtalen som gir Teateret reell
  risiko hvis de glipper.
- `prisberegning.md` — formelen for totalpris, depositum og
  avbestillingskostnad, så den ikke regnes for hånd hver gang.
- `agents/kontrollor.md` — sjekker et utkast fra `leieavtale-utkast`-
  skillen før det sendes videre (ingen gjettede felt, riktig pris, riktig
  frist). Samme "kontrakt for en rolle"-format som `agents/kontrollor.md` i
  resten av repoet, men for denne oppgaven.

## Hvorfor egen mappe

Dette er ikke en del av `teateret_brief`-pipelinen (annen kunde-oppgave, se
vurderingen). Egen mappe holder det synlig som et selvstendig, lite
forbedringssett som kan tas i bruk uavhengig av resten av repoet.
