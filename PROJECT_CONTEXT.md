# Talent360i project context and repository audit

## Phase 4 source integration status — 2026-09-13

Phase 4 imports the two authoritative repository workbooks through stable source keys and records workbook, sheet, row, fingerprint and source metadata. Imports are read-only and idempotent. Finance review status controls eligibility; incomplete or referentially invalid records are skipped with exact reasons. RD blank targets are `Not Expected` and never create gaps. The Faiza list has status `Unavailable — excluded from MVP`; it remains an audit reference only and contributes 0 imported records.

The SME clarification register confirms a 20-question start with 6 Difficult, 8 Moderate and 6 Easy questions, difficult/critical mistakes as review insights, at least 70% new reassessment questions, all required-role-skill coverage, and additional evidence plus manager/SME confirmation for Expert. AI confidence is preserved only for reviewer triage. Where the source pool or policy cannot satisfy these rules, the backend returns an explicit conflict and leaves proficiency pending.

Verified Phase 4 state: 382 source records on a fresh database and 0 changes on repeat import; 101 backend tests and 25 frontend tests pass; lint and production build pass. Browser checks cover both functions and all five role experiences. Luna was not called. The final SME audit records the Faiza reference as `Unavailable — excluded from MVP`, audit reference only, with 0 imported records.

Audit date: 2026-09-12. Baseline commit: `a953cd2`. The findings below describe the initial repository before implementation. The user subsequently authorized Phase 1 and Phase 2 backend work. See NEXT_STEPS.md for current verified results, README.md for setup, and backend/README.md for the protected demo API. The historical status matrix below is not a description of the updated code.

## Stable requirements

Build one deployable skill-assessment application for Finance and DataOps. Preserve the existing React/TypeScript frontend, FastAPI backend, SQLite MVP database, and service-based architecture. Do not introduce Power Apps. Enterprise SSO and production integrations are roadmap items, not MVP blockers; MVP authorization and privacy still apply.

Required experiences: Admin/L&D, SME/Reviewer, Employee, Manager, and Leader.

1. Generate schema-valid questions mapped to skill and proficiency, with options and correct answers. Internal skills require retrieval from approved SOP/training documents and durable source traceability.
2. Reviewers edit, approve, or reject drafts. Only approved questions enter assessments. Record decision actors, timestamps, reasons, and question versions.
3. Assign/randomize assessments, persist responses, score deterministically, and apply configured critical-fail rules.
4. Derive achieved skill levels using supplied rules, compare with role targets, and show gaps, training needs, and supplied learning resources.
5. Leaders see confirmed skill distributions and gaps by team, function, role, and hub, within their authorized scope. No public individual leaderboard.
6. Employees upload or submit evidence against skills, with persisted status and history.
7. Managers confirm or send back skill/evidence results. Audit decisions; only confirmed levels feed official leader reporting.

Also required: in-app notifications, audit history, SkillQuest/gamification, role-to-skill-to-target mappings, and human SME/manager oversight. XP measures engagement only and must not determine official proficiency.

## Source and confidentiality rules

The two supplied Excel workbooks and supplied training/SOP documents are authoritative. Do not invent missing mappings, courses, scoring rules, or data. A blank target means **Not Expected**, distinct from numeric zero. Recommendations must be supported by supplied learning data.

Use only masked/synthetic data outside the company laptop. Never display, commit, or modify API keys. Ignore virtual environments, Python caches, cache directories, and database binaries during inspection. Workbook structure and aggregate validation were inspected locally; source records and personal data are not reproduced here. The audit does not certify that the tracked workbooks are masked or approved for personal-laptop use.

Required future configuration boundary:

```text
Personal laptop: LLM_PROVIDER=mock
Company laptop:  LLM_PROVIDER=luna
                 LUNA_BASE_URL=<local secret>
                 LUNA_API_KEY=<local secret>
                 LUNA_MODEL=<configured model>
```

Switching must require environment changes only. Mock question and TNI responses must be deterministic, realistic, and schema-valid so non-LLM workflows can be exercised without company API access. This boundary is not implemented yet.

## Actual architecture

