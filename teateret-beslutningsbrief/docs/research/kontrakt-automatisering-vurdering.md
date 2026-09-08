---
title: "Automatisering av leieavtale-workflow (Amir/Teateret)"
date: 2026-09-06
status: draft
tags: [automatisering, kontrakt, leieavtale, epost, claude-code]
category: research
chunk_type: assessment
---

# Automatisering og forenkling: leieavtale-workflow

Dette er en egen vurdering, adskilt fra beslutningsbrief-piloten i resten av
repoet. Samme kunde (Teateret, kontaktperson Amir Shafei), men et annet
problem: utfylling og oppfølging av leiekontrakter med artister/arrangører,
ikke ukentlig salgs-/programinnsikt.

**Korreksjon først:** `masterprompt grunnlag.pdf` er ikke en masterprompt.
Det er Teaterets standard leieavtale-mal ("Leieavtale") for utleie av
Hovedscenen, Biscenen, Intimscenen og Axels lounge til artister/arrangører.

## Implementeringsstatus (kontrollert 2026-09-06)

Sjekket på nytt om malen (PDF-en) og filene under stemmer overens, og om
forslagene under faktisk er tatt i bruk:

- **PDF-en er uendret** siden forrige gjennomgang (samme filstørrelse/innhold).
  Alle tall i `kontraktsassistent/`-filene er verifisert linje for linje mot
  malen på nytt: kr 45 000/dag, kr 27 650 tillegg, kr 5 000 depositum, 50/100 %
  avbestilling, 15 % kildetrekk, 7 dagers signeringsfrist, 1 ukes frist for
  kildeskatt-dokumentasjon, og alle sal-kapasiteter (395/450, 146/176/250,
  67/76, 10 i Axels lounge). **Ingen avvik funnet** — skjema, sjekkliste og
  prisberegning implementerer malen korrekt slik den står i dag.
- **Skjema, sjekkliste, prisberegning** (quick wins uten KI, se lenger ned):
  ferdige filer, klare til bruk. Ikke noe tyder på at de faktisk er tatt i
  bruk på en reell henvendelse ennå.
- **Leieavtale-skillen er nå repo-native, ikke en personlig Claude-konto-
  skill.** Lars ba om at kunde-leveranser skal ligge i kundens repo, ikke i
  hans egen LLM-kontoskillsamling — det opprinnelige forslaget om å lagre
  den som personlig skill (`lag-leieavtale`) er derfor forlatt/ubrukt. Den
  faktiske skillen ligger nå i `.agents/skills/leieavtale-utkast/SKILL.md`,
  og virker uansett hvem som åpner en Claude Code-økt i dette repoet.
- **Ny: kontrollør-agent for leieavtale-utkast**
  (`kontraktsassistent/agents/kontrollor.md`). Samme "kontrakt for en
  rolle"-format som `agents/kontrollor.md` for beslutningsbriefen, men
  sjekker leieavtale-utkast: ingen gjettede felt, riktig pris, riktig
  §16-bruk, riktig frist. Dette er det nærmeste et konkret forslag til
  Lars sin uferdige «linse»-idé («noe som kontrollerer og hjelper kunden»)
  som er bygget så langt — men det er en agent-kontrakt, ikke selve
  linse-konseptet, som fortsatt er åpent og bør utvikles videre når Lars er
  klar for det.
- **Steg 0** (lim inn en reell henvendelse + mal i en Claude-samtale): ingen
  spor i repoet av at dette er testet på en faktisk sak ennå. Fortsatt
  anbefalt neste steg, se bunnen av notatet.
- **E-signering**: fortsatt bare research, ikke valgt eller tatt i bruk.
- **Ny forretningsregel lagt inn 2026-09-06: ikke alle henvendelser skal
  formaliseres.** Teateret har betrodde offentlige aktører de ikke skriver
  leieavtale med, og andre aktører som skal kontrakteres iht. tilbud. Dette
  er lagt inn som et "Forhåndsfilter" først i
  `kontraktsassistent/innhentingsskjema.md`, i skillens steg 0
  (`.agents/skills/leieavtale-utkast/SKILL.md`), og som sjekkpunkt 0 hos
  kontrollør-agenten. Konsekvens: §9-markedsføringspakken (12 faste punkter)
  er ikke bekreftet lik for alle typer leietakere — se "Må verifiseres".

