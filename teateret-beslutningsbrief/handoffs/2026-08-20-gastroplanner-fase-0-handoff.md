---
title: "Handoff til Antigravity: GastroPlanner-research og Teateret-pilot"
date: 2026-08-20
status: ready-for-antigravity
owner: Lars
controller: Codex
runtime: Antigravity
---

# Oppdraget

Antigravity (AGY) skal undersøke GastroPlanner mot offisielle kilder, forklare hva løsningen faktisk kan brukes til for Teateret i Kristiansand, og deretter klargjøre den eksisterende beslutningsbrief-piloten for én kontrollert, aggregert GastroPlanner-eksport.

Dette er en bestilling til AGY. Codex er kontrollør og skal senere vurdere kildebelegg, avgrensning, personvern, kodeendringer og testbevis. Codex skal ikke gjøre leverandørresearchen på vegne av AGY.

# Prosjektrot og leserekkefølge

Prosjektrot:

`C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief`

Les før arbeid:

1. `AGENTS.md`
2. `CONTEXT.md`
3. `README.md`
4. `state/context/use_case_brief.md`
5. `docs/data-policy.md`
6. `docs/architecture.md`
7. `docs/implementation-plan.md`
8. `docs/research/arrangementsdata-2025-2026.md`
9. `config/gastroplanner_mapping.example.yml`

Eksisterende kode, tester og live-sperrer skal bevares. Ikke slå på live-modus.

# Grunnlaget AGY overtar

- Det finnes en lokal, testbar prototype som lager en kildebelagt beslutningsbrief fra godkjente webkilder og aggregert CSV.
- Første GastroPlanner-kobling er bevisst filbasert. API-tilgang er ikke bekreftet.
- Offentlig Teateret-research inneholder et avgrenset startgrunnlag: 10 publiserte/planlagte oppsetninger fra 2025 og 15 representative oppsetninger fra 2026. Dette er ikke komplett salgs- eller arrangementshistorikk.
- Komplett analyse krever autoritativ intern eksport. Nettsiden alene kan ikke bevise salg, gjennomføring, restaurantbruk eller årsdekning.
- Fase 1 tillater bare aggregert informasjon. Ingen navn, e-post, telefon, bestillings-ID, setenummer, allergier, fritekstnotater, betalingsdata eller individsegmentering.

# Forretningsmålet

AGY skal finne ut om GastroPlanner-data kan hjelpe Amir og Teaterets program-, markeds- og restaurantansvarlige med å besvare spørsmål som:

1. Hvilke arrangementer, formater, rom, ukedager og tidsperioder presterer best eller svakest?
2. Finnes det ledig kapasitet eller programhull som bør følges opp?
3. Kan aggregert restaurantaktivitet kobles forsvarlig til arrangementer for å måle kryssalg?
4. Hvilke arrangementer bør markedsføres mer, endres eller gjentas – og hvilket datagrunnlag støtter anbefalingen?
5. Hvilken ukentlig informasjon kan leveres i en kort beslutningsbrief uten at ansatte må bruke et nytt system?

AGY skal ikke love at disse spørsmålene kan besvares. Den skal dokumentere hvilke felt og koblingsnøkler som faktisk finnes, og markere resten som datagap.

# Agentplan for AGY

Bruk en kontrollert, sekvensiell arbeidsflyt. Ikke start en fri agentflokk.

## A0 – Koordinator

Ansvar:

- les prosjektreglene og lås scope;
- opprett en kort arbeidsplan og før status;
- sørg for at ingen agent bruker innlogging, hemmeligheter eller ekte kundedata;
- stopp ved tilgangs-, API-, lisens- eller personvernuklarhet;
- samle leveransene til kontroll hos Codex.

## A1 – Offisiell GastroPlanner-researcher

Arbeider kun lesende mot primærkilder:

- offisielt nettsted og produktsider;
- offisiell hjelpeside/supportdokumentasjon;
- offisiell API- eller integrasjonsdokumentasjon;
- offisiell personvernerklæring, databehandlerinformasjon og vilkår;
- eventuell offisiell utviklerportal eller leverandørbekreftelse som Lars gir tilgang til.

Skal kartlegge og kildebelegge:

- hvilke produktmoduler og rapportfunksjoner som finnes;
- bordbestilling, billett/arrangement, event/tilbud, restaurantpakker eller forhåndsbestilling, kommunikasjon og data/innsikt der dette er dokumentert;
- om CSV/XLSX-eksport, planlagte rapport-e-poster, webhooks eller API er offentlig dokumentert;
- om stabile `event_id`/`performance_id` eller andre koblingsnøkler er dokumentert;
- hvilke personopplysninger løsningen kan behandle og rollefordelingen mellom kunde og GastroPlanner;
- integrasjoner som er relevante for Teateret, men bare når de er dokumentert av leverandøren.

Hvert funn merkes:

