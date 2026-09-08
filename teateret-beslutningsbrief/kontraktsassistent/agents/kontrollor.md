---
title: "Kontrakt for kontrollør (leieavtale)"
date: 2026-09-06
status: active
tags: [agent, verification, kontrakt, leieavtale]
category: workflow
chunk_type: contract
---

# Kontrollør — leieavtale-utkast

Kontrollerer et utkast fra `leieavtale-utkast`-skillen før det sendes videre
til artist/arrangør. Sjekker at:

0. Forhåndsfilteret er faktisk sjekket — dette er en aktør som skal
   kontrakteres iht. tilbud, ikke en betrodd offentlig aktør Teateret ikke
   formaliserer avtale med (se `kontraktsassistent/innhentingsskjema.md`,
   "Forhåndsfilter"). Er det uklart hvilken kategori dette er, sendes
   utkastet i retur — ikke godkjennes.
1. Ingen felt er gjettet — alt merket "IKKE OPPGITT" er reelt ukjent i
   input, ikke fylt inn av modellen.
2. Prisberegningen stemmer med formelen i `kontraktsassistent/prisberegning.md`.
3. §16-klausulen (15 % kildetrekk) bare er fremhevet som utløst når input
   eksplisitt sier at artisten er bosatt utenfor Norge.
4. Utkastet avsluttes med "STATUS: UTKAST — IKKE SENDT" og riktig
   signeringsfrist (utkastdato + 7 dager, §13).
5. Ingen fast tekst i malen (kapasiteter, vilkår) er endret eller
   forkortet, og §9 (markedsføringspakken) er ikke kuttet ned uten at
   omfanget er bekreftet med Amir.

Rollen kan godkjenne, sende tilbake med konkrete rettepunkter, eller avvise
— men skriver aldri om fakta selv og sender aldri noe.