## Fakta: hva som faktisk står i malen

Malen er 5 sider og ca. 90 % fast tekst som gjentas likt hver gang:
Teaterets egne opplysninger, sal-kapasiteter, tekniske vilkår, HMS-/rømningsklausuler,
force majeure, forsikring, billettvilkår (Tixly, kr 30 i avgift, 100 % til
arrangør), markedsføringspakken (§9, 12 faste punkter), betalingsfrister,
avbestillingsregler og verneting.

Kun disse feltene varierer reelt fra kontrakt til kontrakt:

- Navn på show/arrangement
- Artist/arrangør: navn, adresse, org.nr, kontaktperson, e-post, telefon
- Dato(er) for arrangementet
- Ekstra forestilling/dobbel show ja/nei (utløser tillegg på kr 27 650)
- Om artisten er bosatt utenfor Norge (utløser 15 % kildetrekk, §16)
- Signeringsdato

Alt annet er copy-paste av samme tekst. Det er her tid går tapt, ikke i
selve avtaleteksten.

## Repo-status (kontrollert)

- `teateret-beslutningsbrief`-repoet har ingen kobling til kontrakter i dag —
  det er bygget for salgs-/programbrief, ikke avtaleadministrasjon.
- Git-repoet har **ingen commits** (`git log` → "does not have any commits yet"),
  ingen remote, alt er untracked. Det er ikke en risiko for kontraktarbeidet
  spesifikt, men det betyr at hele beslutningsbrief-arbeidet per nå kun finnes
  som filer på denne maskinen, uten historikk eller backup. Verdt å rydde opp
  i uavhengig av dette forslaget.
- Governance-modellen i `AGENTS.md`/`CLAUDE.md` (ingen utsending uten
  godkjenning, kun godkjente kilder, menneske som siste kontrollpunkt) er et
  godt utgangspunkt å gjenbruke *prinsipielt* for kontraktarbeid, selv om
  koden ikke skal gjenbrukes direkte (se under).

## Forslag: automatisering og forenkling for Amir

1. **Strukturert innhentingsskjema i stedet for løs e-postkorrespondanse.**
   Et kort skjema (6–7 felt over) fanger nøyaktig det som varierer. I dag
   samles trolig disse feltene inn via frem-og-tilbake-e-post — det er der
   friksjonen sitter, ikke i selve dokumentet.

2. **Autoutfylt kontraktsutkast fra skjema/e-post.** Gitt de 6–7 feltene kan
   et utkast med riktig tekst genereres på sekunder, med §16 (kildetrekk) og
   §11 (tillegg for dobbel show) satt riktig automatisk ut fra ja/nei-svarene.
   Amir leser gjennom og sender selv — ingen automatisk utsending.

3. **Automatisk kostnadsberegning.** kr 45 000/dag + kr 27 650 ved ekstra
   forestilling er enkel logikk som i dag trolig regnes for hånd per kontrakt.

4. **Sjekkliste innebygd i utkastet, ikke bare i hodet.** TONO-rapportering,
   dokumentasjon av kildeskatt innen 1 uke (§16), signeringsfrist på 7 dager
   (§13) — dette er tre frister som er lette å glemme og som gir Teateret
   reell risiko (rett til å leie ut til andre, ansvar for kildeskatt) hvis de
   glipper.

5. **E-signering.** Ingenting i malen tyder på at det finnes en digital
   signeringsløsning i dag (avtalen har fysiske signaturfelt). Med 7-dagers
   frist for signering (§13) er dette trolig den enkeltendringen som sparer
   mest tid og reduserer flest tapte avtaler — og den krever ikke KI i det
   hele tatt, bare et vanlig e-signeringsverktøy.

## Vurdering: bygge inn i repoet, eller bruke Claude Code direkte

