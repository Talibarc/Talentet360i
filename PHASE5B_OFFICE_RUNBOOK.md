# Focused Luna response-contract retest

The user reports that office startup, provider-independent operations and SRC_02 remapping succeeded, preserving 254 chunks and version `bd73ee14ee75`. Do not repeat ingestion or remapping. The actual failed Luna payload was not supplied, so its exact mismatch remains unconfirmed.

The response hardening fixes brittle first/last-bracket slicing, specifies the canonical question JSON in the shared prompt (previously absent from the RD prompt), removes the parser's incorrect Finance provenance label, and separates contract failures (502) from unavailable/configuration failures (503). TNI, Skill Intelligence, mock generation and approval rules are unchanged.

Accepted representations: a canonical question array; an object with only `questions`; JSON-encoded strings (bounded to six normalization steps); complete JSON/plain Markdown fences; Azure ChatCompletions `choices[0].message.content` with exactly one completed assistant text choice and optional known metadata (`id`, `object`, `created`, `model`, `usage`, `system_fingerprint`); whitespace and the exact prefixes `Here is the JSON:`, `Here are the questions:`, or `JSON:`. Prefixes may precede a complete fence. Arbitrary substring extraction is not performed.

Rejected: malformed/duplicate-key/nonstandard JSON, arbitrary prose/suffixes, multiple JSON documents, unknown/ambiguous wrappers, multiple choices, truncated/filtered/tool/refusal output, content-block arrays, excessive nesting, text over 2,000,000 characters, wrong question counts, missing/extra question fields, invalid field types, blank required text, invalid A–D answer keys and invalid/duplicate options. No missing field or source reference is invented. Existing optional `rag_source` is preserved by parsing; the RD endpoint attaches trusted retrieved provenance.

Diagnostics appear in the backend terminal through `uvicorn.error`: event/category/reason, safe JSON/Python type, allowlisted structural keys, unknown-key counts, response/choice counts and sanitized validation paths. Transport failure HTTP status is included when available. Unknown keys, error messages/inputs, prompts, document text, response payloads, credentials and headers are never logged by this layer. SDK content extraction rejects incomplete responses without dumping them.

Verified locally: **208 backend tests passed** (6 existing dependency/workbook-reader warnings); **42 frontend tests passed**; frontend lint/build passed; Git whitespace and secret/generated-path scans passed. No frontend runtime/UI code changed; only API error regression tests were extended. No real Luna/network model call was made and `backend/.env` was not read or modified.

## One-call office checklist (supersedes older multi-call instructions below)

1. Preserve office configuration/database/uploads/index and connect the company VPN. Pull without resetting local changes:

```powershell
cd C:\Users\talib\Talentet360i
git status --short
git pull --ff-only origin main
cd backend
$env:LLM_PROVIDER = 'luna'
$env:DEMO_IDENTITIES_ENABLED = 'true'
$env:ALLOW_SYNTHETIC_RAG = 'false'
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Use existing approved office secret configuration; do not paste credentials into chat or logs. Demo identities remain local-only. No dependency change is required by this patch.

2. In L&D DataOps/RD Sources & Generation, check SRC_02 remains ingested with the expected mapping/version/chunks. Select `RD_PRO_01 — Item Coding`, the B2 mapping with target Moderate, 3 questions, Moderate difficulty and **Require approved SOP**.
3. Click Generate **once**. Do not make a separate connectivity generation call or automatically retry.
4. Success: expect HTTP 201 and exactly three Pending SME Review drafts. Inspect source ID, retrieved chunk citations and document version. Confirm `synthetic_only=false`; drafts must remain ineligible for assessment until SME approval.
5. Failure: stop. Record only HTTP status, the safe UI message and the `Luna ...` structural diagnostic lines. 503 indicates unavailable/configuration; 502 with `unparseable` indicates representation/JSON failure; 502 with `schema` identifies an unsupported envelope/count/field contract. Do not share full response, prompt, source text or credentials.

This patch is fixture-tested only. One controlled office Luna generation remains required; a live fix is not claimed.

---

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
