---
title: "Handoff: Stabiliseringsrunde før pilot (task 002)"
date: 2026-09-06
status: draft
tags: [handoff, stabilisering, tester, sikkerhet]
category: handoff
chunk_type: handoff
---

# Handoff — Stabiliseringsrunde (task 002)

Utført av en Claude Code-økt på Lars sin faste Windows-maskin
(**Python 3.11.9**, ikke Linux-sandkassen fra forrige vurdering). Isolert
`.venv` opprettet i repoet (allerede i `.gitignore`); deklarerte
avhengigheter fra `pyproject.toml` installert for å kunne kjøre testene.
**Ingen commit eller push er gjort.** Ingen nye eksterne kilder,
avhengigheter eller nettverkskall er lagt til i koden.

## Sammendrag

| | Før (Linux-sandkasse) | Etter (Windows 3.11) |
|---|---|---|
| `pytest` | 10 FAILED + 4 SUBFAILED | **1 FAILED**, 261 passed, 335 subtests passed |
| `compileall` | OK | OK (exit 0) |
| `validate_workspace` | kun frontmatter-advarsler | kun frontmatter-advarsler, ingen feil |

Det ene gjenværende røde er `test_google_places_fixture_adapter`, som ligger
i R3/Google-sporet bestillingen eksplisitt fryser — begrunnet under punkt B.

## Viktigste funn

To ting avvek fra bestillingens antakelser og er verdt å merke seg:

