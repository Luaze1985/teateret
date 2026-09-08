---
title: "Stabiliseringsrunde før pilot"
date: 2026-09-06
status: ready
tags: [task, stabilisering, tester, sikkerhet]
category: task
chunk_type: task-definition
---

# Mål

Få testsuiten grønn og rett dokumentasjonsavvik som er avdekket i
`docs/research/repo-vurdering-mot-masterprompt.md`, uten å endre
AI-arkitekturen eller ta forretningsbeslutninger på Lars/Amirs vegne.

# Kontekst

En gjennomgang 2026-09-06 kjørte `pytest` mot repoet og fant **10 FAILED +
4 SUBFAILED** tester, deriblant tre sikkerhetsrelevante. Full begrunnelse og
testfunn står i `docs/research/repo-vurdering-mot-masterprompt.md` — les den
først. Dette er en rettejobb, ikke ny funksjonalitet.

# Input

- `docs/research/repo-vurdering-mot-masterprompt.md` (funn og begrunnelse)
- `tests/test_security_adversarial.py`, `tests/e2e/test_tier1_feature_coverage.py`,
  `tests/e2e/test_tier2_boundary_corner.py`, `tests/e2e/test_tier4_real_world_scenarios.py`
- `teateret_brief/security.py`, `teateret_brief/csv_adapter.py`, `teateret_brief/matcher.py`
- `docs/adr/0002-koblingskompleksitet-og-aksjonerbar-innsikt.md`

# Oppgaver

1. **Kredittkort-skanner**: `test_credit_card_scanner_and_redaction` feiler
   fordi Amex-format (`3782 822463 10005`, 15 sifre) ikke fanges opp. Rett
   mønstergjenkjenningen i `security.py` slik at testens kortformater dekkes.
2. **Hemmelighets-/header-filter**: `test_header_casing_and_separators`
   feiler for header `Passord`. Utvid blacklisten slik at norske varianter
   (store/små bokstaver, vanlige separatorer) fanges, ikke bare engelske.
3. **Path-traversal på Windows**: `test_repopaths_traversal_attacks` feiler
   for `allowed\..\..\escape.txt`, `..\escape.txt` og
   `C:/Windows/System32/calc.exe`. `RepoPaths` må normalisere og blokkere
   disse på samme måte som Unix-varianten allerede blokkeres. Dette kjører
   på Windows i produksjon — prioriter denne.
4. **Numerisk validering**: `test_numeric_invalid_boundaries_rejected`
   feiler for tom streng, kun mellomrom og `N/A`. Utvid valideringen i
   `csv_adapter.py` slik at disse avvises på linje med `NaN`/negative tall.
5. **SSRF-testens feiltekst**: `test_sourcepolicy_ssrf_and_https_guard`
   feiler kun på forventet feiltekst («Kilden peker til en privat eller
   reservert adresse» vs. faktisk «Kilden ga en ugyldig IP-adresse»).
   Bekreft først at selve blokkeringen av private IP-er fungerer (den ser
   ut til å gjøre det), juster deretter enten testen eller feilteksten så de
   stemmer overens.
6. **Scenario-testene**: `test_scenario_3_dark_weekday_gap_mitigation`,
   `test_scenario_4_school_holiday_matinee_surge`,
   `test_scenario_5_city_clash_storm_event` feiler. Scenario 4 feiler pga.
   en ufullstendig `CsvMapping` i selve testen (mangler `Bordreservasjoner`/
   `Pakkemenyer`) — sjekk om det er en test-bug der også for scenario 3 og 5
   før noe rettes i produksjonskoden. Rapporter rotårsak per test i
   handoff-filen (se under) før du retter — ikke anta at det er samme feil
   tre ganger.
7. **ADR-0002 vs. kode**: Teksten i
   `docs/adr/0002-koblingskompleksitet-og-aksjonerbar-innsikt.md` beskriver
   nivå 2 og 3 i motsatt rekkefølge av det `teateret_brief/matcher.py`
   faktisk gjør (`match_level`-literalen: nivå 2 = tittel+dato+rom, nivå 3 =
   nærhet). Rett ADR-teksten til å stemme med koden — ikke omvendt, koden
   følger masterpromptens (`ORIGINAL_REQUEST.md`) opprinnelige definisjon.

# Eksplisitt utenfor scope

- Ikke endre eller "løs" R3-datakildevalget (Google Places/Trends vs.
  MET.no/Agder skoleferie/byarrangementer). Det er en forretningsbeslutning
  som venter på Lars/Amir. Noter det som åpent punkt i handoff-filen.
- Ikke endre AI-arkitekturen (to-trinns Claude-mønster i ADR-0001, tre
  sekvensielle roller). Denne oppgaven er en rettejobb på eksisterende
  design, ikke et redesign.
- Ikke legg til nye eksterne kilder, nye avhengigheter utover
  `pyproject.toml`, eller nye nettverkskall.
- Ikke slett eller svekk en test for å få den til å passere. Er testen selv
  feil (som i scenario 4-hypotesen over), rett testen eksplisitt og forklar
  hvorfor i handoff-filen — ikke bare fjern den.
- Ikke commit eller push. Følg `AGENTS.md`/`CLAUDE.md` — vent på Lars sin
  godkjenning.

# Acceptance Criteria

- [ ] `python -m pytest` går fra 10 FAILED + 4 SUBFAILED til 0, eller hvert
      gjenværende avvik er eksplisitt begrunnet i handoff-filen.
- [ ] `python -m compileall teateret_brief tests` fortsatt uten feil.
- [ ] `python scripts/validate_workspace.py` kjørt og resultat rapportert
      (kjente advarsler om manglende frontmatter i `.agents/`-mappen kan
      ignoreres; rapporter kun nye funn).
- [ ] `docs/adr/0002-koblingskompleksitet-og-aksjonerbar-innsikt.md` stemmer
      med koden i `matcher.py`.
- [ ] Ingen nye eksterne kilder, avhengigheter eller nettverkskall lagt til.
- [ ] Ingen commit eller push er gjort.

# Expected Output

- rettet: kode i `teateret_brief/security.py`, `csv_adapter.py`, evt.
  `matcher.py`-relatert testfeil;
- rettet: `docs/adr/0002-koblingskompleksitet-og-aksjonerbar-innsikt.md`;
- ny fil: `handoffs/2026-09-06-stabiliseringsrunde-handoff.md` med per-punkt
  status (rettet / testen var feil / ikke rørt), rotårsak for
  scenario-testene, og den åpne R3-beslutningen løftet tydelig.

# Verification

- kommandoer: `python -m pytest`, `python -m compileall teateret_brief tests`,
  `python scripts/validate_workspace.py`;
- bevis: output fra disse kommandoene limt inn eller referert i
  handoff-filen;
- risiko: endringer i `security.py` er sikkerhetskritiske — begrunn hver
  endring med hvilken test den retter og hvorfor løsningen ikke er for snever
  (fanger kun testens eksempler) eller for bred (blokkerer gyldig input).
