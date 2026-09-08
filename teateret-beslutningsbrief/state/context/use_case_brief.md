---
title: "teateret-beslutningsbrief use case brief"
date: 2026-08-19
status: draft
tags:[use-case, brief, workflow_multi_agent]
category: architecture
chunk_type: template
---

# Mål

Gi Teaterets ledelse en ukentlig, kildebelagt brief om programtrender og egne aggregerte salgssignaler uten å innføre et nytt fagsystem.

# Forventet output

Markdown, HTML og et usendt e-postutkast med 1–3 kontrollerte anbefalinger, kilder, advarsler og tydelig menneskelig godkjenningspunkt.

# Avgrensninger

- ingen rå kundedata, e-postlesing, utsending eller publisering;
- kun allowlistede HTTPS-kilder og repo-bundne filer;
- pilotens resultat er beslutningsstøtte, ikke autonom handling;
- ekte bruk krever godkjent datagrunnlag og leverandøravklaring.

# Nærmeste profil

`workflow_multi_agent` med `sequential_handoff`, fordi tre smale roller skal levere validerte resultater i en fast rekkefølge.

# Gjenbruk

Mønsteret kan senere brukes av andre lokale arrangementssteder, men gjenbruk vurderes først etter at Teateret-piloten har bevist nytte.
