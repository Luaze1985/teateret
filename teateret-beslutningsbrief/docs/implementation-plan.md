---
title: "Implementeringsplan"
date: 2026-08-19
status: implemented-prototype
tags: [plan, pilot, teateret]
category: delivery
chunk_type: plan
---

# Mål

Gi Amir og Teaterets markeds-/programansvarlige et kort, kildebelagt ukesutkast om arrangementstrender, egne salgssignaler og mulige handlinger. Piloten skal passe inn i e-postarbeidsflyten, men ikke sende selv.

# Fase 1 – lokal pilot

Implementert:

1. Eksplisitt kildeliste med sikre nettverksgrenser.
2. Aggregert, konfigurert GastroPlanner-CSV uten kundeopplysninger.
3. Fast kjede: kildeleser → analytiker → kontrollør.
4. Strukturert validering og kilde-ID-er i alle påstander og anbefalinger.
5. Markdown-, HTML- og e-postutkast med menneskelig godkjenningsmerke.
6. Manifest, hendelser, feilrapport, hasher og kjøringsstatus.
7. Syntetisk offline-demo og automatiserte sikkerhets-/flyttester.

Før kundetest:

- avtal 5–10 kilder og tre konkrete beslutningsspørsmål;
- få en anonymisert eksempel-eksport fra GastroPlanner;
- tilpass CSV-mapping og måltall sammen med faktisk bruker;
- avklar modellleverandør, databehandleravtale, lagringssted og sletting;
- kjør fire ukentlige utkast og mål lesetid, redigeringsbehov og handlinger.

# Foreslått leveranse og prisramme

- **Pilot rundt 10 000 kr:** arbeidsmøte, tilpasning til én eksport, godkjent kildeliste, fire testkjøringer og oppsummering. Eksakte grenser avtales før tilbud.
- **Videre veiledning rundt 5 000 kr:** opplæring, justering av spørsmål og arbeidsflyt.
- **Produksjonsintegrasjon fra 20–30 000 kr:** sikker skydrift, e-postkobling, overvåking, tilgangsstyring og drift. Prises først etter pilotbevis.

# Stoppkriterier

Ikke gå videre dersom utkastene mangler kildegrunnlag, krever mye manuell retting, trekker inn persondata, ikke fører til bedre beslutninger eller er dyrere å drifte enn den dokumenterte nytten.

# Fase 2 – bare etter godkjent pilot

- tidsstyrt containerjobb i egnet norsk/europeisk sky;
- dedikert postkasse med minst mulig tilgang og utkast-only;
- leverandørbekreftet GastroPlanner-API eller kontrollert eksportkanal;
- `changedetection.io` eller tilsvarende for godkjente sider;
- eventuelt dashboard først når e-postbriefen ikke lenger er nok.