- `frontend`: React 19 + TypeScript + Vite starter. The rendered UI is a counter and template links. Router, charts, and icon packages are declared but business screens and API integration are absent.
- `backend/main.py`: FastAPI routes for health, roles, skills, mappings, users, workbook validation, Finance context retrieval, question generation/review, assessments, and TNI. CORS allows local Vite origins. No authentication or authorization dependencies exist.
- `backend/database.py`: SQLAlchemy engine/session configured to `backend/talent360i.db`. Importing `main.py` invokes `Base.metadata.create_all`; no migrations or database configuration override exists.
- `backend/models.py`: seven tables: User, Skill, Role, RoleSkillMap, Question, Assessment, AssessmentItem. No evidence, manager-decision, immutable audit, source-document, notification, or learning-resource tables.
- `backend/excel_loader.py`: reads workbook sheets and performs a limited Finance skill-reference check. It does not import mappings into SQLite.
- `backend/rag_service.py`: exact Finance role-name lookup plus token-overlap matching of up to two skills in Excel. No SOP ingestion/chunking, document approval lifecycle, or DataOps retrieval.
- `backend/question_service.py`: builds a Finance context prompt, calls the LLM, extracts a JSON array, and validates items with Pydantic. Count and exact A/B/C/D option membership are not enforced.
- `backend/llm_service.py` and `config.py`: a service wrapper exists, but it is coupled to Azure AI Inference and `CIS_*` environment variables. Configuration loads `backend/.env`. No `LLM_PROVIDER`, mock provider, or `LUNA_*` boundary.
- `backend/assessment_service.py`: chooses newest approved questions for a skill, saves answers, computes score and achieved level, and adds XP.
- `backend/tni_service.py`: uses the newest assessment ID per mapping among submitted assessments to compute gaps and generic recommendations. No learning-catalog lookup or manager-confirmed skill record.

## Complete file inventory at baseline

All 33 tracked files are listed below. No additional untracked or ignored files/directories were reported at baseline. `.git/` exists; its internal metadata is omitted. There is no repository `AGENTS.md`, backend dependency manifest, test suite, deployment configuration, or root README.

```text
Talentet360i/
├── .git/
├── backend/
│   ├── .gitignore
│   ├── assessment_service.py
│   ├── config.py
│   ├── database.py
│   ├── excel_loader.py
│   ├── llm_service.py
│   ├── main.py
│   ├── models.py
│   ├── question_service.py
│   ├── rag_service.py
│   ├── schemas.py
│   ├── tni_service.py
│   └── data/
│       ├── finance_assessment.xlsx
│       └── overall_rd.xlsx
└── frontend/
    ├── .gitignore
    ├── README.md
    ├── eslint.config.js
    ├── index.html
    ├── package-lock.json
    ├── package.json
    ├── tsconfig.app.json
    ├── tsconfig.json
    ├── tsconfig.node.json
    ├── vite.config.ts
    ├── public/
    │   ├── favicon.svg
    │   └── icons.svg
    └── src/
        ├── App.css
        ├── App.tsx
        ├── index.css
        ├── main.tsx
        └── assets/
            ├── hero.png
            ├── react.svg
            └── vite.svg
```

The audit adds `PROJECT_CONTEXT.md` and `NEXT_STEPS.md` at the root. Static image assets were inventoried; database binaries and secret files were not opened.

## Requirement status

Complete means the full requirement is demonstrated. Partial means substantive code exists but gaps remain; it does not claim runtime success. Missing means no implementation found. Blocked identifies a prerequisite preventing execution or acceptance. None of the seven MVPs is complete.

