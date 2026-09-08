---
title: "Grilling: spørrerunde før ekte pilot"
date: 2026-08-19
status: draft
tags: [grilling, pilot, beslutninger, questionnaire]
category: architecture
chunk_type: interview
---

# Slik brukes skjemaet

Kryss av i rubrikkene, stryk det som ikke gjelder, skriv fritekst der det trengs.
Alt som ikke er avkrysset regnes som ubesvart og blokkerer neste blokk.

- `[x]` = valgt
- `[?]` = usikker, må sjekkes med Teateret
- «Anbefaling:» = mitt forslag hvis du ikke har en sterkere mening

Blokk A og B er bærende. Blokk C–G kan endre seg når A og B er besvart —
ikke bruk mye tid på dem før A er låst.

---

# Funn fra koden før spørsmålene

Tre ting slo jeg opp i stedet for å spørre:

1. **De tre beslutningene har allerede et hjem i koden.**
   `config/runtime.yml` har feltet `decision_questions` med tre oppføringer, og
   `teateret_brief/pipeline.py:36` begrenser det til 1–5. Feltet hashes inn i
   manifestet (`decision_questions_sha256`) og mates til både analytiker og
   kontrollør (`teateret_brief/agents.py:214`). Mekanismen finnes.
   Innholdet er plassholder.

2. **Dagens tre er analysespørsmål, ikke beslutninger.** De lyder i dag:
   *«Hvilke arrangementstyper viser sterkest etterspørsel …»*,
   *«Hvilke ferske markedssignaler er relevante …»*,
   *«Hvor finnes det et konkret program- eller markedshull …»*.
   Alle tre kan besvares uten at noen gjør noe. Det er derfor demo-outputen
   ender på «vurder om … bør møtes med et avgrenset tiltak».

3. **Salgssiden kan i dag regne ut tre ting og ikke mer**
   (`teateret_brief/analytics.py`): sum per måltall, rangering per arrangement,
   og prosentendring fra forrige periode. Alt annet — kapasitet, utsolgtgrad,
   dekningsbidrag, gjenkjøp — finnes ikke og må inn via eksporten.

**Språkkollisjon å avklare:** `CONTEXT.md` sier «beslutninger»,
`config/runtime.yml` sier `decision_questions`, `agents/analytiker.md` sier
«handlinger». Tre ord, og det er uklart om de betyr det samme. Blokk A låser
dette.

---

# Blokk A — De tre beslutningene (bærende)

Uten denne blokken har hverken måleopplegget eller stoppkriteriene i
`docs/implementation-plan.md` et suksesskriterium.

## A1. Hvilke beslutninger skal briefen gjøre lettere?

Kryss av alle som er reelle. Vi rangerer i A6.

- [ ] **Programvalg** — hvilke arrangementer bookes/gjentas neste kvartal
- [ ] **Markedsføringsprioritet** — hvilket arrangement får ukens push
- [ ] **Timing** — når legges billetter ut, når økes trykket
- [ ] **Kapasitet/oppsett** — sal-oppsett, antall forestillinger, dublering
- [ ] **Prising** — pris, rabatter, pakker
- [ ] **Mat/drikke koblet til arrangement** — meny, bemanning, forhåndsbestilling
- [ ] **Samarbeid/partnerskap** — hvem tar vi kontakt med
- [ ] **Ingen av disse — noe annet:** ______________________________

*Anbefaling:* markedsføringsprioritet + mat/drikke-kobling. Begge er ukentlige,
begge er reversible, og begge kan faktisk mates av dataene systemet har i dag.
Programvalg er kvartalsvis og tåler ikke en ukentlig kadens.

## A2. Hvem tar hver av beslutningene i A1?

- [ ] Amir alene
- [ ] Markedsansvarlig alene
- [ ] Programansvarlig
- [ ] Kjøkken-/driftsansvarlig
- [ ] Amir + én til i samtale
- [ ] Annet: ______________________________

*Anbefaling:* én navngitt person per beslutning. To eiere betyr null eiere.

## A3. Når i uka tas beslutningen i dag?

- [ ] Fast møte, ukedag: ____________
- [ ] Løpende, ingen fast tid
- [ ] Månedlig
- [ ] Vet ikke — må observeres

