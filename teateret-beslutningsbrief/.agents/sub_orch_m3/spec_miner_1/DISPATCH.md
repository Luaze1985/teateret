## 2026-08-20T07:41:06Z
You are spec_miner_1 for Milestone 3 (External Context Enrichment & Signals).
Your working directory: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\sub_orch_m3\spec_miner_1
Project root: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief
Original request: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\ORIGINAL_REQUEST.md
Scope document: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\sub_orch_m3\SCOPE.md
Parent conversation ID: 0ae1e169-aedc-4804-9a0c-7a3a6588be69

Task:
1. Read ORIGINAL_REQUEST.md and SCOPE.md.
2. Mine specifications and design implementation for:
   - Feature 14: Google Places Sentiment Adapter (GBP rating, review counts, sentiment topic extraction, review text parsing, and MANDATORY strict reviewer name redaction replacing names with `[ANMELDER]`).
   - Feature 15: Google Trends Agder Adapter (Region `NO-42`, search keywords such as "teater kristiansand", "restaurant kristiansand", "konsert kristiansand", relative interest metrics and trend direction).
   - Feature 16: Schema.org Event Scraper / Parser (Extracting `schema.org/Event` JSON-LD from HTML or JSON payloads, extracting startDate, endDate, name/title, location, ticket status: InStock, SoldOut, PreOrder).
3. Specify static fixtures for zero-network testing (`sample_data/fixtures/`), Pydantic models, and integration tests.
4. Write your specification and design report to `C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\sub_orch_m3\spec_miner_1\handoff.md`.
5. Send a message to parent (0ae1e169-aedc-4804-9a0c-7a3a6588be69) with a summary of your report.