| Requirement | Status | Evidence and remaining gap |
| --- | --- | --- |
| 1. AI question bank | Partial; live generation blocked | Prompt, Excel context, draft persistence, and schema exist. No approved SOP ingestion, DataOps retrieval, robust option/count validation, or mock mode. Company API unavailable here. |
| 2. Reviewer governance | Partial | Approve/reject endpoint overwrites current state. No edit workflow, reviewer authorization, recorded actor assignment, version history, or immutable decisions. |
| 3. Employee assessment | Partial | Approved-status filter, assignment, stored responses, score, and repeat-submission guard exist. No randomization, level filtering, critical-fail rules, answer snapshots, or ownership checks. Runtime not verified. |
| 4. Skill level and TNI | Partial | Score-derived achieved level and arithmetic gaps exist. Thresholds lack source linkage; blank/zero handling is wrong in TNI. No supported course lookup or complete role profile coverage. |
| 5. Leader distribution dashboard | Missing | No API/UI aggregates, confirmation gate, team/hub model, or scoped access. No public individual leaderboard was found. |
| 6. Employee evidence | Missing | No model, storage service, endpoint, status history, or UI. |
| 7. Manager confirmation | Missing | No decisions, send-back workflow, confirmed-level record, audit, or UI. TNI's confirmation message is not an implemented workflow. |
| Admin/L&D, reviewer, employee, manager, leader experiences | Missing | Frontend is template only. User schema permits employee/reviewer/manager/leader strings, but not admin/L&D; strings do not enforce permissions. |
| One Finance/DataOps application | Partial | Shared application and generic function field; both workbooks readable. Generation/retrieval are Finance-specific and no workbook-to-database importer exists. |
| Role-skill-target mapping | Partial | CRUD/model exist; no user-to-job-role relationship or source import. Nullable target and `is_expected` can disagree. |
| RAG traceability | Partial | Retrieval includes some source metadata; stored question source is the generic `Finance Excel RAG`. No immutable document/version/page/chunk or workbook-row citations. |
| In-app notifications | Missing | No implementation. |
| Audit history | Missing | Current timestamps/comment fields exist but no append-only event or version history. |
| SkillQuest/gamification | Partial | XP is added on submission; no quests, badges, or engagement UI. |
| XP independent of proficiency | Partial | Existing achieved-level calculation does not read XP, which is correct by inspection. Official confirmed proficiency does not yet exist. |
| Supported learning recommendations | Missing | Learning sheets exist but TNI uses generic strings, without mapped resource evidence. |
| Mock/Luna environment switch | Missing | Only Azure/CIS wrapper exists. Deterministic mock question/TNI outputs absent. |
| Reproducible local/deployable setup | Blocked | Missing backend dependency manifest and installed runtime dependencies; frontend checks cannot execute successfully. No deployment recipe or end-to-end tests. |

## Source-file findings

Both expected Excel files are present and tracked. They are readable using the bundled Python runtime:

| Workbook | Existing loader counts | Finding |
| --- | --- | --- |
| `backend/data/finance_assessment.xlsx` | 9 roles, 28 skills, 90 mapping records; 26 worksheets | Validator reports **13 distinct referenced skill IDs missing from Skill_Master**. |
| `backend/data/overall_rd.xlsx` | 38 skill rows, 38 matrix rows, 38 learning-mapping rows; 11 worksheets | Sheets can be read; this is not complete DataOps validation. |

Finance also contains Training_Catalogue, Training_Skill_Map, Assessment_Blueprints, Assessment_QBank, governance/results/TNI sheets, and Users_Teams. DataOps includes SOP & Learning Mapping and Source Register. Their existence does not prove complete or approved data, nor implemented application features. No separate training/SOP document files are present anywhere in the repository. References in Excel do not replace actual approved documents.

The existing validator only checks Finance mapping skill references. It does not certify role joins, blank targets, duplicates, scoring policy, learning links, DataOps consistency, or privacy. It returned `needs_review`; this issue must be reconciled against authorized sources without inventing replacements. Scoring and critical-fail policy must be traced to source cells before implementation; this audit does not certify current hard-coded rules as supplied policy.

## Significant implementation defects found

