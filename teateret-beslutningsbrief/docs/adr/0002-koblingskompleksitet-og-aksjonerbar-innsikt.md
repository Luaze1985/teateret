# 0002: Koblingskompleksitet og aksjonerbar innsikt

## Kontekst og beslutning

For at dataene fra GastroPlanner og Teaterets arrangementsprogram skal ha reell forretningsverdi, må de kunne kobles sammen for å belyse kapasitet, bestselgere, ledige rom og kryssalg mot restaurant. 

Vi har besluttet en 3-delt standard for koblingskompleksitet. Rekkefølgen
speiler `match_level`-literalen i `teateret_brief/matcher.py`
(`level_1_id` → `level_2_title_date_room` → `level_3_proximity`):
1. **Nivå 1 (Direkte ID/Pakke):** Eksplisitt kobling via felles system-ID eller arrangementspakke. Dette gir høyeste tillit og direkte årsakssammenheng.
2. **Nivå 2 (Tittel + dato + rom):** Deterministisk match på normalisert arrangementstittel og dato, disambiguert på rom når flere arrangementer deler dato. Navneforskjeller håndteres via deterministisk synonymmapping, ikke via uregulert LLM-gjetting. Regnes som bekreftet kobling (`match_status="matched"`).
3. **Nivå 3 (Tids-/dato-nærhet):** Når det finnes nøyaktig ett arrangement på datoen uten tittelmatch, kobles aggregert aktivitet via nærhet i tid/dato. Dette klassifiseres og merkes i briefen som *nærhetskorrelasjon* som krever gjennomgang (`match_status="needs_review"`), aldri som bevist kryssalg.

## Konsekvenser

- Briefen leverer konkrete, aksjonerbare signaler til ledelsen (f.eks. «ledig kapasitet i biscenen fredag», «høy bordbooking ved standup»), samtidig som usikkerhet og datagap synliggjøres.
- Unngår at ledelsen tar beslutninger basert på falske årsakssammenhenger.
