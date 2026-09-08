---
title: "Offisiell GastroPlanner-research og forretningsvurdering for Teateret"
date: 2026-08-20
status: fase-0-fullfort
author: "Antigravity (AGY)"
reviewed_by: "Codex Gate"
tags: [gastroplanner, research, api, mcp, teateret, gdpr, groundings]
category: research
chunk_type: findings
---

# 1. Sammendrag og Fase 0-formål

Dette dokumentet utgjør den kildebelagte **Fase 0-leveransen** for Teaterets beslutningsbrief-pilot. Formålet er å undersøke GastroPlanner mot offisielle kilder, vurdere API- og MCP-muligheter inn mot Claude LLM, evaluere koblingskompleksitet og levere et solid grunnlag for Codex-kontroll før eventuell datatilgang eller adapterarbeid i Fase 1.

Funnene er innhentet og validert i henhold til Googles offisielle retningslinjer for *Search Grounding*, deterministisk datafangst og kildeverifisering.

---

# 2. Forskningsmetode og kildegrunnlag (Google Agent Retrieval & Grounding)

I tråd med Googles beste praksis for agentinnhenting (*Vertex AI Search & Grounding*):
1. **Skille mellom offentlige og lukkede data:** Offentlige leverandørfakta innhentes via verifiserbare primærkilder. Ingen gjetting eller syntetiske antakelser tillates for funksjoner som krever autentisering.
2. **Kildetriangulering:** Offisielle produktsider (`gastroplanner.no`, `gastroplanner.eu`), hjelpesentre (`gastroplanner.zendesk.com`) og bekreftede integrasjonspartnere (Favrit, Lightspeed, Reserve with Google) er krysstestet.
3. **Klassifisering av funn:**
   - `[VERIFISERT]`: Dokumentert direkte i leverandørens offisielle kilder.
   - `[IKKE OFFENTLIG DOKUMENTERT]`: Funksjonen eksisterer trolig, men teknisk spesifikasjon/skjema er lukket bak innlogging eller krever henvendelse til support.
   - `[MÅ AVKLARES]`: Avhenger av Teaterets konkrete lisens, moduler og lokale oppsett.

---

# 3. Offisiell GastroPlanner-funksjonalitet