1. All routes are unauthenticated. `/questions` returns correct answers and explanations, while `/users`, assessment IDs, and employee TNI IDs have no access scope. Assessment payloads omit answers, but the separate question endpoint exposes them.
2. Assessment selection filters skill/status only, uses descending question ID, and ignores proficiency, expectedness, job-role eligibility, and business-function isolation. Question records are live references rather than fixed approved versions.
3. Blank target is accepted with `is_expected=True`. Generation blocks a null target, but assignment does not. Submission substitutes target 1 for null; TNI uses `mapping.target_level or 1`, which also changes valid zero to 1.
4. Achieved-level thresholds are hard-coded (`>=95`, `>80`, otherwise), with no policy/version reference or critical-fail evaluation. For target 0, the middle branch can produce level 1. These are observed rules, not endorsed requirements.
5. Duplicate answer IDs pass schema validation and collapse into a dictionary at submission; the last answer wins. Invalid question option dictionaries also pass schema validation when the correct-answer string is A-D.
6. Review overwrites status/comment/time and never assigns `reviewed_by_id`. There is no edit/reapproval/version control or immutable audit trail.
7. Retrieval can return no matching skill without failing. A real-source sample returned two matches with incomplete level indicators; generation has no completeness gate. Generic stored source labels cannot reproduce the context.
8. TNI covers only submitted assessments, selects latest assignment ID rather than latest submission time, and does not cover unassessed expected skills. Its level-3 confirmation flag does not enforce manager confirmation.
9. SQLite foreign-key enforcement is not explicitly enabled; role/skill uniqueness is enforced only in application lookup for mappings. Concurrency and integrity behavior remain untested.

## Git and secret hygiene

- Baseline working tree was clean. No `.env`, `.venv`, Python cache, database, private-key, or certificate-key paths were tracked in the current index. A filename scan of reachable local Git history found none of those path categories either.
- A heuristic scan of current tracked text for common literal credential/private-key patterns found no matches. Only locations would have been reported. Environment variable names and empty defaults are not credentials.
- This was not a comprehensive historical secret-content scan, remote-repository audit, or proof that every credential format is absent.
- Both workbooks are tracked and potentially confidential. The Finance workbook includes a Users_Teams sheet. Masking, classification, and permission to keep these files outside the company laptop are unverified. No source records were printed or sent to an LLM/API.
- Backend ignores `.env`, `.venv/`, `__pycache__/`, `*.pyc`, and `talent360i.db`; frontend ignores dependencies/build outputs. No root ignore policy exists, and alternative environment/database filenames are not broadly covered.

## Checks actually run

No packages were installed; no company API calls were made. No application database was created/opened. No application source or workbook was modified.

| Check | Result |
| --- | --- |
| Python AST parse of all 11 backend `.py` files, with no imports/bytecode writes | PASS: all parse. Syntax validity does not demonstrate service behavior. |
| `python -B -m unittest discover -s backend` | **0 tests**, reports `NO TESTS RAN`. No backend test files/configuration found; frontend has no test script. |
| `npm.cmd run lint` in frontend | FAIL, exit 1: `eslint` not recognized; dependencies absent. No lint results obtained. |
| `npm.cmd run build` in frontend | FAIL, exit 1: `tsc` not recognized; dependencies absent. Vite build not reached. |
| Import `assessment_service` using system Python | FAIL: `ModuleNotFoundError: No module named 'fastapi'`. |
| Runtime dependency inventory | System Python lacks FastAPI, SQLAlchemy, Pydantic, openpyxl, dotenv, pytest, httpx. Bundled Python has openpyxl/Pydantic but lacks FastAPI, SQLAlchemy, dotenv, Azure SDK, pytest, httpx. |
| Existing `validate_workbooks()` with bundled Python | Executes; returns `needs_review`, 13 missing Finance skill references. Only aggregate counts recorded. |
| Existing Finance retrieval with a source-derived role/skill, bundled Python | Executes; two matched skills, not all indicators populated. Synthetic unmatched skill returns an empty match list without error. |
| Pydantic probes with synthetic data, bundled Python | Confirms invalid option keys, duplicate answers, and null-target/expected inconsistency are accepted. These are requirement failures, not positive validation results. |
| Git index/current text/history-path checks | Findings documented above; no known credential values displayed. |

Not demonstrated: API startup/health, database initialization/persistence, review-to-assessment workflow, scoring through real sessions, Luna generation, frontend rendering, or end-to-end integration. These remain unverified, not passing. Safe repeatable integration checks should use isolated temporary SQLite and synthetic fixtures after confirmation and dependency setup.
