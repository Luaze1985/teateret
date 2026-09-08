---
title: "Datapolicy for pilot"
date: 2026-08-19
status: mandatory
tags: [privacy, security, data]
category: governance
chunk_type: policy
---

# Tillatt i fase 1

- Offentlig arrangementsinformasjon fra eksplisitt godkjente HTTPS-kilder.
- Aggregert salg per arrangement, dato eller kategori.
- Kapasitet, solgte billetter, omsetning og aggregert bord-/pakkeantall.
- Interne beslutningsspørsmål uten kunde- eller personalopplysninger.

# Ikke tillatt i fase 1

- Navn, e-post, telefon, fritekst fra kunder, bookingnotater eller preferanser.
- Rå e-postkasser, mottakerlister, betalingsdata eller ordrehistorikk på personnivå.
- Innlogging eller scraping av sosiale plattformer.
- Modelltrening, personalisering eller segmentering på enkeltpersoner.
- Automatisk utsending, publisering eller kjøp.

# Minstekrav før ekte data

1. Teateret må være behandlingsansvarlig og utpeke dataeier.
2. Formål, dataminimering, tilgang, lagringstid og sletting dokumenteres.
3. Modell- og skyleverandør vurderes, inkludert databehandleravtale og behandlingssted.
4. Testdata anonymiseres; private filer holdes i git-ignorert mappe.
5. Logger skal ikke inneholde rå data eller hemmeligheter.
6. Mottaker av utkastet og menneskelig godkjenner må være navngitt.

# Teknisk håndheving

CSV-leseren avviser kjente identifikator-kolonner og direkte e-post/telefonmønstre. Alle filstier må ligge i repoet. Nettverkskilder bruker allowlist og offentlige IP-er. Dette reduserer risiko, men erstatter ikke juridisk vurdering eller en databehandleravtale.