*Anbefaling:* briefen må lande minst 12 timer før beslutningspunktet. Finnes det
ikke noe fast beslutningspunkt, er ukentlig kadens feil produkt.

## A4. Hva er beslutningsgrunnlaget i dag, uten briefen?

- [ ] Magefølelse/erfaring
- [ ] Tall fra GastroPlanner hentet manuelt
- [ ] Facebook/Instagram-innsikt
- [ ] Billettsystem-rapporter
- [ ] Ingenting systematisk
- [ ] Annet: ______________________________

## A5. Hva skal til for at Amir faktisk endrer en beslutning?

- [ ] Et tall som avviker mer enn ____ % fra forrige periode
- [ ] Et konkurrentsignal (noen andre gjør noe nytt)
- [ ] En anbefaling med kilde han kan sjekke selv
- [ ] En påminnelse om noe han hadde glemt
- [ ] Vet ikke

*Anbefaling:* dette er den viktigste raden i skjemaet. Terskelen for handling er
det anbefalingene må skrives mot. Uten den blir hver anbefaling en
«vurder å vurdere».

## A6. Ranger de tre som skal inn i `config/runtime.yml`

1. ______________________________________________
2. ______________________________________________
3. ______________________________________________

*Anbefaling:* skriv dem som beslutninger med et objekt, ikke som analysespørsmål.
«Hvilket av neste ukes arrangementer skal ha markedsbudsjettet?» slår
«Hvilke arrangementstyper viser sterkest etterspørsel?».

## A7. Skal «beslutning», «beslutningsspørsmål» og «handling» bety det samme?

- [ ] Ja — velg ett ord, resten går i `_Avoid_` i `CONTEXT.md`
- [ ] Nei — de er tre nivåer og skal defineres hver for seg
- [ ] Vet ikke

*Anbefaling:* nei, tre nivåer. **Beslutning** = det Amir velger. **Signal** =
det systemet fant. **Anbefaling** = systemets forslag til én beslutning.
«Beslutningsspørsmål» strykes som ord.

---

# Blokk B — Hvordan vi vet om det virket

## B1. Etter fire uker, hva må være sant for at piloten kalles vellykket?

- [ ] Minst ____ av 4 briefs førte til en dokumentert beslutning
- [ ] Amir bruker under ____ minutter per brief
- [ ] Under ____ % av anbefalingene måtte rettes faktafeil i
- [ ] Amir vil betale for fortsettelse
- [ ] Annet: ______________________________

*Anbefaling:* 2 av 4 førte til en beslutning som ikke ville blitt tatt ellers.
Alt annet er sekundært.

## B2. Hvem noterer utfallet av hver brief?

- [ ] Amir, i en linje nederst i e-posten
- [ ] Lars, i en logg
- [ ] Ingen — vi spør muntlig etter fire uker
- [ ] Annet: ______________________________

*Anbefaling:* Amir, én linje, i utkastet selv. Blir det en egen loggbok,
skjer det ikke.

## B3. Akseptabel redigeringsmengde per brief?

- [ ] Skal kunne brukes uendret
- [ ] Lett språkvask er greit
- [ ] Opp til halvparten kan skrives om
- [ ] Spiller ingen rolle, det er lesingen som teller

## B4. Hva er en feil, og hvor mange tåler vi?

- [ ] Feil tall = kritisk, null toleranse
- [ ] Feil tolkning av kilde = alvorlig
- [ ] Irrelevant anbefaling = irriterende, men ok
- [ ] Terskel for å stanse piloten: ____________

## B5. Hva gjør vi hvis ingen av de fire ukene ga en beslutning?

- [ ] Stopper — dette er stoppkriteriet i `docs/implementation-plan.md`
- [ ] Justerer de tre beslutningene og kjører fire til
- [ ] Bytter format (møteagenda i stedet for e-post)
- [ ] Annet: ______________________________

*Anbefaling:* stopp, og si det til Teateret på forhånd. Det gjør piloten
troverdig og gjør et nei billig for begge parter.

---

# Blokk C — Kilder

