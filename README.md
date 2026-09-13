# Talent360i skills and development workspace

Phase 5A adds a provider-independent offline RAG foundation for RD/DataOps. `backend/offline_rag.py` ingests only manifest-approved PDF, DOCX, PPTX or text files beneath `RAG_SOURCE_DIR`, writes a Git-ignored deterministic index, and retrieves by exact function, Skill_ID, proficiency, approval and synthetic policy. Workbook URLs remain metadata and are never fetched. Finance keeps its validated workbook behavior.

Phase 4 adds read-only, traceable imports from the supplied Finance and RD/DataOps workbooks to the responsive React/TypeScript and FastAPI application. Stable workbook keys, sheet/row provenance, review status, source limitations and SME policy safeguards are retained. Unsupported records remain blocked rather than being inferred. See [backend/README.md](backend/README.md) for demo identities, role permissions and the full API walkthrough.

## Install on Windows

Verified with Python 3.14.6 and Node 24.18.0. Run these commands in the repository root:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
npm.cmd --prefix frontend ci --cache .cache/npm --no-audit --no-fund
```

`requirements.txt` locks runtime dependencies; `requirements-dev.txt` adds the test dependencies. The `.in` files record the direct dependency inputs. Use the locked `.txt` files for repeatable installation. Other Python/OS combinations have not been verified.

## Configure and start

Copy `backend/.env.example` to `backend/.env` **only if `.env` does not already exist**, preserving local secrets. Mock is the default and requires no credentials:

```text
LLM_PROVIDER=mock
```

On the company laptop, edit only `backend/.env`:

```text
LLM_PROVIDER=luna
LUNA_BASE_URL=<company endpoint stored locally>
LUNA_API_KEY=<company key stored locally>
LUNA_MODEL=<configured model>
```

Restart the backend after configuration changes. Existing process environment variables take precedence over `.env`; clear stale overrides if switching via the file. Legacy `CIS_*` values remain supported when the corresponding `LUNA_*` value is blank/missing. Optional `LUNA_API_VERSION` retains the original integration default when blank.

```powershell
$env:LLM_PROVIDER = 'mock'
$env:PYTHON_DOTENV_DISABLED = '1'
$env:DATABASE_URL = 'sqlite:///C:/Users/talib/Talentet360i/backend/phase4-demo.sqlite'
backend/.venv/Scripts/python.exe backend/seed_workbook_demo.py
backend/.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Keep this backend terminal open. Then start Vite in a second terminal. If Vite shows `ECONNREFUSED 127.0.0.1:8000`, FastAPI is not running yet; start the three commands above and refresh the browser.

API docs: <http://127.0.0.1:8000/docs>. Health: <http://127.0.0.1:8000/health>.

Run the frontend in another terminal:

```powershell
npm.cmd --prefix frontend run dev -- --strictPort
```

The database defaults to ignored `backend/talent360i.db`; `DATABASE_URL` can select another SQLite location. Tests use memory/temporary SQLite, not the normal database. The protected API requires `X-Demo-User-Id` and enforces role/ownership scope. This loopback-only identity selector is for synthetic demos, not production authentication. Do not use real employee records on the personal laptop.

## Run checks

```powershell
backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests -q
backend/.venv/Scripts/python.exe -m pip check
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

The test suite creates synthetic roles/users, generates mock drafts, approves/rejects them, assigns eligible approved questions, submits responses, checks persisted scores, and reads detailed TNI. Temporary fictional workbooks exercise learning joins. Tests disable dotenv loading, isolate SQLite, and prohibit external socket connections; Windows event-loop loopback connections are allowed.

For manual API testing, select the seeded Reviewer, Manager, Employee and Leader IDs in `/docs` using the header appropriate to each action. Follow the backend walkthrough through generation, review, assignment, submission, TNI, evidence, manager confirmation and aggregates. Here `employee_id` is the numeric user database ID. Missing learning mappings produce no recommendations; nothing auto-imports or repairs the source workbooks. Phase 3 verifies frontend tests, lint, production build, and all backend regressions.

## Provider and result behavior

- Mock questions are deterministic fictional exercises labelled synthetic, mapped to the requested skill/level. They bypass company RAG and do not claim SOP provenance or production assessment validity.
- Luna continues through the unchanged `llm_service.py` transport. The new provider boundary validates question count/options and structured TNI. No live Luna call was made during any implementation phase.
- Detailed TNI separates calculated and official manager-confirmed levels and includes targets, gaps, unassessed skills, next steps and mapped learning resources. Scoring is deterministic application code, never an LLM decision.
- Learning lookup uses exact source skill-name/ID joins: Finance Skill_Master → Training_Skill_Map → Training_Catalogue, and DataOps Skill Master → SOP & Learning Mapping. Titles/URLs/citations come only from source rows; ambiguous or absent joins return no resources. Source level/review metadata is preserved where available. These are skill-mapped candidates, not a claimed level-specific or approved curriculum.
- Legacy synthetic assessments retain their tested provisional score bands. Workbook-backed results calculate an objective score but leave proficiency and skill gaps pending because neither workbook contains an approved score-to-level policy. A difficult/critical error is retained as a review insight and does not automatically fail the assessment.
- Blank targets are Not Expected. They cannot generate questions or receive/submit assessments and are excluded from TNI. Duplicate answer IDs are rejected. Assessment selection is randomized across approved questions for the mapping/level and stores frozen question/policy snapshots. Question revisions and decisions are retained.

`NEXT_STEPS.md` contains verified results, every changed file, and unresolved blockers. `PROJECT_CONTEXT.md` retains the initial audit and stable requirements. No dependencies, environments, databases, secrets, caches, or build output are intended for Git.

## Use the Phase 4 frontend

Open http://127.0.0.1:5173. Select a synthetic identity by role/function; the application discovers seeded IDs from the mock-only loopback endpoint `/demo/identities`. It never assumes numeric database IDs. Every protected request uses the centralized API client and `x-demo-user-id`. Switching identities remounts the workspace and clears prior role data. Reload returns to identity selection.

The Vite server proxies `/api` to `http://127.0.0.1:8000`. Keep both servers local. Production build output is in ignored `frontend/dist`; deployment must provide the same `/api` reverse-proxy mapping and appropriate production authentication. This phase does not publish or deploy the app.

