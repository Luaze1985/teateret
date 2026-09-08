---
title: "Avstemmings- og kvalitetsrapport for GastroPlanner 2026"
date: 2026-08-20
status: evaluert
author: "Antigravity (AGY)"
reviewed_by: "Codex Gate"
tags: [gastroplanner, matching, avstemming, testresultat, teateret]
category: research
chunk_type: findings
---

# 1. Sammendrag

Denne rapporten dokumenterer testen av **3-trinns avstemmingsmotor (ADR 0002)** og **utvidet GastroPlanner CSV-adapter** mot de bekreftede arrangementsdataene for 2026.

Testen ble gjennomført med syntetisk, personvernsikret testdatasett ([sample_data/gastroplanner_sample_2026.csv](file:///c:/Users/larse/Documents/kunde/Kundeprosjekter/Teateret/teateret-beslutningsbrief/sample_data/gastroplanner_sample_2026.csv)).

---

# 2. Evalueringsresultat og Dekningsgrad

| Metrikk | Verdi | Vurdering |
|---|---|---|
| **Totalt unike arrangementer testet** | 9 | Dekker representative arrangementer i 2026 (Hovedscenen, Biscenen, Intimscenen, Foajeen). |
| **Matchet (Matched)** | 9 | 100,0 % dekningsgrad. |
| **Trenger gjennomgang (Needs Review)** | 0 | Ingen tvetydige tids- eller romnærheter i dette datasettet. |
| **Umatchet (Unmatched)** | 0 | 0 % avvik. |
| **PII-sikkerhetssjekk** | PASS | Ingen personopplysninger, e-postadresser eller telefonnumre oppdaget. |

---

# 3. Detaljert avstemmingstabell

| Dato | Arrangement (GastroPlanner) | Rom | Matchet arrangements-tittel | Match-nivå | Begrunnelse / ID |
|---|---|---|---|---|---|
| 2026-02-25 | Speed date 40–59 | Foajeen | Speed date 40–59 | `level_1_id` | Eksakt ID: `EVT-260225` |
| 2026-03-13 | Svanesjøen | Hovedscenen | Svanesjøen | `level_1_id` | Eksakt ID: `EVT-260313` |
| 2026-04-22 | Speed date 30–45 | Foajeen | Speed date 30–45 | `level_1_id` | Eksakt ID: `EVT-260422` |
| 2026-07-11 | Norge–England – VM på storskjerm | Hovedscenen | Norge–England – VM på storskjerm | `level_1_id` | Eksakt ID: `EVT-260711` |
| 2026-07-17 | Sommerstandup med Fire halvkjente fjes | Hovedscenen | Sommerstandup med Fire halvkjente fjes | `level_1_id` | Eksakt ID: `EVT-260717` |
| 2026-08-20 | Kristiansand Jazzfestival 26 | Biscenen | Kristiansand Jazzfestival 26 | `level_1_id` | Eksakt ID: `EVT-260820` |
| 2026-08-26 | Speed date 40–60 | Foajeen | Speed date 40–60 | `level_1_id` | Eksakt ID: `EVT-260826` |
| 2026-08-29 | Baldrian og Musa – Luft og kjærlighet | Intimscenen | Baldrian og Musa – Luft og kjærlighet | `level_1_id` | Eksakt ID: `EVT-260829` |
| 2026-09-11 | Amund Mathisen // Teateret | Intimscenen | Amund Mathisen // Teateret | `level_1_id` | Eksakt ID: `EVT-260911` |

---

# 4. Forretningsmessig analyse av testdataene for ledelsen (Amir)

1. **Kapasitet og Bestselgere:**
   - **Hovedscenen:** *Svanesjøen* (380/400 = 95 % fyllingsgrad, 185 000 NOK) og *Norge–England VM* (350/350 = 100 % fyllingsgrad, 142 000 NOK) viser maksimal utnyttelse.
   - *Sommerstandup* (290/350 = 83 % fyllingsgrad, 98 500 NOK) har 60 ledige plasser som kan utløse et målrettet markedstiltak 1–2 uker i forkant.
2. **Foajé- og intimformater:**
   - *Speed date-konseptene* i Foajeen fyller jevnt 80–100 % av kapasiteten (32–40 gjester) med stabil pakke- og bordomsetning (14 800 – 18 500 NOK).
3. **Restaurantkryssalg:**
   - Høyest bordbooking og forhåndsbestilte pakker sees rundt *Norge–England* (150 bord / 90 pakker) og *Svanesjøen* (120 bord / 65 pakker).
