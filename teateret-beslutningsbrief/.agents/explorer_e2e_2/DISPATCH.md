## 2026-08-20T07:20:20Z
You are explorer_e2e_2, an exploration agent for the E2E Testing Track focusing on R3 (External Signals: Weather, School Holidays, City Event Clashes, Google Places/Trends) and R4 (Automated Brief Rendering, Security Audit, Manifest, Staging, CLI).

Read the authoritative files:
- ORIGINAL_REQUEST.md: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\ORIGINAL_REQUEST.md
- PROJECT.md: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\orchestrator\PROJECT.md
- TEST_INFRA.md: C:\Users\larse\.gemini\antigravity\brain\6aef8a6e-b7c2-4b46-96e8-bfae6b74d455\TEST_INFRA.md
- teateret_brief/pipeline.py, teateret_brief/cli.py, teateret_brief/render.py, teateret_brief/security.py

Investigate and document:
1. Detailed test cases and assertions for R3: MET.no weather forecasts, Agder school holidays, city event clashes, 3-tier caching & fallback, sentiment & trends.
2. Detailed test cases and assertions for R4: Capacity utilization & dark weekday gaps, 3 prioritized recommendations, Markdown/HTML/Email rendering with disclaimers, Pre-flight PII scanning, SHA-256 cryptographic audit manifest, Atomic staging directory, RepoPaths traversal confinement, Network SourcePolicy, CLI execution (`--mode demo` and `--mode live`).
3. Tier 4 Real-World scenarios covering end-to-end user workflows.
4. Send your report back via send_message.
