---
title: "Arkitektur"
date: 2026-08-19
status: prototype
tags: [architecture, agents, security]
category: technical
chunk_type: design
---

# Flyt

```text
Godkjente HTTPS-kilder ─┐
                       ├─> innhenting og normalisering ─> kildeleser
Aggregert salgs-CSV ───┘                                  │
                                                          v
                                                      analytiker
                                                          │
                                                          v
                                                      kontrollør
                                                          │
                                                          v
                                    Markdown + HTML + usendt e-postutkast
                                               + manifest og hendelseslogg
```

Innhenting, validering, måltall og rendering er deterministisk kode. Modellen brukes bare der vurdering og syntese gir verdi. Rollene kan ikke kalle verktøy, åpne lenker, lese filer eller sende meldinger.

# Moduler

- `security.py`: repo-grenser, URL-policy, DNS/IP-kontroll og persondatagater.
- `fetcher.py`: kontrollert web/RSS-innhenting og isolerte kildefeil.
- `csv_adapter.py`: eksplisitt skjema for aggregert salg.
- `analytics.py`: deterministiske summer; DuckDB er valgfri akselerator.
- `agents.py`: Pydantic-kontrakter mot Claude og offline fixture-roller.
- `pipeline.py`: rekkefølge, budsjetter, kontrollport og revisjonsspor.
- `render.py`: deterministiske, usendte artefakter.

# Tillitsgrenser

1. Eksterne sider og importer er ubetrodde.
2. Kun kilde-ID-er som pipeline selv har opprettet godtas.
3. Modellutdata er ubetrodde til Pydantic, referansesjekk og kontrollør har godkjent.
4. Renderte filer skannes for direkte kontaktopplysninger.
5. En ansatt må kontrollere og eventuelt sende e-postutkastet.

# Driftsstatus

Offline-demoen er kjørbar. Live-modus er deaktivert i runtime-konfigurasjonen og er bare en teknisk prøveflate. Prosessnivåets DNS-kontroll er ikke alene tilstrekkelig mot DNS-rebinding; egress-allowlist/nettverksisolasjon kreves før aktivering. Sikker e-post, skycontainer, identitet, overvåking, backup og databehandleravtaler ligger utenfor fase 1.
