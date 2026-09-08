---
title: "Repo-vurdering mot masterprompt (ORIGINAL_REQUEST.md)"
date: 2026-09-06
status: draft
tags: [vurdering, masterprompt, ai-arkitektur, tester]
category: research
chunk_type: assessment
---

# Repo-vurdering mot masterprompt

Masterprompten her er `ORIGINAL_REQUEST.md` — den originale spesifikasjonen
som ble brukt til å bygge `teateret_brief`-pipelinen (ikke leieavtale-PDF-en,
se forrige notat). Vurderingen er gjort ved å lese spesifikasjonen opp mot
faktisk kode, kjøre `pytest`, `compileall` og demo-modus, og lese ADR-ene
som styrer AI-arkitekturen.

**Kontrollert i denne økten:** kjørt i en midlertidig Linux-sandkasse
(ikke Lars sin faste Windows-utviklingsmiljø), med avhengigheter
installert fra `pyproject.toml`. Ingenting i repoet er endret eller
committet — kun lest og kjørt.

## A. Krav-for-krav mot masterprompten

| Krav | Status | Merknad |
|---|---|---|
| R1 — GastroPlanner-innlesing, PII-fritt, streng typing | **Delvis** | Kolonnevalidering er streng (avviser ukjente kolonner korrekt). Men numerisk validering slipper gjennom tomme felt, mellomrom og «N/A» — bekreftet av 3 feilende tester (`test_numeric_invalid_boundaries_rejected`). |
| R2 — 3-nivå event-matching mot 129 arrangementer | **Delvis / dokumentasjonsavvik** | Koden (`matcher.py`) følger masterpromptens rekkefølge (nivå 2 = tittel+dato+rom, nivå 3 = nærhet). Men `docs/adr/0002` beskriver nivåene i **motsatt rekkefølge** i selve teksten. Kode og eget ADR er ikke enige med hverandre. En test for nivå 2-romdisambiguering feiler også. |
| R3 — MET.no vær, Agder skoleferie, byarrangementer | **Ikke levert som spesifisert** | Ingen kode for MET.no eller skoleferiekalender finnes i `teateret_brief/`. I stedet er det bygget Google Places, Google Trends og schema.org-skraping (`docs/adr/ADR-0004-google-datakilder.md`) — andre, mer avhengighetstunge kilder (uoffisiell `pytrends`, Google API-nøkkel) enn det som ble bedt om. Dette ser ut som en beslutning tatt underveis i byggingen, ikke noe som er bekreftet tilbake mot deg eller Amir. |
| R4 — Rendering + sikkerhetsrevisjon | **Fungerer, men med reelle hull i "streng scanner"** | Demo-kjøring produserer `brief.md/html/email.txt` + manifest med hash og `pii_scan_status: pass`. Men egne adversarial-tester viser: kredittkort-skanneren fanger ikke Amex-format (`3782 822463 10005`), og en header kalt «Passord» slipper gjennom hemmelighets-filteret. |
| Automatisert testsuite 100 % grønn | **Nei, akkurat nå rød** | `python -m pytest`: **10 FAILED + 4 SUBFAILED** av totalt over 100 tester. Se detaljer under. `compileall`: ingen feil (syntaktisk OK). |

## B. Konkrete testfunn (kjørt, ikke antatt)

Sikkerhetsrelevante (høyest prioritet):

- **Kredittkort-skanner** mister Amex-formatet (`3782 822463 10005`) — reell risiko for R1/R4s "zero PII"-krav hvis noen limer inn kortnummer i fritekst.
- **Hemmelighets-filter** slipper gjennom en header kalt «Passord» — filteret er ikke robust mot norsk variant av «password».
- **Path-traversal-beskyttelse** stopper Unix-stiler (`../escape.txt`) men **ikke** Windows-stiler (`allowed\..\..\escape.txt`, `C:/Windows/System32/calc.exe`). Siden dette faktisk kjører på din Windows-maskin, er dette den mest presserende av de tre.
- **SSRF-guard**: blokkerer faktisk privat IP (127.0.0.1) — testen feiler bare fordi feilmeldingsteksten er endret ("Kilden ga en ugyldig IP-adresse" i stedet for forventet tekst). Selve beskyttelsen ser ut til å virke; dette er trolig en utdatert test, ikke et sikkerhetshull.