- `verifisert` – direkte støttet av offisiell kilde;
- `ikke offentlig dokumentert` – ingen offisiell dokumentasjon funnet;
- `må avklares` – avhenger av Teaterets abonnement, oppsett eller leverandørsvar.

Sekundærkilder kan brukes til å finne en offisiell side, men ikke som endelig belegg.

## A2 – Forretningsanalytiker

Bruker bare A1s verifiserte funksjoner. Lager en matrise med:

`funksjon → tilgjengelige data → mulig beslutning → målbar verdi → nødvendig tilgang → risiko → pilot/ikke pilot`

Vurder særlig:

- program- og kapasitetsanalyse;
- aggregert salg og omsetning per oppsetning;
- aggregert bordbooking og mulig restaurantandel rundt arrangement;
- pakker eller forhåndsbestillinger dersom offisielt dokumentert;
- raskere ukentlig rapportering til ledelsen;
- datakvalitet, manglende ID-er og manuell avstemming;
- hva som kan selges som en liten pilot rundt 10 000 kroner, og hva som er produksjonsintegrasjon til 20–30 000 kroner eller mer.

Ikke påstå årsakssammenheng. «Høyt restaurantsalg samme kveld» er et signal, ikke bevis på at arrangementet skapte salget.

## A3 – Data- og personvernkontrollør

Definerer minste tillatte datakontrakt for pilot. Foretrukne aggregatfelt som skal verifiseres mot faktisk eksport:

- stabil arrangements-/oppsetnings-ID;
- tittel, dato/tid, rom og status;
- kapasitet;
- aggregert antall billetter/gjester/reservasjoner;
- aggregert bruttoomsetning;
- aggregert antall bordbookinger;
- aggregert antall pakker/forhåndsbestillinger;
- kilde, uttrekkstid og datakvalitetsstatus.

Skal eksplisitt blokkere person- og bestillingsnivå. Kontroller også at modellprompter, logger, traces og feilmeldinger ikke inneholder rådata.

Dette er teknisk og forretningsmessig risikovurdering, ikke juridisk rådgivning. Databehandleravtale, formål, lagringstid, behandlingssted og tilgang må avklares før ekte data.

## A4 – Adapter- og avstemmingsagent

Start bare etter at A1–A3 er kontrollert og Lars har gitt en anonymisert/aggregert eksempelrapport.

Ansvar:

- tilpass `config/gastroplanner_mapping.example.yml` til dokumenterte kolonner;
- utvid adapteren minst mulig;
- koble oppsetninger primært med stabile system-ID-er;
- bruk kontrollert tittel + dato + rom bare som fallback;
- gi hver kobling `matched`, `needs_review` eller `unmatched` samt begrunnelse;
- behold intern eksport som autoritativ kilde og offentlig Teateret-data som kontroll-/berikelseskilde;
- skriv tester før eller sammen med endringen.

Ikke bygg API-klient hvis API og tilgang ikke er offisielt bekreftet.

## A5 – Analyseagent

Bruk deterministisk kode til summer, rangeringer, perioder, endringer og dekningsmål. Bruk modell bare til syntese og forslag.

Minimumsanalyse:

- topp og bunn per oppsetning, format, rom og periode der data finnes;
- kapasitetsutnyttelse når både kapasitet og salg finnes;
- utvikling over tid uten å sammenligne ufullstendige perioder som om de var komplette;
- restaurant-/arrangementskryssalg bare ved forsvarlig aggregert kobling;
- datagap, lav koblingsgrad og funn som trenger menneskelig forklaring;
- svar på de tre beslutningsspørsmålene som avtales med Teateret.

## A6 – Uavhengig kontrollagent

Kontrollerer før noe kalles ferdig:

- at hver produktpåstand har offisiell kilde;
- at «ikke dokumentert» ikke er omskrevet til «finnes ikke»;
- at hver forretningsanbefaling bygger på dokumenterte funksjoner/data;
- at ingen persondata finnes i filer, logger eller eksempler;
- at datadekning og koblingsgrad er oppgitt;
- at analyser ikke gjør ubegrunnede salgs- eller årsakspåstander;
- at live-modus, e-postsending og ekstern publisering fortsatt er deaktivert;
- at testkommandoer faktisk er kjørt før status settes til verifisert.

# Faser og beslutningsporter

## Fase 0 – Research og leverandøravklaring

Ingen innlogging og ingen datauthenting. Lever:

- `docs/research/gastroplanner-offisiell-dok-og-forretningsbruk.md`;
- funksjons-/forretningsmatrise;
- liste over dokumenterte eksport-/integrasjonsmuligheter;
- liste over spørsmål til GastroPlanner og Teaterets systemeier.

Spør leverandøren dersom offentlig dokumentasjon ikke svarer på:

1. Finnes kunde-API, og kan offisiell dokumentasjon deles?
2. Hvilke CSV/XLSX-rapporter kan eksporteres for 2025–2026?
3. Kan aggregerte rapporter sendes planlagt til en dedikert e-postadresse?
4. Følger stabile arrangements- og oppsetnings-ID-er med?
5. Kan billett, event, bord og pakker kobles på aggregert nivå?
6. Hvilke moduler og rettigheter er aktive i Teaterets konto?
7. Hvilke avtaler, underleverandører, behandlingssteder og oppbevaring gjelder?

Codex skal kontrollere fase 0 før AGY går videre.

## Fase 1 – Minste pilot

Forutsetter én godkjent, anonymisert og aggregert eksempelrapport. Lever:

- faktisk datakontrakt og kolonnemapping;
- avstemming mot `docs/research/arrangementsdata-2025-2026.md`;
- datakvalitetsrapport og koblingsgrad;
- én lokal, usendt beslutningsbrief;
- testbevis og liste over gjenværende gap.

Ingen API, postkasse, container eller automatisk tidsplan i denne fasen.

## Fase 2 – Fire ukers kontrollert utprøving

Manuell, aggregert eksport behandles ukentlig. Mål:

- gyldige rader og avviste rader;
- andel arrangementer som kobles sikkert;
- menneskelig gjennomgangstid;
- rettinger før godkjenning;
- om minst én faktisk beslutning blir enklere eller bedre;
- null persondata.

## Fase 3 – Mulig produksjon

Vurder først etter dokumentert pilotverdi:

- offisielt API eller kontrollert rapport-e-post;
- dedikert postkasse med minste tilgang;
- tidsstyrt containerjobb;
- drift, logging, sletting, backup og stoppbryter;
- fortsatt bare usendt utkast inntil en egen beslutning åpner for mer.

# Påkrevde leveranser fra AGY

1. Kildebelagt offisiell GastroPlanner-research.
2. Funksjons- og forretningsmatrise.
3. Dokumenterte ukjente forhold og leverandørspørsmål.
4. Foreslått minimumsdata og eksplisitt blokkerte felt.
5. Pilotplan med eier, mål, prisavgrensning og stoppkriterier.
6. Bare dersom fase 0 godkjennes: liten adapterendring, tester og anonymisert demo.
7. Kontrollpakke til Codex med endringsliste, kildeoversikt, testlogg, risiko og uavklarte punkter.

# Stoppregler

Stopp og be Lars/Codex om avklaring dersom:

- kilde krever innlogging eller tilgang til Teaterets konto;
- API-nøkkel, token, pakkeinstallasjon, deploy eller skytjeneste trengs;
- data kan inneholde kunder, ansatte, allergier, notater eller betalingsinformasjon;
- AGY ikke finner offisiell dokumentasjon for en avgjørende funksjon;
- løsningen krever at live-modus, utsending eller publisering aktiveres;
- en kodeendring utvider scope utover aggregert filimport og beslutningsbrief.

# Verifikasjon før kontroll hos Codex

Fra prosjektroten, dersom kode er endret:

```powershell
python -m unittest discover -s tests
python -m pytest
python -m compileall teateret_brief tests
python scripts\validate_workspace.py
```

Rapporter `STATUS: UNTESTED` dersom en kommando ikke faktisk er kjørt eller ikke fullførte.

# Prompt som kan gis direkte til AGY

> Les `handoffs/2026-08-20-gastroplanner-fase-0-handoff.md` og følg den som oppdragskontrakt. Start kun med fase 0. Undersøk GastroPlanner mot offisielle primærkilder og skriv den kildebelagte researchleveransen i prosjektet. Skill mellom verifisert, ikke offentlig dokumentert og må avklares. Ikke logg inn, ikke bruk ekte kundedata, ikke installer noe, ikke endre live-modus og ikke bygg API-klient. Lever fase 0 til Codex-kontroll før du starter adapter- eller pilotarbeid.

# Suggested skills for AGY

- `research` – primærkilder og kildebelagt researchfil.
- `llm-workflow-lens` – skille fakta, verktøyroller, minimumstest og menneskelig kontroll.
- `data-analytics:gather-business-context` – koble funksjoner til beslutninger og verdi.
- `data-analytics:create-data-context` – dokumentere felt, kilder og definisjoner.
- `data-analytics:validate-data` – kvalitet, dekningsgrad og koblingsfeil.
- `legal:compliance` – strukturere personvernspørsmål uten å gi juridisk konklusjon.
- `tdd` – adapter og avstemming etter godkjent fase 0.
- `code-review` – uavhengig kontroll av senere kodeendringer.
- `handoff` – kontrollpakke tilbake til Codex.

# Ferdigdefinisjon for fase 0

Fase 0 er ferdig når AGY har levert en kildebelagt og forretningsrettet beskrivelse av GastroPlanner, dokumentert hva som ikke kunne verifiseres, foreslått minste trygge pilot, og gitt Codex nok materiale til å godkjenne eller stoppe videre arbeid. Research alene gir ikke tillatelse til datatilgang eller implementasjon.