Avhenger av blokk A. `config/sources.yml` har i dag én aktivert kilde:
Teaterets eget program.

## C1. Hvilke kildetyper skal med?

- [ ] Teaterets eget program (allerede aktiv)
- [ ] Lokale kulturkalendere — hvilke: ____________
- [ ] Kommunens arrangementsoversikt
- [ ] Navngitte konkurrentscener — hvilke: ____________
- [ ] Bransjenyheter/nasjonale trender
- [ ] Lokalavis
- [ ] Turist-/reiselivssider
- [ ] Annet: ______________________________

## C2. Er det greit å overvåke navngitte konkurrenter?

- [ ] Ja, det er offentlige sider
- [ ] Ja, men det skal ikke stå i briefen hvem
- [ ] Nei — for tett miljø
- [ ] Må avklares med Amir

*Anbefaling:* spør. I et lite kulturmiljø er dette et relasjonsspørsmål, ikke et
juridisk et, og det er ikke din vurdering å ta på Teaterets vegne.

## C3. Hvor gammelt kan et signal være før det er verdiløst?

- [ ] Under 7 dager
- [ ] Under 14 dager
- [ ] Under 30 dager
- [ ] Spiller ingen rolle

## C4. Hva skal skje når en kilde slutter å svare?

- [ ] Nevnes i briefen, kjøringen fortsetter (slik det er i dag)
- [ ] Varsle Lars separat
- [ ] Stoppe kjøringen
- [ ] Annet: ______________________________

## C5. Antall kilder i pilot?

- [ ] 3–5
- [ ] 5–10 (som `docs/implementation-plan.md` antar)
- [ ] 10+

*Anbefaling:* 5. Under det blir briefen tynn, over det blir godkjenningsjobben
til Teateret større enn nytten.

---

# Blokk D — Salgsdata fra GastroPlanner

Dagens forventede skjema (`config/gastroplanner_mapping.example.yml`):
`Dato;Arrangement;Reservasjoner;Omsetning`.

## D1. Hvilke felt finnes faktisk i eksporten?

- [ ] Dato
- [ ] Arrangement/tittel
- [ ] Antall reservasjoner
- [ ] Antall gjester (≠ reservasjoner)
- [ ] Omsetning
- [ ] Kapasitet / maks antall
- [ ] Bookingkanal (nett, telefon, drop-in)
- [ ] No-show / kansellering
- [ ] Mat- vs drikkeomsetning
- [ ] Tidspunkt på døgnet
- [ ] Annet: ______________________________

*Merk:* uten **kapasitet** kan systemet ikke si om et arrangement gikk bra —
bare om det solgte mye. 84 reservasjoner er en suksess i en sal på 90 og en
fiasko i en sal på 300.

## D2. Aggregeringsnivå

- [ ] Én rad per arrangement
- [ ] Én rad per dag
- [ ] Én rad per uke
- [ ] Rådata per booking (**avvises av datapolicyen**)

## D3. Hvor langt tilbake går historikken?

- [ ] Under 3 måneder
- [ ] 3–12 måneder
- [ ] Over 12 måneder (gir sesongsammenligning)

## D4. Hvordan kommer eksporten inn i systemet?

- [ ] Amir laster ned og legger i avtalt mappe
- [ ] Lars henter manuelt hver uke
- [ ] Automatisk eksport fra GastroPlanner — bekreftet av leverandør? [ ] ja [ ] nei
- [ ] Annet: ______________________________

## D5. Hva skjer med eksporten etter kjøring?

- [ ] Slettes etter hver kjøring
- [ ] Beholdes i pilotperioden, slettes etterpå
- [ ] Beholdes
- [ ] Må avklares

## D6. Skal mat/drikke kobles til arrangement i anbefalingene?

- [ ] Ja — det er halve poenget med GastroPlanner-koblingen
- [ ] Nei — hold det til billetter/reservasjoner
- [ ] Senere

---

# Blokk E — Leveranse og arbeidsflyt

## E1. E-post- og filplattform

- [ ] Microsoft 365
- [ ] Google Workspace
- [ ] Annet: ____________
- [ ] Vet ikke

## E2. Hvem mottar utkastet i piloten?

