# Talent360i local foundation

Phase 1 provides a testable FastAPI/SQLite backend and the existing React/Vite starter. No business frontend, evidence, manager confirmation, dashboards, or new gamification were built in this phase.

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
backend/.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

API docs: <http://127.0.0.1:8000/docs>. Health: <http://127.0.0.1:8000/health>.

Run the starter frontend in another terminal:

```powershell
npm.cmd --prefix frontend run dev
```

The database defaults to ignored `backend/talent360i.db`; `DATABASE_URL` can select another SQLite location. Test configuration uses `sqlite:///:memory:` before importing the app, so tests do not access the normal database. Do not use real employee records for personal-laptop testing. Existing endpoints still lack role/ownership authorization; keep this phase on loopback with synthetic data.

## Run Phase 1 checks

```powershell
backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests -q
backend/.venv/Scripts/python.exe -m pip check
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

The test suite creates synthetic roles/users, generates mock drafts, approves/rejects them, assigns eligible approved questions, submits responses, checks persisted scores, and reads detailed TNI. Temporary fictional workbooks exercise learning joins. Tests disable dotenv loading, isolate SQLite, and prohibit external socket connections; Windows event-loop loopback connections are allowed.

For manual API testing, create a synthetic role, skill, mapping and employee through `/docs`, generate questions with the mapping ID, approve drafts, assign an assessment, submit one answer per assigned question, then retrieve `/users/{employee_id}/tni`. Here `employee_id` is the numeric user database ID. Without a supported workbook skill mapping, TNI explicitly returns no learning resources. Nothing auto-imports or repairs the source workbooks.

## Provider and result behavior

- Mock questions are deterministic fictional exercises labelled synthetic, mapped to the requested skill/level. They bypass company RAG and do not claim SOP provenance or production assessment validity.
- Luna continues through the unchanged `llm_service.py` transport. The new provider boundary validates question count/options and structured TNI. No live Luna call was made during Phase 1.
- Detailed TNI includes provisional current/target levels, gap, development focus, next steps, limitations, and mapped learning resources. Scoring is deterministic application code, never an LLM decision.
- Learning lookup uses exact source skill-name/ID joins: Finance Skill_Master → Training_Skill_Map → Training_Catalogue, and DataOps Skill Master → SOP & Learning Mapping. Titles/URLs/citations come only from source rows; ambiguous or absent joins return no resources. Source level/review metadata is preserved where available. These are skill-mapped candidates, not a claimed level-specific or approved curriculum.
- The inherited score bands remain provisional: at least 95% gives target level; above 80% gives target minus one with the existing level-one floor; otherwise target minus two with a zero floor. A zero target stays zero. This is tested behavior, not certification against company policy. Critical-fail policy remains unresolved.
- Blank targets are Not Expected. They cannot generate questions or receive/submit assessments and are excluded from TNI. Duplicate answer IDs are rejected. Assessment selection filters approved status and target level; randomization and immutable question versions remain later work.

`NEXT_STEPS.md` contains verified results, every changed file, and unresolved blockers. `PROJECT_CONTEXT.md` retains the initial audit and stable requirements. No dependencies, environments, databases, secrets, caches, or build output are intended for Git.