Dette er et annet problem enn det repoet er bygget for. Beslutningsbriefen
er en deterministisk matche- og aggregeringsoppgave (tall, 3-nivå matching,
DuckDB) der determinisme er poenget. Kontraktsutfylling er en
tekstforståelses- og utfyllingsoppgave — nøyaktig den typen jobb en språkmodell
er god på uten at det trengs egen pipeline-kode rundt.

**Anbefaling: ikke bygg dette inn i `teateret_brief`-pakken.** Å presse en
tekstutfyllingsoppgave inn i en kodebase bygget for deterministisk
tallmatching gir mer kompleksitet uten tilsvarende nytte, og blander to
kundeleveranser med ulik modenhet (piloten er fortsatt i spørsmålsrunde før
ekte drift, jf. `state/context/grilling_questionnaire.md`).

Foreslått vei, i den minste testbare rekkefølgen:

- **Steg 0 (nå):** Amir/du limer inn e-posten fra artist/arrangør i en
  Claude-samtale sammen med malen, får et utfylt utkast tilbake, leser
  gjennom og sender selv. Null infrastruktur, tester om utkastet faktisk
  holder mål og sparer tid.
- **Steg 1 (hvis steg 0 er nyttig noen uker på rad):** Pakk dette som en
  gjenbrukbar skill/prompt-mal (Claude Code eller Cowork) som tar
  e-postteksten som input og returnerer utkast + sjekkliste. Fortsatt
  manuelt trigget, fortsatt ingen e-posttilgang.
- **Steg 2 (bare hvis volumet faktisk krever det):** Vurder automatisk
  innlesing av henvendelser. Da bør det bygges som et eget, lite verktøy —
  gjerne med samme prinsipper som beslutningsbriefen (utkast, aldri
  autosend; menneske godkjenner), men som egen kodebase, ikke en gren av
  `teateret_brief`.

Claude Code er godt egnet til steg 1 fordi oppgaven er avgrenset og
tekstbasert. Det er ikke et argument for å erstatte repoet — de løser
forskjellige problemer for samme kunde.

## E-post-instrumentet: Amir sin adresse

Notatet du limte inn om ChatGPT/Outlook stemmer med hvordan
tilkoblingsmodeller for e-post generelt fungerer, og er relevant først fra
steg 2 over — ikke nå:

- En Outlook-kobling (ChatGPT eller tilsvarende) gir kun tilgang til **den
  ene kontoen som kobles til**, typisk `amir@teateret.no`. Organisasjons-
  godkjenning i Microsoft 365 betyr at appen er tillatt i firmaet, ikke at
  hele domenet eller alle innbokser blir lesbare.
- Dette forutsetter at `teateret.no` faktisk kjører på Microsoft 365. Er
  e-posten ren Domeneshop-webmail/IMAP, virker ikke en offisiell
  Outlook-app-kobling i det hele tatt — da må en eventuell automatisering
  (steg 2) heller bygges med IMAP-henting i egen kode, ikke en tredjeparts
  Outlook-kobling.
- Uavhengig av hvilken løsning: koble kun `amir@teateret.no`, ikke
  Domeneshop-admin-innlogging, og be om lesetilgang fremfor skrive-/sendetilgang
  så lenge målet bare er å lese henvendelser.

### Verifisert 2026-09-06: påvirker det de fire andre ansatte?

Konkret spørsmål fra Lars: hvis Amir kobler til sin egen konto (M365-sporet),
kan det gi tilgang til — eller på annen måte påvirke — e-posten til
Teaterets fire andre ansatte? Sjekket direkte mot OpenAIs egen
dokumentasjon for Outlook-koblingen, ikke bare generell Microsoft-teori:

- **Nei.** Organisasjonsgodkjenning (admin-godkjenning i Microsoft Entra)
  og individuell kontotilkobling er to separate ting. Admin-godkjenning
  åpner bare *muligheten* for at ansatte kan koble til — den kobler ikke
  noen konto selv og gir ikke ChatGPT/Claude tilgang til noen innboks.
  OpenAIs egen dokumentasjon er eksplisitt: "Microsoft permission approval
  does not enable ChatGPT actions or connect an individual user's Microsoft
  account." Hver ansatt må selv logge inn og koble til sin egen konto for at
  noe skal skje med den kontoen.