Data/scenario:

- 3 numeriske grensetester feiler (tom streng, mellomrom, «N/A» godtas der de skal avvises).
- 3 av 4 "virkelighetsscenario"-tester feiler (`dark_weekday_gap`, `school_holiday_matinee_surge`, `city_clash_storm_event`). Den jeg sjekket i detalj feiler pga. en ufullstendig kolonne-mapping i selve testen (mangler `Bordreservasjoner`/`Pakkemenyer` i mappingen) — altså trolig en test-bug, ikke nødvendigvis en produksjonsfeil. De to andre er ikke rotårsakssjekket like grundig; anta samme kategori til noen faktisk går gjennom dem.

## C. Vurdering av AI-løsningen (arkitekturen, ikke bare koden)

**Det som er en god beslutning og bør bevares:**

- To-trinns mønster (ADR-0001): Claude kalles kun som en ren synteserolle på ferdig validerte, PII-sanerte aggregater — ingen verktøytilgang, ingen nettverkstilgang, ingen rå kundedata. Dette er riktig arkitektur for denne bruken og bør ikke bygges om.
- Tre smale, verktøyløse roller med fast rekkefølge og Pydantic-kontrakter: konservativt og revisjonsvennlig — riktig avveining for en beslutningsstøtte-pilot, ikke en "fri agentflokk".

**Det som bør rettes opp før piloten går videre:**

- ADR-0002s tekst må rettes slik at den faktisk beskriver det koden gjør — akkurat nå motsier repoets eget arkitekturdokument koden.
- R3-kildevalget (Google Places/Trends i stedet for MET.no/skoleferie/byarrangementer) er en reell forretningsbeslutning som bør bekreftes eksplisitt med deg/Amir, ikke stå som en stille endring fra spesifikasjonen. Google-sporet krever API-nøkkel, gratiskreditt-avhengighet og en uoffisiell bibliotek (`pytrends`) — mer skjørt enn det opprinnelige forslaget.
- `pyproject.toml` krever Python ≥3.11; sandkassen her har 3.10 og fungerte likevel, men bør verifiseres på din faste maskin — hvis det faktisk kreves språkfunksjoner fra 3.11 et sted, bør det testes eksplisitt.

## D. Svar på "veien videre" — repo eller Claude Code

Konklusjonen er ikke et enten/eller. Selve AI-arkitekturen (to-trinns Claude-mønster, smale roller) er riktig og bør ikke kastes eller bygges om fra bunnen via løse Claude Code-økter — det ville mistet nettopp den reproduserbarheten og revisjonssporet som er poenget med piloten.

Det som trengs nå er en **stabiliseringsrunde**, ikke mer funksjonsbygging:

1. Rett de tre sikkerhetsrelevante testfunnene (kredittkort, hemmelighets-filter, Windows-path-traversal).
2. Rett ADR-0002-teksten så den stemmer med koden.
3. Ta en eksplisitt beslutning på R3: behold Google-sporet (og oppdater masterprompten/README til å reflektere det), eller bygg MET.no/skoleferie som opprinnelig spesifisert.
4. Commit repoet til git — fortsatt null commits. Med reelle, identifiserte feil å rette er dette mer presserende enn sist gang jeg nevnte det. *Gjør jeg ikke uten din bekreftelse, jf. `AGENTS.md`.*

Dette er nettopp den typen avgrensede, testbare rettejobb Claude Code er godt egnet til — fordi testsuiten allerede finnes og kan verifisere at rettingene faktisk virker. Så: bruk Claude Code (eller en økt som denne) til å gjøre stabiliseringsrunden i #1-3 over, men innenfor den eksisterende arkitekturen — ikke som en erstatning for den.

## Må verifiseres

- Er R3-kildevalget (Google vs. MET.no/skoleferie) forankret hos Amir, eller var det en beslutning tatt underveis i byggingen?
- Kjører testsuiten grønt på din faste Windows-maskin, eller reproduseres de samme 14 feilene der?
- Skal repoet committes nå, gitt at det står med reelle, udokumenterte feil?