1. **Punkt 3 (Windows path-traversal) var ikke en reell feil på Windows.**
   `test_repopaths_traversal_attacks` **passerer** på Python 3.11 her. Feilen
   i vurderingen var et Linux-sandkasse-artefakt: på Linux tolkes `\` som et
   vanlig filnavntegn, ikke separator, så `allowed\..\..\escape.txt` ble sett
   som ett filnavn inne i root. På Windows er `\` separator og `RepoPaths`
   blokkerer allerede alle seks angrepene. **Ingen produksjonskode endret** —
   å skrive en OS-uavhengig normaliserer inn i sikkerhetskritisk stikode uten
   en feilende test ville vært nettopp den «for bred»-risikoen Verification-
   seksjonen advarer mot. **Residualrisiko (betinget av deploy):** `RepoPaths`
   er repoets path-confinement-grense. Unix-svakheten for `\`-payloads er reell
   og blir en no-op *dersom* noe av dette senere kjøres i Linux (CI, Docker, en
   sky-agent). Ufarlig så lenge kjøring skjer på Windows — men les det som
   «ikke aktuelt på nåværende deploy-mål», ikke «ikke aktuelt». Løftes som eget
   punkt om ønskelig.

2. **Punkt 5 (SSRF) var en reell kodefeil, ikke bare feiltekst.**
   `SourcePolicyError` arver fra `ValueError`. Den bevisste
   «privat eller reservert»-feilen ble derfor fanget av `except ValueError` i
   samme løkke og re-kastet som «ugyldig IP-adresse». Blokkeringen virket
   (feil ble alltid kastet), men med feil melding. Rettingen er en
   kontrollflyt-endring (parse i egen try, `is_global`-sjekk utenfor), ikke en
   tekstjustering — rotårsak var eksception-shadowing.

## Per-punkt status

### 1. Kredittkort-skanner (Amex) — RETTET
- Fil: `teateret_brief/security.py` (`_CREDIT_CARD_RE`).
- Rotårsak: mønsteret dekket ikke Amex 4-6-5-gruppering med separatorer
  (`3782 822463 10005`). 15-sifret Amex uten separator var allerede dekket.
- Fiks: lagt til alternativet `(?<!\d)3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}(?!\d)`.
  Smalt nok (kun 34/37-prefiks, 4-6-5) til ikke å gi falske treff; bredt nok
  til å fange testens Amex-format i både skanning og redaksjon.
- Verifisert: `test_credit_card_scanner_and_redaction` grønn.

### 2. Hemmelighets-/header-filter (Passord) — RETTET
- Fil: `teateret_brief/security.py`.
- Rotårsak: `passord`/`password` fantes ikke i blacklisten.
- Fiks: lagt til `passord`, `password`, `passwd`, `pwd` i
  `_FORBIDDEN_COLUMN_EXACT`, og `passord`/`password` i stammelisten for
  sammensatte headere.
- Verifisert: `test_header_casing_and_separators` (subtest `Passord`) grønn;
  domene-safelisten (`test_domain_safelist_preserved_against_blacklist`)
  fortsatt grønn (ingen gyldige kolonner blokkeres).

### 3. Path-traversal på Windows — IKKE RØRT (testen passerer på Windows)
- Se «Viktigste funn» punkt 1. `test_repopaths_traversal_attacks` er grønn på
  Python 3.11/Windows uten endring. Ingen produksjonskode endret.

### 4. Numerisk validering — RETTET (med en reell spec-konflikt løst)
- Fil: `teateret_brief/csv_adapter.py` (`_parse_number`).
- Rotårsak: tom streng, kun mellomrom og `N/A` returnerte `0.0` i stedet for
  å avvises.
- Fiks: `""`/kun-mellomrom og `N/A`/`n/a` kaster nå `DataPolicyError`.
  Bindestrek (`-`, `–`, `—`) og `null`/`None` beholdes bevisst som «ingen
  verdi = 0» (bestillingen ba spesifikt om tom/mellomrom/N/A — ikke bredere).
- **Spec-konflikt oppdaget og løst:** to eldre enhetstester
  (`tests/test_csv_adapter.py::test_number_parsing_variations` og
  `tests/test_csv_adapter_stress.py::test_whitespace_nbsp_and_currency_tokens`)
  forventet motsatt oppførsel (tom/`N/A` → `0.0`). Disse kodifiserte den
  gamle, lempelige oppførselen som bestillingen nå erstatter (R1 «streng
  typing»). I tråd med regelen «er testen selv feil, rett den eksplisitt og
  forklar hvorfor» er de fire konfliktende casene (`""`, `" "`, `N/A`, `n/a`)
  flyttet fra «→ 0.0» til `assertRaises(DataPolicyError)`, med kommentar i
  testene. Ingen test er slettet eller svekket; alle gyldige tallcase
  (valuta, tusenskille, desimaltegn, dash/null/None) er beholdt. En tredje
  numerisk test i samme fil (`test_invalid_numbers_rejected`) ble sjekket: den
  dekker kun negative/NaN/Inf/ugyldige strenger og overlapper ikke med
  dash/null/None, så det finnes ingen motstridende tredje spec.
- Verifisert: `test_numeric_invalid_boundaries_rejected` (`[]`, `[   ]`,
  `[N/A]`) grønn; begge de oppdaterte enhetstestene grønne.

### 5. SSRF-feiltekst — RETTET (rotårsak: eksception-shadowing)
- Fil: `teateret_brief/security.py` (`SourcePolicy.validate`).
- Se «Viktigste funn» punkt 2. Blokkeringen av private IP-er virket; nå
  returneres også riktig melding («Kilden peker til en privat eller reservert
  adresse»). Genuint ugyldige IP-er kaster fortsatt «ugyldig IP-adresse».
- Verifisert: `test_sourcepolicy_ssrf_and_https_guard` grønn;
  `test_source_policy_ssrf_and_dns` (adversarial, sjekker kun exceptiontype)
  fortsatt grønn.

### 6. Scenario-testene 3/4/5 — RETTET (test-bug, per-test rotårsak)
Rotårsaken ble sjekket per test som bestilt — **ikke antatt samme feil tre
ganger**. Alle tre er samme *kategori* (ufullstendig `CsvMapping` i selve
testen mot en CSV som `create_csv_file` skriver med alle 9 kolonner), men med
ulikt konkret avvik:

- **Scenario 3** (`test_scenario_3_dark_weekday_gap_mitigation`): mappingen
  deklarerte kun `tickets_sold` + `revenue_nok`; CSV-en hadde i tillegg
  `Kapasitet`, `Bordreservasjoner`, `Pakkemenyer`. Med `strict_columns=True`
  (default) avviste `load_aggregated_csv` de tre udeklarerte kolonnene.
- **Scenario 4** (`test_scenario_4_school_holiday_matinee_surge`): manglet
  `Bordreservasjoner` + `Pakkemenyer` i mappingen.
- **Scenario 5** (`test_scenario_5_city_clash_storm_event`): manglet kun
  `Pakkemenyer` i mappingen.
- Fiks (i testfila `tests/e2e/test_tier4_real_world_scenarios.py`): fullførte
  hver mapping så den dekker alle CSV-kolonnene — samme mønster som det
  allerede grønne scenario 2. Dette **beholder** streng kolonnevalidering
  (bedre enn å sette `strict_columns=False`); ingen produksjonskode endret.
- Verifisert: alle tre scenariotestene grønne.

### 7. ADR-0002 vs. kode — RETTET
- Fil: `docs/adr/0002-koblingskompleksitet-og-aksjonerbar-innsikt.md`.
- Rotårsak: teksten beskrev nivå 2 og 3 i motsatt rekkefølge av
  `match_level`-literalen i `teateret_brief/matcher.py`.
- Fiks: nivå 2 = tittel+dato+rom (`level_2_title_date_room`, `matched`),
  nivå 3 = tids-/dato-nærhet (`level_3_proximity`, `needs_review`). Teksten
  peker nå eksplisitt på literalen. **Koden er ikke endret** — den følger
  masterpromptens (`ORIGINAL_REQUEST.md`) definisjon.

## Feil utenfor de 7 punktene, oppdaget på Windows

Baseline på Windows viste to røde tester som **ikke** står i bestillingens 7
oppgaver (begge var trolig del av de opprinnelige 10 på Linux). Begge er
utdaterte testforventninger, ikke kodefeil:

### A. `test_level_2_room_disambiguation` — RETTET (test-bug)
- Rotårsak: autoritativ tittel i `docs/research/arrangementsdata-2025-2026.md`
  (linje 46) er «Kokosbananas – Det store showet **(2 show)**» (12:30 & 14:30).
  Matcheren returnerer eventtittelen ordrett; testen hadde en utdatert
  forventning uten `(2 show)`-suffikset. Selve rom-disambigueringen virker.
- Fiks: oppdatert forventet streng i
  `tests/e2e/test_tier1_feature_coverage.py` til den autoritative tittelen,
  med forklarende kommentar. Eksakt likhet beholdt (ikke svekket til
  delstreng).

### B. `test_google_places_fixture_adapter` — IKKE RØRT (utenfor scope, R3)
- Rotårsak: utdatert testforventning (`place_name == "Teateret"`) mot
  `config/google_places_config.yml` som setter `name: "Teateret Kristiansand"`.
  Trivielt 1-ords test-avvik.
- **Ikke rettet fordi** dette ligger i R3/Google-sporet bestillingen eksplisitt
  fryser i påvente av Lars/Amirs forretningsbeslutning. Å røre R3-tester nå
  kan bli bortkastet eller forhåndsbinde beslutningen.
- Handling for Lars: **hvis** Google-sporet beholdes → endre forventningen til
  «Teateret Kristiansand» (ettord-fiks). **Hvis** R3 bygges om til
  MET.no/skoleferie → testen forsvinner uansett. Dette er det eneste
  gjenværende røde i suiten og oppfyller akseptansekriteriets «eksplisitt
  begrunnet»-alternativ.

## Åpent punkt løftet tydelig — R3-datakildevalget

**Ikke rørt, venter på Lars/Amir.** Repoet har bygget Google Places / Google
Trends / schema.org-skraping (ADR-0004) i stedet for det masterprompten (R3)
spesifiserte: MET.no vær, Agder skoleferie, byarrangementer. Google-sporet
krever API-nøkkel, gratiskreditt-avhengighet og et uoffisielt bibliotek
(`pytrends`). Dette er en reell forretningsbeslutning, ikke en teknisk
rettejobb: **behold Google (og oppdater masterprompt/README til å reflektere
det), eller bygg MET.no/skoleferie som opprinnelig spesifisert.** Punkt B over
henger direkte på denne beslutningen.

## Verifikasjon (kommandoer og bevis)

Kjørt fra repo-rot med `.venv`-Python (3.11.9):

```
python -m pytest
# → 1 failed, 261 passed, 335 subtests passed in ~1.8s
#   eneste failed: test_google_places_fixture_adapter (punkt B, begrunnet)

