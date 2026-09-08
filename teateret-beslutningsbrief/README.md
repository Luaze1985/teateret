---
title: "Teateret beslutningsbrief"
date: 2026-08-19
status: prototype
tags: [teateret, beslutningsstotte, ai, pilot]
category: project
chunk_type: overview
---

# Teateret beslutningsbrief

Privat, lokal pilot som samler godkjente markedssignaler og aggregert salgsdata til ett kildebelagt lederutkast. Systemet sender ingenting og publiserer ingenting.

## Det som er bygget

- HTTPS-kilder må stå i en eksplisitt allowlist. Private IP-er, omdirigeringer, ukjente porter og URL-er med innloggingsdata stoppes.
- GastroPlanner-data leses fra aggregert CSV gjennom en konfigurerbar kolonnemapping. Direkte kundeopplysninger avvises.
- Tre sekvensielle, verktøyløse roller leser, analyserer og kontrollerer. Hvert steg må returnere gyldig, strukturert JSON.
- Resultatet lagres som `brief.md`, `brief.html` og `email.txt`, alltid merket som usendt utkast.
- Hver kjøring får manifest, hendelseslogg, input-hash, kilde-ID-er, promptversjoner, modellbruk og stoppgrunn.
- Én kilde kan feile uten at resten stopper. Ingen lesbare kilder, ugyldige referanser, persondata eller kontrollør-avslag blokkerer leveransen.

## Kjør trygg demo

Demoen bruker kun syntetiske lokale data og gjør ingen nettverks- eller modellkall.

```powershell
.\scripts\run_demo.ps1
```

Eller:

```powershell
python -m teateret_brief.cli --mode demo --run-id min-demo
```

Resultatet legges i `runs/<run-id>/`. Mappen er git-ignorert.

## Test

```powershell
python -m unittest discover -s tests
python -m pytest
python -m compileall teateret_brief tests
```

Valider workspace-kontrakten fra prosjektroten:

```powershell
python scripts\validate_workspace.py
```

## Live-modus er sperret med vilje

Live-modus er i tillegg satt til `live_mode_enabled: false` i `config/runtime.yml`. Den skal ikke slås på før utgående nettverk er isolert/allowlistet utenfor prosessen og personvernportene er godkjent. Når den er godkjent, krever den begge eksplisitte flagg, en CSV-fil inne i repoet og miljøvariablene `ANTHROPIC_API_KEY` og `ANTHROPIC_MODEL`:

```powershell
python -m teateret_brief.cli --mode live `
  --allow-live-network `
  --allow-live-model `
  --sales sample_data/private/gastroplanner_aggregert.csv
```

Ikke legg hemmeligheter i `.env.example`, kode, konfigurasjon eller kjøringslogger. Før ekte bruk må Teateret godkjenne kilder, CSV-skjema, behandlingsgrunnlag, leverandøravtale, lagringstid og hvem som mottar utkastet.

## Avgrensning

Dette er en beslutningsbrief, ikke en selvkjørende markedsavdeling. Første versjon har ingen e-postleser, ingen automatisk utsending, ingen sosial medieinnlogging, ingen CRM-integrasjon og ingen kundedata. GastroPlanner-integrasjon er filbasert til leverandørens API/eksportmuligheter er verifisert.

Se [implementeringsplanen](docs/implementation-plan.md), [arkitekturen](docs/architecture.md), [datapolicyen](docs/data-policy.md) og [GitHub-vurderingen](docs/research/github-reuse.md).

## Valgfrie avhengigheter

Kjernen kjører uten nye installasjoner. `duckdb` og `trafilatura` er valgfrie forbedringer for henholdsvis analyse og tekstuttrekk:

```powershell
python -m pip install -e ".[ingest]"
```

Installer bare etter eksplisitt godkjenning.
