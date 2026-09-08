---
name: leieavtale-utkast
description: Fyll ut Teaterets leieavtale-mal fra en limt-inn henvendelse fra artist/arrangør. Ingen e-postintegrasjon — alt limes inn manuelt, output er alltid et utkast, aldri sendt.
---

# Leieavtale-utkast (Teateret AS)

Denne skillen ligger i repoet, ikke på en persons Claude-konto — den følger
med prosjektet, ikke med Lars. Se `docs/research/kontrakt-automatisering-vurdering.md`
for hvorfor (annen oppgave enn `teateret-brief`, egen vurdering).

## Forutsetning — ingen e-postintegrasjon

Ingen tilgang til noen innboks, verken via ChatGPT-Outlook, Gmail eller
andre koblinger. Input er alltid tekst som limes inn manuelt (en e-post, en
SMS, et referat). Output er alltid et utkast noen selv kopierer ut og
sender — skillen sender aldri noe selv.

## Når denne brukes

Noen limer inn en henvendelse fra en artist/arrangør som vil leie en scene
hos Teateret, eller ber om å "lage en leieavtale"/"kontraktsutkast for
Teateret".

## Steg

0. **Avklar først om dette i det hele tatt skal formaliseres.** Teateret
   har betrodde offentlige aktører de ikke skriver formell leieavtale med,
   og andre aktører som skal kontrakteres iht. tilbud (se
   `kontraktsassistent/innhentingsskjema.md`, "Forhåndsfilter"). Er det
   uklart hvilken kategori henvendelsen tilhører — ikke gjett, si fra at
   dette må avklares med Amir før et utkast lages. Kun ved "kontrakteres
   iht. tilbud" går man videre til steg 1.

1. **Hent ut variable felt** fra det limte inn innholdet. Kun disse varierer
   fra kontrakt til kontrakt (se `kontraktsassistent/innhentingsskjema.md`):
   navn på show, artist/arrangørs firmanavn/adresse/org.nr/kontaktperson/
   e-post/telefon, dato(er), ekstra forestilling/dobbel show (ja/nei),
   bosatt utenfor Norge (ja/nei), hvilken scene (hvis nevnt).

2. **List eksplisitt hva som mangler.** Finn ALDRI på et org.nr, en adresse
   eller en dato som ikke står i input. Skriv "IKKE OPPGITT — sjekk med
   [feltnavn]" der informasjon mangler, og list de manglende feltene øverst
   i svaret.

3. **Beregn totalpris** etter formelen i `kontraktsassistent/prisberegning.md`:
   `45 000 kr × antall leiedager + 27 650 kr × antall dager med dobbel show`.
   Depositum er alltid kr 5 000, trekkes fra sluttfaktura.

4. **Sett §16-klausulen (15 % kildetrekk) kun hvis artisten er bosatt
   utenfor Norge.** Er svaret nei eller ukjent, ta med paragrafen i sin
   standardform uten å anta at den utløses.

5. **Fyll malen** (full tekst i `docs/research/repo-vurdering-mot-masterprompt.md`-
   kilden, `masterprompt grunnlag.pdf` i repo-roten) med de innhentede
   feltene. All annen tekst er fast og gjengis uendret — MED UNNTAK av §9
   (markedsføringspakken), som ikke er bekreftet lik for alle typer
   leietakere. Ikke kutt eller endre punkter i §9 selv; flagg i stedet at
   omfanget bør bekreftes med Amir hvis det er tvil.

6. **Avslutt alltid utkastet med:**
   ```
   STATUS: UTKAST — IKKE SENDT. Les gjennom før dette sendes til motpart.
   Frist for signering: [dato utkast sendes] + 7 dager (§13).
   ```

7. **Kjør utkastet gjennom kontrollør-sjekken** i
   `kontraktsassistent/agents/kontrollor.md` før det leveres videre — spesielt
   hvis dette gjøres av noen andre enn den som skal godkjenne det til slutt.

8. **Skriv aldri e-post og send aldri noe.** Lever kun utkastteksten.

## Kilde

Malen er hentet fra `masterprompt grunnlag.pdf` i repo-roten. Se også
`kontraktsassistent/` for skjema, sjekkliste og prisberegning uten KI, og
`docs/research/kontrakt-automatisering-vurdering.md` for helhetsvurderingen.