For an isolated synthetic demo database, set `DATABASE_URL` before both seed and backend startup:

```powershell
$env:LLM_PROVIDER = 'mock'
$env:PYTHON_DOTENV_DISABLED = '1'
$env:DATABASE_URL = 'sqlite:///C:/Users/talib/Talentet360i/backend/phase3-demo.sqlite'
backend/.venv/Scripts/python.exe -B backend/seed_demo.py
backend/.venv/Scripts/python.exe -B -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Adjust the absolute database path if your checkout is elsewhere. The Phase 3 visual checks used this isolated, ignored database. The seed does not import the supplied workbooks or manufacture the 13 missing Finance references.

### Presentation walkthrough

1. **Admin/L&D:** inspect source health, validate workbooks, inspect existing mappings, and generate synthetic question drafts. Optional Finance context retrieval requires exact supplied names and fails clearly if unavailable. Publish a SkillQuest before qualifying activity occurs.
2. **SME/Reviewer:** select a pending draft, inspect options, answer rationale and provenance, edit a revision if needed, and approve/reject with comments. History retains frozen revisions.
3. **Manager or Admin/L&D:** assign approved questions to an employee using the role/skill selections. The question count must not exceed available approved questions.
4. **Employee:** complete the assessment, inspect the deterministic score and provisional level, and open Skills & learning for TNI. Only source-supported learning resources are linked; no mapping means no recommendation.
5. **Employee / Manager:** submit text/link evidence, send it back with comments, revise it, and confirm evidence. Confirm the assessment result after linked evidence is accepted. Result re-review is available for sent-back assessments.
6. **Leader:** inspect confirmed-only distribution, gaps and the skill/level heatmap. Filter by function, role, team, hub, skill and level. No individual leaderboard exists.
7. **All roles:** inspect scoped notifications and audit history. Employees can claim completed quests and see XP history; XP never changes proficiency.

Loading skeletons, empty states, inline errors, success messages, native accessible dialogs, keyboard focus, and responsive navigation are included. HTTP 401/403/404/409/422 have centralized guidance; backend details explain source and workflow conflicts. Draft assessment answers are held only while the assessment dialog stays open.

### Verified Phase 4 checks

- Backend: **101 passed**, including every Phase 3 regression, 0 failures/errors; 4 warnings from upstream libraries/workbook extensions.
- Frontend: **25 passed**, 0 failures; lint and production build exit 0.
- Import: fresh database **382 source records**; repeat import **0 changes**. Finance imports 28 skills, 9 selected roles, 12 role-description records, 60 mappings, 49 safe questions and 30 learning mappings. RD imports 38 skills, 3 bands, 114 matrix mappings and 38 learning metadata records. The Faiza question source is retained as an audit reference with status `Unavailable — excluded from MVP` and 0 imported records.
- Browser: Finance and DataOps Employee, Reviewer, Manager and Leader views plus Admin/L&D were verified against the fresh workbook database. Empty/source-limitation states and confirmed-only reporting render correctly.
- Original Luna transport/config/provider behavior and both authoritative workbooks are preserved. The SME clarification workbook remains outside Git. No Luna key was requested and no live Luna call was made.

See `NEXT_STEPS.md` for exact checks, changed files, known source limitations, and repository hygiene details.
