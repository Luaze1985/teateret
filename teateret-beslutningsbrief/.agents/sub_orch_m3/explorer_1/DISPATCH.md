## 2026-08-20T07:41:06Z
You are explorer_1 for Milestone 3 (External Context Enrichment & Signals).
Your working directory: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\sub_orch_m3\explorer_1
Project root: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief
Original request: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\ORIGINAL_REQUEST.md
Scope document: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\sub_orch_m3\SCOPE.md
Parent conversation ID: 0ae1e169-aedc-4804-9a0c-7a3a6588be69

Task:
1. Read ORIGINAL_REQUEST.md and SCOPE.md.
2. Inspect the current codebase (`teateret_brief/models.py`, `teateret_brief/security.py`, `teateret_brief/fetcher.py` if present, `tests/`, etc.).
3. Design and specify:
   - Feature 10: MET.no Weather Signal Adapter (location Kristiansand 58.1467, 7.9956, User-Agent header `TeateretDecisionBrief/1.0 (kontakt@teateret.no)`, symbol codes, precipitation, temperature, wind, and demand heuristics: rainy/cold -> boost indoor theater and cafe, hot/sunny summer -> boost terrace/foajeen).
   - Feature 13: External Signal 3-Tier Cache & Fallback architecture (Tier 1: Live Safe HTTPS with timeout/SSRF/allowlist guard, Tier 2: Disk TTL cache, Tier 3: Deterministic Static Fixtures from `sample_data/fixtures/`).
4. Detail Pydantic data models, method signatures, error handling, and test requirements.
5. Write your findings and design report to `C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\sub_orch_m3\explorer_1\handoff.md`.
6. Send a message to parent (0ae1e169-aedc-4804-9a0c-7a3a6588be69) with a summary of your report.