- [ ] Bare Amir
- [ ] Amir + markedsansvarlig
- [ ] Ledergruppa
- [ ] Annet: ______________________________

*Anbefaling:* bare Amir i fire uker. Flere mottakere gjør at ingen eier
tilbakemeldingen.

## E3. Når skal den ligge klar?

Ukedag: ____________  Klokkeslett: ____________

## E4. Format

- [ ] E-postutkast (som i dag)
- [ ] PDF-vedlegg
- [ ] Møteagenda-punkt
- [ ] Delt dokument
- [ ] Annet: ______________________________

## E5. Hvem er godkjenneren når Lars ikke er det lenger?

Navn/rolle: ______________________________

## E6. Hva skjer med briefen etter at den er lest?

- [ ] Arkiveres i `runs/`
- [ ] Kopieres inn i Teaterets eget system
- [ ] Slettes
- [ ] Ikke tenkt på

---

# Blokk F — Personvern og drift i pilotfasen

## F1. Hvor kjører piloten?

- [ ] Din maskin, manuell kjøring hver uke
- [ ] Teaterets maskin
- [ ] Sky (utløser fase 2-kravene i `docs/implementation-plan.md`)

*Anbefaling:* din maskin, manuell kjøring. Sky i pilotfasen drar inn
databehandleravtale, tilgangsstyring og kill switch for tidlig.

## F2. Inneholder eksporten personopplysninger?

- [ ] Nei — kun aggregerte tall
- [ ] Ja — må anonymiseres før den kommer inn
- [ ] Vet ikke

*Merk:* er svaret nei, faller mesteparten av personvernkravene i
`outputs/production-readiness-checklist.md` bort for piloten. Det er verdt å få
bekreftet skriftlig.

## F3. Lagringstid for `runs/`

- [ ] Slettes etter piloten
- [ ] 3 måneder
- [ ] 12 måneder
- [ ] Annet: ____________

## F4. Er det greit at teksten går gjennom Anthropic?

- [ ] Ja, når det bare er offentlige kilder + aggregerte tall
- [ ] Ja, men det må stå skriftlig hva som sendes
- [ ] Nei — da må vi kjøre lokal modell
- [ ] Må avklares

## F5. Hvem eier koden etter piloten?

- [ ] Lars — Teateret får bruksrett
- [ ] Teateret
- [ ] Delt
- [ ] Ikke avklart

---

# Blokk G — Kommersiell avgrensning

## G1. Hva er inkludert i pilot på ~10 000 kr?

- [ ] Ett arbeidsmøte
- [ ] Tilpasning til én CSV-eksport
- [ ] Godkjent kildeliste
- [ ] Fire ukentlige kjøringer
- [ ] Oppsummering med anbefaling om videre løp
- [ ] Annet: ______________________________

## G2. Hva er eksplisitt utenfor?

- [ ] Automatisk utsending
- [ ] Skydrift
- [ ] GastroPlanner-API
- [ ] Dashboard
- [ ] Flere enn de avtalte kildene
- [ ] Annet: ______________________________

## G3. Hvem er kontaktperson og beslutningstaker hos Teateret?

Navn: ____________  Rolle: ____________

## G4. Hva skjer hvis piloten viser at det ikke virker?

- [ ] Vi stopper, ingen videre fakturering
- [ ] Vi justerer og kjører fire uker til (pris: ____________)
- [ ] Ikke avtalt

*Anbefaling:* si «vi stopper» høyt før piloten starter.

## G5. Kan mønsteret gjenbrukes til andre scener?

- [ ] Ja, mønsteret er ditt å gjenbruke
- [ ] Ja, men ikke til Teaterets nærmeste konkurrenter
- [ ] Nei
- [ ] Ikke avtalt

---

# Etter utfylling

Når blokk A er besvart oppdaterer vi:

- `CONTEXT.md` — språket fra A7, og de tre beslutningene erstatter det åpne
  spørsmålet
- `config/runtime.yml` — `decision_questions` får ekte innhold
- `agents/analytiker.md` — kontrakten må si hvilken klasse beslutninger
  anbefalingene mater
- eventuell ADR i `docs/adr/` hvis A1 velger bort noe som er dyrt å reversere