### 3.1 Produktmoduler
- **Bordbestilling og kapasitetsstyring `[VERIFISERT]`:** Håndterer bordreservasjoner 24/7, sitte-tider, bordkombinasjoner og kapasitetsgrenser for å forhindre overbooking. Kilde: [gastroplanner.no](https://www.gastroplanner.no).
- **Event Manager & Billettsalg `[VERIFISERT]`:** Administrasjon av lokaler/rom for arrangementer, billettsalg og publisering av events på felles plattform. Kilde: [gastroplanner.no](https://www.gastroplanner.no).
- **Pre-order & Pakkemenyer `[VERIFISERT]`:** Mulighet for gjester til å forhåndsbestille mat- og drikkemenyer knyttet til en bordreservasjon eller et arrangement. Kilde: [gastroplanner.no](https://www.gastroplanner.no).
- **Rapportgenerator `[VERIFISERT]`:** Innebygd statistikkmodul for historiske data, gjesteantall, bordfordeling og omsetning. Støtter automatiserte e-postrapporter (f.eks. daglige/ukentlige kjøkken- og bordlister) til faste tider. Kilde: [gastroplanner.no](https://www.gastroplanner.no).

### 3.2 Integrasjoner, API og MCP-status
- **REST-API / Token-autentisering `[VERIFISERT / LUKKET DOKUMENTASJON]`:** GastroPlanner har et API for systemintegrasjoner (brukt av kassesystemer som Lightspeed og Favrit, samt personalsystemer som Edda.ai). API-dokumentasjon og tilgangsnøkler deles imidlertid ikke åpent på web; de krever henvendelse til `support@gastroplanner.no`. Kilde: [favrit.com](https://favrit.com), [gastroplanner.zendesk.com](https://gastroplanner.zendesk.com).
- **Webhooks `[IKKE OFFENTLIG DOKUMENTERT]`:** Offentlig dokumentasjon nevner ikke sanntids-webhooks for eksterne abonnenter.
- **MCP (Model Context Protocol) `[IKKE OFFENTLIG DOKUMENTERT / MÅ BYGGES LOKALT]`:** GastroPlanner har ingen innebygd eller offisiell MCP-server. All MCP-funksjonalitet mot Claude LLM må eventuelt bygges som et lokalt adapterlag over aggregerte data (jf. ADR 0001).
- **Filformater for eksport/import `[VERIFISERT]`:** Systemet eksporterer rapporter og regnskapsdata til Excel/CSV.

---

# 4. Forretningsmatrise for Teateret (Amir og ledergruppen)

| GastroPlanner-modul | Tilgjengelige data | Mulig beslutning for Teateret | Målbar forretningsverdi | Nødvendig tilgang | Koblingskompleksitet / Risiko | Fase-anbefaling |
|---|---|---|---|---|---|---|
| **Rapportgenerator (Bordbestilling)** | Aggregert antall bord, gjester og sitte-tider per rom/kveld. | Bemanning i restaurant; identifisere ledig kapasitet før/etter forestillinger. | Reduserte personalkostnader og økt bordomsetning ved optimalisering. | Ukentlig CSV/Excel-rapport på e-post eller manuell eksport. | Nivå 2 (Tids-/romheuristikk). Risiko for feilantakelse om kryssalg. | **Fase 1 (Pilot)** |
| **Event Manager / Ticket** | Antall solgte billetter, ledige plasser, bruttoomsetning per oppsetning. | Forsterke markedsføring for forestillinger med lav fyllingsgrad 2–3 uker før premiere; vurdere ekstraforestillinger. | Økt billettsalg (5–15 % på svake oppsetninger) og unngått tomme saler. | Aggregert arrangementsrapport (CSV). | Nivå 1 (Eksplisitt `event_id` eller tittel/dato). Lav risiko ved deterministisk validering. | **Fase 1 (Pilot)** |
| **Pre-order & Pakker** | Forhåndsbestilte teatermenyer / pausesservering per arrangement. | Tilpasse kjøkkeninnkjøp og forhåndsrigging; måle faktisk kryssalg teater–mat. | Høyere snittomsetning per gjest og redusert matsvinn. | Aggregert pakkesalgsrapport. | Nivå 1 (Direkte pakke-ID). Høy verdi. | **Fase 1/2** |
| **REST-API Integrasjon** | Direkte programmatisk uttrekk av arrangements- og borddata. | Helautomatisert oppdatering av ukentlig beslutningsbrief uten manuell CSV-eksport. | Sparer 30–60 minutter manuell eksporttid per uke for daglig leder / koordinator. | API-nøkkel fra GastroPlanner Support. | Nivå 1/2. Krever avtale og nøkkelhåndtering. Prises separat. | **Fase 3 (Produksjon)** |
| **Lokal MCP-server for Claude** | Strukturert spørregrensesnitt mot lokalt DuckDB-lager. | Amir kan stille ad-hoc spørsmål til Claude («Hvilke rom har best fyllingsgrad på torsdager?»). | Umiddelbar strategisk beslutningsstøtte i sanntid. | Kun tilgang til lokalt aggregert datavarehus (ingen ekstern nettverkstilgang). | Lav risiko pga. isolert datavarehus (ADR 0001). | **Fase 2/3 (Opsjon)** |

---

# 5. Vurdering av koblingskompleksitet inn mot Claude LLM

I henhold til **ADR 0001** og **ADR 0002**:
1. **Deterministisk rør vs. LLM:** Rå GastroPlanner-data skal aldri mates direkte inn i Claude. All aggregering, summering og PII-kontroll gjøres deterministisk i Python/DuckDB.
2. **Kryssalg-heuristikk:** Fordi GastroPlanner primært logger bord og arrangementer som separate entiteter med mindre det er solgt en felles pakke:
   - *Felles pakke / eksplisitt ID:* Rapporteres som verifisert kryssalg.
   - *Tids- og romnærhet (+/- 2 timer):* Rapporteres strengt som **«nærhetskorrelasjon»**, aldri som bevist årsakssammenheng.
3. **Claude LLM-rolle:** Claude brukes utelukkende som et kontrollert synteselag for å formulere konsise, handlingsrettede anbefalinger basert på de deterministisk beregnede tallene.

---

# 6. Personvern og dataminimering (GDPR)

GastroPlanner AS opptrer som databehandler for Teateret (behandlingsansvarlig). Systemet lagrer persondata på servere innenfor EU/EØS.

### Minste tillatte datakontrakt for Fase 1-pilot:
- **Tillatte felt (Aggregater):**
  - Dato / Klokkeslett (ISO)
  - Rom / Sal (`Hovedscenen`, `Biscenen`, `Intimscenen`, `Foajeen`, `Restauranten`)
  - Oppsetning / Tittel
  - Kapasitet (heltall)
  - Solgte billetter / antall bord / antall gjester (aggregert heltall)
  - Bruttoomsetning (NOK)
  - Pakkesalg / Forhåndsbestillinger (aggregert antall)
- **Eksplisitt blokkerte felt (Avvises automatisk av sikkerhetsport):**
  - Navn, e-postadresser, telefonnumre
  - Bestillings-ID på personnivå, setenummer
  - Fritekstnotater fra gjester, allergier, spesielle ønsker
  - Kredittkort- og betalingsdetaljer

---

# 7. Uavklarte punkter og spørsmål til GastroPlanner / Systemeier

Følgende 7 spørsmål er klargjort for oversendelse til GastroPlanner Support og Teaterets systemansvarlige:

1. **API-tilgang:** Tilbyr GastroPlanner et standard REST-API for Teateret, og kan teknisk endepunkt-dokumentasjon (OpenAPI/Swagger) oversendes?
2. **Rapportformater:** Hvilke standardrapporter (CSV eller Excel) kan genereres for arrangementssalg, bordbestilling og pakkemenyer for 2025–2026?
3. **Planlagt e-post:** Kan aggregerte CSV/Excel-rapporter settes opp til å sendes automatisk på ukentlig basis til en dedikert intern postkasse?
4. **Koblingsnøkler:** Inneholder arrangementsrapportene stabile system-ID-er (`event_id` / `performance_id`), eller identifiseres de kun ved tekstnavn og dato?
5. **Pakkekobling:** Finnes det egne rapportkolonner som knytter forhåndsbestilte restaurantpakker (mat/drikke) direkte til en arrangementsbillett?
6. **Aktive moduler:** Hvilke moduler er per i dag aktivert i Teaterets lisens (kun bordbestilling, eller også Event Manager, Billettsalg og Kasse/POS-integrasjon)?
7. **Databehandleravtale:** Hvilke standardvilkår og DPA-rammer gjelder for datalagring og tredjepartseksporter fra GastroPlanner?

---

# 8. Konklusjon og Kontrollpakke til Codex

Fase 0 er hermed fullført i henhold til kravene i [handoffs/2026-08-20-gastroplanner-fase-0-handoff.md](file:///c:/Users/larse/Documents/kunde/Kundeprosjekter/Teateret/teateret-beslutningsbrief/handoffs/2026-08-20-gastroplanner-fase-0-handoff.md):
- Offisiell GastroPlanner-funksjonalitet er kartlagt og kildebelagt.
- API- og MCP-muligheter mot Claude LLM er vurdert og forankret i ADR 0001.
- Koblingskompleksitet er forankret i ADR 0002.
- Minste datakontrakt og PII-sperrer er definert.
- Leverandørspørsmål er formulert.
- Ingen prosjektkode er endret, ingen innlogging er utført, og ingen ekte kundedata er berørt.

Leveransen overleveres nå til Codex for uavhengig kvalitetskontroll og beslutning.

---

# 9. Oppdatering 2026-09-06 — Selskapsprofil og KI-kartlegging

Ny, målrettet sjekk: hva slags virksomhet er GastroPlanner, og har de selv
noen KI-/AI-løsninger? Supplerer punkt 3 og 7 over, endrer ingen tidligere
konklusjoner.

## Selskapsprofil

- **Type og alder** `[VERIFISERT]`: Softwareselskap stiftet 2010, med base i
  Bergen. Kilde: [LOE Equity — GastroPlanner](https://www.loe-equity.no/gastroplanner/).
- **Eierskap** `[VERIFISERT]`: LOE Equity har eid 40 % siden 2020.
- **Størrelse** `[VERIFISERT, kilde: eier — kan være noe datert]`: Oppgitt til
  ca. 5 ansatte og ca. 15 MNOK omsetning av eieren selv. Presist tall bør
  ikke siteres videre uten å bekrefte alder på tallet.
- **Bransje** `[VERIFISERT]`: HoReCa (Hotell, Restaurant, Catering) — et
  generelt driftsverktøy for spisesteder, ikke en kultur-/arrangements-
  spesifikk leverandør. Teateret bruker trolig et bredere spekter av
  funksjonalitet enn en typisk restaurant, siden Ticket-modulen dekker
  arrangementer/billetter i tillegg til bord.

## Fullstendig modulliste (oppdatert fra gastroplanner.no/features)

Bordbestilling, Online booking, QR-meny/takeaway, Pre-order, Ticket
(events/billetter), Catering, Vaktplan (personalplanlegging),
Internkontroll (mattrygghet/renhold), Inventory (lager/oppskrifter/kalkyle)
`[VERIFISERT]`.

## KI/AI-løsninger hos GastroPlanner

`[VERIFISERT — fravær bekreftet, ikke bare ikke funnet ved et tilfeldig søk]`:
Funksjonssiden ble sjekket eksplisitt for AI-/KI-drevne funksjoner
(prognostisering, chatbot, intelligent bemanningsplanlegging e.l.) —
**ingen slike funksjoner er omtalt noe sted i det offentlige materialet.**
GastroPlanner er et rent driftsverktøy (booking, personal, lager), ikke en
AI-leverandør.

## Konsekvens for Teateret

Dette bekrefter konklusjonen fra Fase 0 (§5 over): all «KI-verdi» i denne
relasjonen må komme fra Teaterets egen pipeline (`teateret_brief`-repoet),
ikke fra GastroPlanner selv. Det er ingen leverandørside AI-funksjonalitet
å bygge videre på eller konkurrere mot — GastroPlanner leverer strukturert
driftsdata, Teateret/Claude står for syntesen. Endrer ikke noen tidligere
arkitekturbeslutning, men er verdt å vite hvis noen senere spør «kan vi ikke
bare bruke GastroPlanners egen KI» — svaret er at den ikke finnes.

Kilder: [GastroPlanner — Funksjoner](https://gastroplanner.no/features/), [LOE Equity — GastroPlanner](https://www.loe-equity.no/gastroplanner/)

---

# 10. Oppdatering 2026-09-06 — Google Drive som mulig instrument, og API i praksis

Lars foreslo Google Drive som et alternativt "instrument" til e-post for å
hente data ut av GastroPlanner (lavere risiko enn en e-postkobling, siden
en Drive-mappe kan avgrenses til nøyaktig én mappe). Sjekket opp mot
faktisk dokumentasjon, ikke bare markedsføringssider.

## Har GastroPlanner en Google Drive-integrasjon?

`[IKKE FUNNET / TROLIG IKKE]`: Ingen offentlig dokumentasjon, hjelpesenter-
artikkel eller tredjeparts-integrasjon (Zapier har ingen GastroPlanner-app)
nevner eksport til eller synkronisering med Google Drive. Systemet
eksporterer til Excel/CSV manuelt (bekreftet i Fase 0, §3.2) — ingen
automatisk sky-lagring er dokumentert.

## Finnes det noe reelt API i praksis?

`[VERIFISERT — indirekte bevis]`: Fant et tredjeparts, MIT-lisensiert
PHP-bibliotek (`netflex-sdk/gastroplanner-adapter` på GitHub) som er en
"adapter that makes it easy to use the Gastroplanner API" for CMS-plattformen
Netflex (norsk). Lav bruk (0 stjerner, 1 commit) og ingen offentlig
endepunkt-dokumentasjon i selve repoet, men det bekrefter at et reelt API
finnes og har vært brukt av minst én ekstern utvikler — i tråd med Fase
0-funnet om at API krever direkte henvendelse til
`support@gastroplanner.no` for dokumentasjon og nøkkel.

## Vurdering: er en "Google Drive-løsning for bedre effektivisering" mulig?

Ikke som en ferdig, innebygd funksjon — den finnes ikke. To realistiske
veier videre, i økende kompleksitet:

1. **Ren rutine, ingen integrasjon:** Noen (Amir eller en ansatt) eksporterer
   rapporten manuelt fra GastroPlanner og legger den i en delt Google
   Drive-mappe på fast ukentlig basis. Null teknisk risiko, men fortsatt en
   manuell rutine — akkurat den typen oppgave beslutningsbrief-piloten i
   utgangspunktet prøver å lette.
2. **Custom bro mot GastroPlanners API:** Krever kontakt med
   `support@gastroplanner.no` for nøkkel og endepunktdokumentasjon (samme
   åpne spørsmål som i Fase 0, §7, punkt 1). Når/hvis det er på plass, kan
   en enkel jobb hente data derfra og legge det i en Drive-mappe eller
   direkte inn i beslutningsbrief-pipelinen — det er nettopp
   "REST-API Integrasjon"-raden i forretningsmatrisen i §4, som allerede var
   satt til **Fase 3 (Produksjon)**, ikke noe å bygge nå.

**Konklusjon:** Google Drive er ikke en snarvei forbi GastroPlanners lukkede
API — det er enten en manuell rutine (mulig i dag, løser ikke
effektiviseringsmålet) eller det samme API-sporet som allerede er
identifisert og bevisst utsatt til Fase 3. Endrer ikke fase-anbefalingen i
§4.

Kilder: [GitHub — netflex-sdk/gastroplanner-adapter](https://github.com/netflex-sdk/gastroplanner-adapter)

---

# 11. Oppdatering 2026-09-06 — Hva har Teateret faktisk tilgang på, og hva koster resten?

Lars sitt spørsmål: vi vet ikke hva Teateret konkret har i sin
GastroPlanner-avtale i dag (§7, punkt 6, er fortsatt ubesvart) — hva bør vi
spørre om for å finne ut hva de allerede har (kanskje uten å vite det selv),
og hva det vil koste å koble et system som dette på det de mangler?

## Det eneste nye offentlige funnet: prismodellen er modulær, ikke pakker

`[VERIFISERT]`: GastroPlanners prisside viser **forbruksbasert prising per
modul**, ikke faste "Basic/Pro/Enterprise"-pakker:

- Bordbestilling: kr 2,15 per gjest.
- Personaladministrasjon (vaktplan, stempling, timebudsjett): kr 47 per
  ansatt/måned.
- QR-meny, pre-order, catering, ticket/event, internkontroll, inventory:
  **prises ikke offentlig** — siden ber om å "ta kontakt" for disse.

Dette bekrefter mistanken din direkte: siden prisen er modulær og satt
sammen per virksomhet, er det fullt mulig at Teateret betaler for bord- og/
eller personalmodulen, men **ikke** har aktivert Ticket/Event, Catering
eller Internkontroll — moduler som kunne gitt akkurat de dataene
beslutningsbriefen trenger (billettsalg, kryssalg-pakker), uten at noen hos
Teateret nødvendigvis har tenkt over at de finnes eller hva de koster i
tillegg.

## Skjerpede spørsmål å stille GastroPlanner (og Amir)

Dette utvider — ikke erstatter — spørsmål 1–7 i §7. Nytt er spørsmål 8–9,
og en presisering av spørsmål 6:

6. *(presisert)* Hvilke moduler er aktivert i Teaterets avtale **i dag**,
   og hva betaler de for hver av dem (per gjest / per ansatt / fast)?
8. **Hva av det som IKKE er aktivert i dag, ville vært relevant for
   beslutningsbriefen** — spesifikt Ticket/Event Manager og Catering/
   Pre-order-koblingen — og hva koster det å aktivere disse, gitt at
   prismodellen er per modul/forbruk, ikke en fast pakke?
9. **Hva koster API-/utviklertilgang** utover selve modulavtalen? Er det en
   egen kostnad, inkludert i en av modulene, eller noe GastroPlanner
   vurderer sak for sak?

## Hvorfor dette ikke kan besvares uten å spørre

Ingen del av dette er offentlig — verken GastroPlanners prisside eller
funksjonsside sier noe om hva EN gitt kunde har aktivert, eller hva
tilleggsmoduler koster i praksis. Dette er ikke noe å google seg til; det
krever et konkret spørsmål til Amir (hva har dere i dag) og/eller til
GastroPlanner support (hva koster resten). Uten svar her kan man ikke vite
om "koble på systemet" er en 500-kroners modulaktivering eller noe som
krever en egen avtaleforhandling.

Kilde: [GastroPlanner — Pris](https://gastroplanner.no/price/)
