## 2026-08-20T07:29:08Z
<USER_REQUEST>
You are challenger_e2e_2, an adversarial code-executing verifier for the E2E Testing Track.

Read the authoritative files:
- ORIGINAL_REQUEST.md: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\ORIGINAL_REQUEST.md
- PROJECT.md: C:\Users\larse\Documents\kunde\Kundeprosjekter\Teateret\teateret-beslutningsbrief\.agents\orchestrator\PROJECT.md
- TEST_INFRA.md: C:\Users\larse\.gemini\antigravity\brain\6aef8a6e-b7c2-4b46-96e8-bfae6b74d455\TEST_INFRA.md
- tests/e2e/

Your Task:
1. Empirically verify Tier 4 real-world scenarios, CLI execution, staging isolation, and cryptographic manifest verification.
2. Run the CLI entrypoint directly across various modes and parameters, checking exit codes, stdout/stderr formatting, and filesystem outputs.
3. Verify that SHA-256 hashes generated in manifest.json match bit-for-bit with actual generated disk files.
4. Report your findings and a clear verdict (APPROVE or REQUEST_CHANGES) via send_message.
</USER_REQUEST>
