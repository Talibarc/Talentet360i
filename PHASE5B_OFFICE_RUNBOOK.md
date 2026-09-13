# Phase 5B office-laptop runbook

Keep source documents, the manifest, local index, `.env`, credentials, and databases outside Git.

1. Pull the private repository: `git pull origin main`
2. Create/activate `backend/.venv`, install `backend/requirements-dev.txt`, and run `python -m pytest -q` in `backend`.
3. Create a restricted folder outside Git, such as `C:\Talent360i-Secure-Sources`.
4. Using company authentication, open approved workbook links manually; the application must not fetch URLs.
5. Download only selected approved SOP/training documents.
6. Create `manifest.json` in the secure folder using stable Source_ID and Skill_ID values, without content or credentials.
7. Configure the untracked `backend/.env`: `LLM_PROVIDER=mock`, secure `RAG_SOURCE_DIR`, local `RAG_INDEX_DIR`, and `ALLOW_SYNTHETIC_RAG=false`.
8. From `backend`, run `python offline_rag.py --manifest manifest.json`.
9. Verify ingestion status, hashes and chunk counts with the CLI and `GET /rag/sources`.
10. Test exact Skill_ID retrieval with `GET /rag/retrieve`; confirm function/skill isolation.
11. Configure Luna endpoint, key, model and version only in the local untracked `.env`.
12. Run one minimal approved Luna connectivity test.
13. Generate one Finance draft and verify the existing Finance behavior.
14. Generate one RD draft; verify citations, `Pending SME Review`, confidence as triage metadata, and `synthetic_only=false`.
15. Complete SME review and one employee assessment path; verify drafts are ineligible before approval.
16. Run backend tests, frontend tests/lint/build, `git diff --check`, secret scanning and generated-file scanning.

Faiza Microsoft List is `Unavailable — excluded from MVP`, audit-only, with zero imported records. Do not access it.