python -m compileall teateret_brief tests -q
# → exit 0, ingen feil

python scripts/validate_workspace.py
# → 129 «Markdown mangler frontmatter»-advarsler, ingen ERROR/FEIL:
#     107 i .agents/ (kjente, ignoreres per bestilling)
#      18 i .venv/    (transient env jeg opprettet; .venv er gitignored)
#       3 pre-eksisterende repo-filer uten frontmatter og IKKE endret av
#         denne runden: ORIGINAL_REQUEST.md, docs/adr/0001-*.md, docs/adr/0002-*.md
#   → ingen nye funn introdusert av stabiliseringsrunden.
```

### Sikkerhetskritiske endringer — begrunnelse per endring (`security.py`)
- **Amex-regex**: retter `test_credit_card_scanner_and_redaction`. Smal (kun
  34/37, 4-6-5), fanger ikke gyldige ikke-kort-tall; bred nok for separatorer.
- **passord/password i blacklist**: retter `Passord`-subtesten. Domene-
  safelisten er verifisert fortsatt grønn, så ingen gyldig kolonne blokkeres.
- **SSRF kontrollflyt**: retter `test_sourcepolicy_ssrf_and_https_guard`.
  Endrer kun hvilken melding som kastes for privat IP; blokkeringsatferden er
  uendret og adversarial-testen er fortsatt grønn.

## Merknader / rydding
- `.venv/` er opprettet i repoet for testkjøring og er gitignored. Kan slettes
  med `Remove-Item -Recurse -Force .venv` hvis den ikke skal beholdes for
  gjenkjøring. **NB:** `validate_workspace.py` ekskluderer ikke gitignorerte
  stier, så den vil vise 18 `.venv`-frontmatteradvarsler ved hver kjøring helt
  til `.venv` fjernes — det er env-støy, ikke ny repo-rot. Den editable-installen (`pip install -e .`) feiler pga. en
  pre-eksisterende flat-layout-pakkefeil i `pyproject.toml` (setuptools finner
  flere topp-nivå-pakker); omgått ved å installere deklarerte deps ved navn i
  stedet. Ikke rettet — utenfor scope, men verdt et eget punkt.
- Ingen commit/push utført, jf. `AGENTS.md`/`CLAUDE.md` — venter på din
  godkjenning.
