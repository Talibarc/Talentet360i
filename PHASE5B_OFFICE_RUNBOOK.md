# Final office validation update

Use the office pull/startup and final acceptance checklist in [FINAL_IMPLEMENTATION_REPORT.md](FINAL_IMPLEMENTATION_REPORT.md). Do not reseed or reset the existing office database. Correct SRC_02 through the audited **Edit skill mapping** dialog; content/chunk versions are preserved. Workbook import and TNI no longer depend on mock mode. The only live-model step is one controlled, approved-SOP Luna draft generation request after local configuration and source checks.

Keep `LLM_PROVIDER=luna`, `DEMO_IDENTITIES_ENABLED=true`, `ALLOW_SYNTHETIC_RAG=false` only for controlled validation with the backend bound to `127.0.0.1`. Never expose demo identities on public/production hosting. Missing official policy remains pending after a successful Luna test.

# Phase 5B office-laptop runbook

Keep source documents, the manifest, local index, `.env`, credentials, and databases outside Git.

1. Pull the private repository: `git pull origin main`
2. Create/activate `backend/.venv`, install `backend/requirements-dev.txt`, and run `python -m pytest -q` in `backend`.
3. Create a restricted folder outside Git, such as `C:\Talent360i-Secure-Sources`.
4. Using company authentication, open approved workbook links manually; the application must not fetch URLs.
5. Download only selected approved SOP/training documents.
6. Configure the untracked `backend/.env`: `LLM_PROVIDER=mock`, secure `RAG_SOURCE_DIR`, local `RAG_INDEX_DIR`, and `ALLOW_SYNTHETIC_RAG=false`.
7. Start both applications, sign in as Admin/L&D, and open **Bulk document ingestion**.
8. Select or drag all approved files as one batch. Review each Source_ID, source metadata, Skill_ID mappings and approved-source confirmation, then run **Validate All**.
9. Resolve rows marked **Mapping required** or **Pending source validation**, remove unwanted rows, then choose **Upload & Ingest All** and review every result.
10. Verify statuses, hashes and chunk counts in the Admin/L&D source view and `GET /rag/sources`. The manifest CLI remains an optional controlled fallback.
11. Test exact Skill_ID retrieval with `GET /rag/retrieve`; confirm function/skill isolation.
12. For controlled local validation, configure the untracked `.env` with `LLM_PROVIDER=luna`, `DEMO_IDENTITIES_ENABLED=true`, and `ALLOW_SYNTHETIC_RAG=false`, plus locally supplied Luna values. Bind the backend only to `127.0.0.1`. This combination is for local hackathon validation only and must never be used for production or public hosting.
13. Run one minimal approved Luna connectivity test.
14. Generate one Finance draft and verify the existing Finance behavior.
15. Generate one RD draft; verify citations, `Pending SME Review`, confidence as triage metadata, and `synthetic_only=false`.
16. Complete SME review and one employee assessment path; verify drafts are ineligible before approval.
17. Run backend tests, frontend tests/lint/build, `git diff --check`, secret scanning and generated-file scanning.

Faiza Microsoft List is `Unavailable — excluded from MVP`, audit-only, with zero imported records. Do not access it.
