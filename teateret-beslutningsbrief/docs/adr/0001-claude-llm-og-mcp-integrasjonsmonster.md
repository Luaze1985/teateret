# 0001: To-trinns integrasjonsmønster for Claude LLM og MCP

## Kontekst og beslutning

For å koble GastroPlanner til Claude LLM må vi balansere strengt personvern/injeksjonsforsvar med fleksibilitet for ukentlige rapporter og ad-hoc innsikt. 

Vi har besluttet et to-trinns integrasjonsmønster (Mønster C):
1. **Fase 0/1 (Beslutningsbrief):** Deterministisk rør (Python/DuckDB) henter, validerer, aggregerer og sanerer data før Claude kalles som en ren, strukturert syntesemodell uten direkte verktøytilgang eller nettverkstilgang.
2. **Fase 2/3 (Ad-hoc innsikt):** Dersom det er behov for at Claude skal svare interaktivt på ledelsens spørsmål, bygges det en lokal MCP-server på toppen av det *aggregerte datavarehuset*, aldri direkte mot GastroPlanners rå-API.

## Vurderte alternativer

- **Mønster A (Kun deterministisk rør):** Utelukker interaktiv Claude-utforskning for ledelsen.
- **Mønster B (Direkte MCP mot rå-API):** Forkastet fordi det ville gitt Claude tilgang til ufiltrerte data, økt risiko for prompt injection fra eksternt innhold og skapt sårbarhet for PII-lekkasje.

## Konsekvenser

- Claude LLM forblir fullstendig skjermet fra rå personopplysninger og ekstern nettverksrisiko.
- Fase 0 research skal kartlegge API/eksportmuligheter, men adapteren for pilot bygges filbasert og aggregert.