- Koblingen bruker delegerte tillatelser (`Mail.Read` m.fl.), ikke
  applikasjonstillatelser. Delegerte tillatelser er alltid bundet til
  brukeren som faktisk logger inn — appen kan bare se det denne ene brukeren
  selv har tilgang til, uansett hva som er godkjent på organisasjonsnivå.
  Applikasjonstillatelser (som ville gitt bredere tilgang) krever en helt
  annen, langt strengere godkjenningsprosess og brukes ikke av vanlige
  "koble til e-posten din"-integrasjoner som dette.
- Eneste unntak: hvis Amir *allerede*, uavhengig av dette, har fått delt
  eller delegert tilgang til en kollegas postkasse i Microsoft 365 (en helt
  separat IT-beslutning), kan koblingen hans i så fall også lese den
  postkassen — men det er et eksisterende IT-tilgangsvalg Teateret har tatt
  selv, ikke noe ChatGPT/Claude-koblingen skaper.
- **Konklusjon: bekymringen stemmer ikke**, forutsatt vanlig oppsett uten
  delte postkasser. Å koble `amir@teateret.no` påvirker verken tilgangen
  til eller synligheten av de fire andre ansattes e-post.

Kilder: [OpenAI Help Center — Outlook Email and Calendar connectors for ChatGPT](https://help.openai.com/en/articles/12512241-outlook-email-and-calendar-connectors-for-chatgpt), [OpenAI Help Center — Admin controls, security and compliance](https://help.openai.com/en/articles/11509118-admin-controls-security-and-compliance-in-apps-connectors-enterprise-edu-and-business), [m365.fm — Delegated vs. Application Permissions](https://www.m365.fm/blog/delegated-vs-application-permissions-choosing-the-right-model-for-your-app/)

## Må verifiseres før steg 2 vurderes videre

- Er `teateret.no` på Microsoft 365 eller Domeneshop-webmail/IMAP?
- Hvor mange leieavtaler inngås Teateret per måned? (Avgjør om automatisering
  utover steg 1 i det hele tatt lønner seg.)
- Finnes det allerede et e-signeringsverktøy hos Teateret, eller håndteres
  signatur i dag på papir/PDF?
- Hvem hos Teateret (Amir, eller noen andre) skal faktisk eie og bruke
  utkastene — samme spørsmål som står åpent for beslutningsbriefen i
  `CONTEXT.md`, og bør trolig svares på samtidig.
- Nøyaktig hvor grensen går mellom "betrodd offentlig aktør, ingen formell
  avtale" og "kontrakteres iht. tilbud" — hvilke konkrete aktører/typer
  faller i hver kategori.
- Om §9-markedsføringspakken (§9, 12 punkter — hjemmeside, Facebook-
  arrangement, Visit Sørlandet, skjermer/plakater, Meta Ads, nyhetsbrev,
  BYLIV-app m.fl.) faktisk leveres i sin helhet til alle typer leietakere,
  eller om noen punkter kuttes/tilpasses for enkelte aktører. Skillen er nå
  instruert til aldri å kutte §9 selv uten at dette er bekreftet med Amir.

## Anbefalt neste steg

Test steg 0 på neste reelle henvendelse: lim inn den innkommende e-posten
og denne malen i en Claude-samtale, se om utkastet er godt nok til at Amir
bare må lese og sende. Ikke bygg noe før det er testet på minst 2–3 ekte
saker.

## Quick wins uten KI (kartlagt 2026-09-06)

Brutt ut fra forslagene over: dette er tingene som ikke krever noen
språkmodell, bare et skjema/en rutine. Filene ligger i `kontraktsassistent/`.

| Tiltak | Innsats | Effekt | Fil |
|---|---|---|---|
| Strukturert innhentingsskjema | Svært lav — klart til bruk nå | Høy — fjerner frem-og-tilbake e-post for å samle info | `kontraktsassistent/innhentingsskjema.md` |
| Sjekkliste for frister (signering, kildeskatt-dok, TONO) | Svært lav — klart til bruk nå | Middels/høy — reduserer risiko for tapt avtale (§13) og feilhåndtert kildeskatt (§16) | `kontraktsassistent/sjekkliste-frister.md` |
| Prisberegningsformel | Svært lav — klart til bruk nå | Lav/middels — fjerner regnefeil, sparer noen minutter per kontrakt | `kontraktsassistent/prisberegning.md` |
| E-signering | Middels — krever valg av verktøy og ny rutine | Høy — kutter signeringstid, reduserer risiko for at 7-dagersfristen i §13 sprenges | Ikke bygget, se under |

De tre første er ferdige og kan tas i bruk med en gang — ingen godkjenning
eller anskaffelse nødvendig.

### E-signering — hva som faktisk finnes (sjekket 2026-09-06)

Ved lavt volum (noen få kontrakter i måneden) er de fleste
abonnement-baserte verktøyene overdimensjonert:

- **Visma Sign Professional**: ca. 360 kr/mnd, opptil 5 brukere og 20
  signeringer/mnd, inkluderer BankID og arkivering. Billigst av
  abonnementene i denne sammenligningen — merk at kilden er Visma Sign selv,
  så tallet bør verifiseres uavhengig før valg.
- **Posten signering**: markedsføres som betal-per-bruk uten faste
  kostnader, som passer bedre ved sporadisk volum enn et fast abonnement —
  men jeg fikk ikke hentet ut konkret pris per signatur, må sjekkes direkte
  på `signering.posten.no/priser`.
- **Penneo, Scrive, Oneflow**: 1.100–2.900 kr/mnd, bygget for
  compliance-tunge bransjer (regnskap/jus) eller høyt volum — sannsynligvis
  overkill for denne bruken.

*Vurdering:* Sjekk Posten signering og Visma Sign sin faktiske pris per
signatur direkte, ikke bare de aggregerte sammenligningssidene. Med
noen få kontrakter i måneden er betal-per-bruk trolig riktigere enn et
fast abonnement.

Kilder: [Smartbyrå — Beste verktøy for digital signering i bedrift](https://smartbyra.no/digital-signering/beste-verktoy-for-digital-signering-i-bedrift), [Visma Sign — Hva koster elektronisk signering?](https://vismasign.no/blogg/hva-koster-elektronisk-signering/), [businesswith.no — Beste elektronisk signeringstjenester 2026](https://businesswith.no/elektronisk-signering/), [Posten signering — priser](https://signering.posten.no/priser)

## Flere skill-/agent-kandidater for Teateret (forslag, ikke bygget)

Ikke bygget nå — smallest-testable-version-prinsippet tilsier å ikke bygge
mer før `leieavtale-utkast` + kontrollør er brukt på et par ekte saker.
Listet her som kandidater for senere:

- **Markedsføringssjekk-skill**: går gjennom de 12 faste punktene i §9 for
  et konkret arrangement (grafisk materiell mottatt, Facebook-arrangement
  opprettet, plakater trykket, nyhetsbrev-innlegg planlagt, osv.) og sier
  hva som er gjort/gjenstår. Ingen KI-logikk nødvendig i kjernen, men en
  skill strukturerer sjekken og kan minne om det som lett glemmes.
- **Henvendelses-triage-skill**: rask vurdering av om en ny leieforespørsel
  faktisk kan innfris (ledig dato, riktig scene-størrelse for forventet
  publikum, ikke kollisjon med annet i programmet). Krever tilgang til
  kalender-/programdata Teateret allerede har — ikke en dag-1-kandidat.
- **Oppfølgings-agent for frister på tvers av saker**: i dag sjekker
  `kontraktsassistent/sjekkliste-frister.md` én kontrakt om gangen. En agent
  som holder oversikt over *flere* saker samtidig og flagger de som
  nærmer seg 7-dagersfristen uten signatur, er nærmere det Lars beskriver
  som en «linse» — men krever et sted å holde den løpende oversikten
  (en enkel liste-fil, i det minste), som ikke finnes ennå. Naturlig neste
  skritt når/hvis «linse»-konseptet er mer avklart.
