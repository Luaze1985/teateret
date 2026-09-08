---
name: teateret-brief
description: Generer en ukentlig beslutningsbrief for Teateret i Kristiansand basert på aggregerte GastroPlanner-data og offentlige arrangementsdata.
---

# Teateret Beslutningsbrief Workflow

Denne skillen veileder agenten gjennom en deterministisk, personvernssikker generering av Teaterets ukentlige beslutningsbrief i henhold til ADR 0001 og ADR 0002.

## Forutsetninger og sikkerhetspolicy

1. **Ingen rå persondata:** CSV-filer må være aggregert på arrangements-, rom- eller dagsnivå. Kolonner med personnavn, e-post, telefon og notater avvises automatisk.
2. **Deterministisk før LLM:** Summer, fyllingsgrader og avstemming beregnes i Python/DuckDB før Claude mates med aggregater.
3. **Usendt utkast:** Briefen genereres som Markdown/HTML og lagres lokalt i `outputs/` eller `runs/<id>/`. Ingen e-post sendes automatisk.

---

## Prosedyre steg-for-steg

### Steg 1: Valider og les inn GastroPlanner CSV
- Bruk `teateret_brief.csv_adapter.load_aggregated_csv` med mapping fra `config/gastroplanner_mapping.example.yml` (eller lokal mapping-fil).
- Sikre at filen ligger i `sample_data/` eller godkjent inndata-mappe.

### Steg 2: Avstem mot arrangementsregisteret (3-trinns matcher)
- Initialiser `EventMatcher` fra `teateret_brief.matcher` med godkjente arrangementsdata (f.eks. fra `docs/research/arrangementsdata-2025-2026.md`).
- Kjør `matcher.evaluate_all(observations)`.
- Verifiser at:
  - Nivå 1 (ID-match) og Nivå 2 (Tittel/Dato/Rom) settes som `matched`.
  - Nivå 3 (Tids/Dato-nærhet) merkes som `needs_review` og omtales i briefen som *nærhetskorrelasjon*.

### Steg 3: Kjør deterministisk aggregering
- Kjør `teateret_brief.analytics.summarize_sales(observations)` for å generere summer, rangeringer og periodeendringer.

### Steg 4: Generer syntese og anbefalinger via Claude
- Send det aggregerte JSON-payloadet gjennom `StructuredClaudeRoles` i `teateret_brief.agents`.
- Modellen produserer opptil 3 konkrete anbefalinger for ledelsen (Amir) basert på:
  1. Rom- og scenekapasitet (ledige hull vs. fylte saler).
  2. Kryssalg restaurant / teater.
  3. Markedsføringsbehov 2–3 uker frem i tid.

### Steg 5: Render artefakter og verifiser
- Renderer Markdown (`brief.md`), HTML (`brief.html`) og manifest (`manifest.json`) i en unik kjøringsmappe under `runs/<run_id>/`.
- Skann de genererte filene for PII via `security.scan_public_artifact`.
