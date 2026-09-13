# Talent360i Phase 4 verification and next steps

## Phase 5A complete

The offline RAG foundation accepts explicit local manifests and PDF, DOCX, PPTX or text documents without URL access. It validates stable RD source/skill metadata, rejects path traversal and unsafe synthetic use, records hashes and provenance, performs deterministic skill-scoped retrieval, and fails closed without approved context. Generated RD drafts remain pending SME review. Approved company content, Luna connectivity and live source validation remain Phase 5B office work.

Phase 4 completed on 2026-09-13 in mock mode. The original Finance and RD workbooks were read without modification, and the SME clarification workbook was validated from its local attachment location without copying it into the repository.

The final SME-alignment audit corrected the Faiza reference to the permanent MVP status `Unavailable — excluded from MVP`, audit reference only, 0 imported records. No scoring or source rule was inferred from unresolved SME comments.

## Phase 4 verified results

| Check | Result |
| --- | --- |
| Fresh import | **PASS:** 382 stable provenance records created. |
| Repeat import | **PASS:** 0 changes; entity IDs and question revision counts remained stable. |
| Finance | **PASS:** 28 skills, 9 selected roles, 12 role-description metadata records, 60 valid mappings, 49 safe questions, 30 valid learning mappings. Of 115 question rows, 36 were incomplete; the safe set is 23 Approved, 21 Pending SME Review and 5 Needs Rewrite. |
| RD/DataOps | **PASS:** 38 skills, B2/B3/B4 roles, 114 matrix cells (86 Expected, 28 Not Expected) and 38 learning metadata records. The Faiza source is `Unavailable — excluded from MVP`, retained only as an audit reference, with 0 imported records. |
| Backend suite | **PASS: 101 passed, 0 failed, 4 warnings in 65.92 s.** |
| Frontend suite | **PASS: 25 passed, 0 failed, 4 files in 13.39 s.** |
| Frontend lint/build | **PASS:** lint exit 0; production build exit 0 in 2.04 s. |
| Browser | **PASS:** Finance and DataOps Employee, SME/Reviewer, Manager and Leader; Admin and L&D source/mapping views. Empty states, access scoping, source limitations and confirmed-only leader reporting verified. |
| Repository checks | **PASS:** `git diff --check` and cached check exit 0 before final staging. Original workbook hashes remained unchanged. |
| Provider | **PASS:** `LLM_PROVIDER=mock`; Luna was neither requested nor called. |

## Phase 4 source and policy blockers

1. Finance has 30 invalid role-map rows covering 13 distinct missing R2R skill references. A further 30 question rows lack an exact valid role/skill/target mapping, and 13 training mappings lack a valid skill or course reference. None were invented.
2. The confirmed 20-question starting blueprint requires 6 Difficult, 8 Moderate and 6 Easy questions. No Finance role has a sufficient approved pool, and its source difficulty labels are Role Ready/Advanced. Valid workbook assessment assignment therefore remains blocked.
3. RD/DataOps contains no question rows. The Faiza Microsoft List is `Unavailable — excluded from MVP`, remains an audit reference only, and has 0 imported records. DataOps generation and assessment remain unavailable for this MVP.
4. Twenty questions cannot cover all 31 B3 or 38 B4 expected competencies. The source does not resolve that blueprint conflict or supply enough questions for the 70% reassessment-new rule.
5. The workbooks do not define a complete Beginner/Moderate/Expert score calculation or the meaning of greater-than-90% document matching. Workbook results remain pending policy validation; Expert additionally requires complex-case evidence and manager/SME confirmation.
6. Eight RD learning rows have no URL. Linked workbook resources remain metadata and are not claimed as approved course or SOP content.

## Phase 4 changed files

- `.gitignore`
- `README.md`
- `NEXT_STEPS.md`
- `PROJECT_CONTEXT.md`
- `backend/assessment_service.py`
- `backend/governance_service.py`
- `backend/main.py`
- `backend/models.py`
- `backend/schemas.py`
- `backend/seed_demo.py`
- `backend/seed_workbook_demo.py`
- `backend/source_import.py`
- `backend/tests/test_source_integration.py`
- `backend/tni_service.py`
- `backend/workflow_service.py`
- `frontend/src/Admin.tsx`
- `frontend/src/App.tsx`
- `frontend/src/Employee.tsx`
- `frontend/src/Manager.tsx`
- `frontend/src/Reviewer.tsx`
- `frontend/src/catalog.ts`
- `frontend/src/source-integration.test.tsx`
- `frontend/src/types.ts`
- `frontend/src/workflows.test.tsx`

---

## Historical Phase 3 verification

Phase 3 completed on 2026-09-12 against baseline `d6d5b5b`. The responsive frontend connects the existing mock backend. No commit or push was made. The Phase 1/2 reports below are retained as historical records.

## Exact verification results

| Check | Result |
| --- | --- |
| Complete backend suite | **PASS: 88 passed, 0 failed, 0 errors, 2 warnings in 38.61 s**. All 85 existing cases preserved; 3 new identity-discovery tests. |
| Frontend tests | **PASS: 22 passed, 0 failed, 3 test files in 9.61 s**. Vitest / Testing Library synthetic fixtures. |
| Frontend lint | **PASS: exit 0**, no lint findings. |
| Production build | **PASS: exit 0**, TypeScript + Vite; final build 1.44 s. Main JS 240.93 kB and lazy leader/chart JS 361.04 kB; no oversized-chunk warning. |
| Python dependency consistency | **PASS: no broken requirements found**. |
| `git diff --check` | **PASS: exit 0**, no whitespace findings after generated-cache index cleanup. Git's LF/CRLF notices are informational. |
| `git diff --cached --check` | **PASS: exit 0**. Only four generated workbook deletions are staged. |
| Luna preservation | **PASS:** transport, config and provider source unchanged against HEAD after Git newline normalization. No live Luna calls or key requests. |
| Supplied workbooks | **PASS:** both supplied source workbooks byte-for-byte unchanged. |
| Secret/artifact scan | **PASS for current index/new text scope:** no credential heuristic matches; no tracked environment, database, dependency, cache or build paths after removing the four old generated test workbooks. No new unignored generated artifacts. This is not a historical secret audit or workbook confidentiality certification. |

## Browser verification

Real browser interactions used only the isolated ignored `backend/phase3-demo.sqlite` database, seeded with synthetic identities. No company users or workbook records were imported.

- Finance: generate a question, SME approve, manager assign, employee submit (100%, calculated level 3), inspect TNI, submit linked evidence, manager confirm evidence and result, leader shows one confirmed level-3 record.
- DataOps: generate/approve/assign, employee submit (0%, calculated level 1), claim a published quest (20 engagement XP), submit evidence, manager send back with comments, employee revise/resubmit, manager confirm evidence/result, leader shows one confirmed level-1 record and a two-level gap. XP did not alter proficiency.
- Notifications: mark a displayed employee notice read; read status and unread indicator update. Audit history shows persisted scoped events and source-limit messages.
- Desktop visual inspection: identity selection, Admin/L&D, reviewer content/rationale/source/history, employee dashboard and focused assessment, TNI, evidence, SkillQuest, manager inbox, leader chart/heatmap/details, notifications and audit.
- Mobile visual inspection at a 390 x 844 viewport override: Admin, reviewer, employee, evidence, SkillQuest, manager, leader and audit. Document width matched scroll width in measured major pages (375 CSS px after scrollbar); wide tables scroll inside their cards. Override reset afterward.
- Resumed final browser session reported **0 console errors**. Earlier development-only HMR reload errors after dependency/source updates cleared after a clean reload; workflows were then completed successfully.

Initial implementation checks caught shared-export lint issues, Windows text encoding, and accessible control-name mismatches. These were corrected. Chart code was split into a lazy bundle. The two backend warnings remain upstream Starlette/httpx and AnyIO deprecations, unchanged from prior phases.

## MVP status matrix

| Experience | Synthetic demo status | Boundary |
| --- | --- | --- |
| Admin/L&D | Complete | Source-health warnings, workbook validation, existing mappings, exact Finance context lookup, draft generation, assignment and quest publication. No invented source imports. |
| SME/Reviewer | Complete | Pending/status queues, separate content/answer/source sections, edit/reapproval, approve/reject comments and frozen revision history. |
| Employee assessment | Complete | Own assignments, focused question dialog, progress, answer submission, deterministic score and provisional level. No correct answers or explanations rendered before submission. |
| TNI / learning | Complete for available mappings | Separate calculated/official levels, targets, unassessed skills, development steps and source-constrained links. Missing mappings remain explicitly unavailable. |
| Evidence | Complete text/link workflow | Submission, history, send-back comments and resubmission. Binary file uploads are not implemented or claimed. |
| Manager | Complete | Scoped inbox, selected result context, latest TNI/official comparison, evidence decisions, result confirmation/send-back, history and assignment. |
| Leader | Complete | Confirmed-only KPIs, distribution chart, gap heatmap, details and function/role/team/hub/skill/level filters. No public individual leaderboard. |
| Notifications / governance | Complete | Own notifications/unread/read, scoped audit history with filtering/paging and explicit source limitations. |
| SkillQuest / XP | Complete basic experience | Published quests, progress, claim state and XP ledger; engagement never changes official proficiency. |
| Responsive / accessibility | Verified | Shared cards/forms/chips/tabs/dialogs, persistent desktop navigation, mobile drawer, keyboard focus, labelled controls, skeleton/empty/error/success states, constrained tables. |
| Provider boundary | Preserved | Mock used in the running demo; original Luna source remains unchanged and uncalled live. |

## Remaining blockers and limits

1. **13 missing Finance references** remain unresolved. Neither supplied workbook is modified. Workbook masking/classification remains unverified.
2. **Approved SOP/training documents are absent/unregistered.** Real internal-skill RAG and DataOps document retrieval require authorized sources. Mock exercises do not claim SOP provenance.
3. **Company scoring, critical-fail policy, level frameworks and learning suitability/approval require authoritative validation.** Existing tested backend calculations are preserved; no frontend scoring rules or courses are invented.
4. Production authentication/SSO, deployment hardening, file uploads and live company-laptop Luna validation remain roadmap work. Demo identities are local synthetic selection, not production login.
5. Assessment draft answers are held in the open dialog only; closing/reloading discards the unsent draft. Submitted results and histories persist in SQLite.
6. Legacy pending assessments without Phase 2 snapshots still require reassignment; the existing explicit 409 is preserved.

## Every Phase 3 changed file

The four `.pytest_tmp` paths were already problematic/deleted in the working tree at Phase 3 start and tracked in the baseline commit. They are now removed from the index only (staged deletions), with ignore coverage. No other changes were staged. No commit or push occurred.

- `.gitignore`
- `NEXT_STEPS.md`
- `README.md`
- `backend/.pytest_tmp/test_detailed_tni_supported_le0/dataops.xlsx`
- `backend/.pytest_tmp/test_detailed_tni_supported_le0/finance.xlsx`
- `backend/.pytest_tmp/test_learning_exact_joins0/dataops.xlsx`
- `backend/.pytest_tmp/test_learning_exact_joins0/finance.xlsx`
- `backend/README.md`
- `backend/main.py`
- `backend/tests/test_frontend_integration.py`
- `frontend/README.md`
- `frontend/index.html`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/public/favicon.svg`
- `frontend/src/Admin.tsx`
- `frontend/src/App.css`
- `frontend/src/App.tsx`
- `frontend/src/Employee.tsx`
- `frontend/src/Governance.tsx`
- `frontend/src/Leader.tsx`
- `frontend/src/Manager.tsx`
- `frontend/src/Reviewer.tsx`
- `frontend/src/api.test.ts`
- `frontend/src/api.ts`
- `frontend/src/catalog.ts`
- `frontend/src/format.ts`
- `frontend/src/hooks.ts`
- `frontend/src/index.css`
- `frontend/src/main.tsx`
- `frontend/src/reporting.test.tsx`
- `frontend/src/test-setup.ts`
- `frontend/src/types.ts`
- `frontend/src/ui.tsx`
- `frontend/src/workflows.test.tsx`
- `frontend/vite.config.ts`
- `frontend/vitest.config.ts`

## Next work

- Obtain authorized source fixes/documents and validate policy/mapping acceptance without inventing missing data.
- Run company-laptop Luna validation only when explicitly authorized there; keep secrets local.
- Plan production identity, deployment, migrations and protected binary evidence storage separately.
- Use the root README presentation walkthrough for the current synthetic demo.

---

## Historical Phase 1 and Phase 2 reports

# Talent360i prioritized implementation checklist

Baseline audit: 2026-09-12, commit `a953cd2`. See PROJECT_CONTEXT.md for requirements, inventory, evidence, and check results.

**Phase 2 backend work was authorized and is complete for the synthetic demo. No frontend work, commit, or push is included.** The original audit and Phase 1 reports remain below as history. Company-source acceptance blockers are listed separately from implemented demo behavior.

## Phase 2 results — 2026-09-12

Phase 2 baseline commit: `bccc593`. Final backend run: **85 passed, 0 failed, 0 errors, 2 upstream deprecation warnings in 14.73 seconds**. This includes all 35 Phase 1 cases plus 50 new cases. The Phase 1 workflow assertions are unchanged; their client fixture explicitly overrides identity with an administrator for regression testing. New tests exercise actual header authorization and denial paths.

Verification includes complete Finance and DataOps question → SME review → assessment → TNI → evidence send-back/resubmission → manager confirmation → scoped aggregate flows; answer hiding; employee/manager/function isolation; self-review and arbitrary confirmed-level rejection; question/policy snapshots; critical-fail execution; official/calculated separation; notifications and idempotent reads; append-only SQL triggers; quests and once-only XP; source failures; transaction rollback; randomized eligible selection; profile scopes; additive setup over a legacy user table; seed idempotency; persistence across process restarts; and concurrent submission with exactly one score/XP/audit event.

The first expanded test run found a missing quest creation timestamp. It was fixed and all subsequent final checks passed. The two remaining warnings are the pre-existing Starlette/httpx and AnyIO BlockingPortal deprecations. `pip check` passes. `git diff --check` passes. No dependency changes were required. Frontend source/dependencies were not modified or built during Phase 2.

### Backend MVP status

| Backend requirement | Demo status | Company/source boundary |
| --- | --- | --- |
| AI question generation | Complete with deterministic mock | Real approved-SOP RAG remains blocked by absent documents; missing/ambiguous Finance references are rejected, not substituted. Luna transport is preserved, uncalled live. |
| SME governance | Complete | Scoped generation, edit/reapproval, approve/reject, immutable revision snapshots and audit actors. Company SME identities are not imported. |
| Employee assessment/scoring | Complete | Random approved mapping/level selection, frozen questions/target/policy, persisted responses, score/critical-fail execution and repeat-submission protection. Actual company score policies need validation. |
| Achieved level/TNI | Complete for supplied/synthetic mappings | Calculated and official levels separated; unassessed skills explicit; learning joins remain source-constrained. Full source mapping/curriculum quality is unresolved. |
| Employee evidence | Complete for text/link submission | Owned skill-linked evidence, immutable revisions and manager comments. Binary file uploads are not implemented or claimed. |
| Manager confirmation | Complete | Assigned managers only, no self-review, required comments/revisions, confirm/send-back/requeue. Only confirmed calculated results can create official levels. |
| Leader aggregation APIs | Complete | Role/team/function/hub/skill/level grouping and filters; scoped, manager-confirmed-only records, no public individual leaderboard or personal identifiers. |
| In-app notifications | Complete | Automatic/manual creation, own listing/unread count/read state and audit; manager notices limited to direct reports. |
| Append-only audit | Complete | Generation, review, assessment, evidence, decisions, notifications and XP; SQLite UPDATE/DELETE rejection and authorized reads. No invented backfill of old history. |
| Demo role authorization | Complete for local synthetic use | Admin, L&D, Reviewer, Employee, Manager, Leader; job-role and reporting profiles. Header identity selection is not production authentication/SSO. |
| SkillQuest/XP | Complete basic backend | Configured quests count distinct post-publication events; rewards once only. XP cannot alter calculated/official proficiency. |
| Providers | Preserved | Mock used for all real generation during verification. Existing Luna tests use fake transports/placeholders only. |

### Phase 2 changed files

| File | Change |
| --- | --- |
| `README.md` | Current backend setup, demo seed/header and Phase 2 behavior. |
| `PROJECT_CONTEXT.md` | Historical-audit notice updated for authorized Phase 2 work. |
| `NEXT_STEPS.md` | Results, status matrix, file report and remaining blockers. |
| `backend/README.md` | Detailed role/API walkthrough, transaction/persistence behavior and source limitations. |
| `backend/models.py` | Fifteen additive profile, history, snapshot, review, official-level, notification, audit and engagement tables; append-only triggers. |
| `backend/database.py` | Foreign-key enforcement and per-request commit/rollback. |
| `backend/auth.py` | Loopback demo identity and role/employee/manager/function authorization helpers. |
| `backend/event_service.py` | Transactional audit, notifications and unique-source XP awards. |
| `backend/governance_service.py` | Question scoping, version history, edit/reapproval and critical-question prerequisites. |
| `backend/assessment_service.py` | Randomized scoped assignment, frozen question/target/policy, deterministic submission, critical fail, audit/notices and concurrent retry protection. |
| `backend/workflow_service.py` | Evidence/history, manager decisions, result requeue, official-level transitions and quest progression/claims. |
| `backend/leader_service.py` | Confirmed-only scoped aggregates without personal identifiers. |
| `backend/main.py` | Protected existing/new routes, policies, user profiles, source status, inbox, notifications, audits and quests. |
| `backend/schemas.py` | User profiles/access roles, SOP-required generation flag, official-level and unassessed TNI fields. |
| `backend/workflow_schemas.py` | Validated evidence, decision, revision, policy, notification, quest and profile requests. |
| `backend/tni_service.py` | Separate official/calculated levels, review states and unassessed expected skills. |
| `backend/llm_provider.py` | Update mock TNI limitation text to reflect implemented manager confirmation; preserve provider boundary. |
| `backend/rag_service.py` | Exact skill retrieval and explicit missing-reference/indicator failures. |
| `backend/seed_demo.py` | Explicit idempotent synthetic identities/mappings without workbook imports or repairs. |
| `backend/tests/conftest.py` | Phase 1 privileged test identity, secure header client, cleared inherited Luna/CIS credentials. |
| `backend/tests/test_phase2.py` | End-to-end and negative tests for Phase 2 workflows. |
| `backend/tests/test_persistence_and_concurrency.py` | Additive setup, restart/seed persistence and exactly-once concurrent submission tests. |

### Remaining source/deployment blockers

- The **13 Finance skill references remain unresolved**; both original workbooks are unchanged. Their confidentiality/masking status is still unverified. Tests and seed fixtures use synthetic records only.
- Approved SOP/training documents are absent/unregistered. Real internal-skill document RAG and full document approval/location provenance remain incomplete. `require_approved_sop=true` fails explicitly instead of inventing content; ordinary mock demos remain available.
- Actual company scoring thresholds, critical-fail rules, level frameworks and learning approval/suitability still need source reconciliation. Configurable policy execution works, but only fictional policy settings were tested. No supplied mappings were repaired or manufactured.
- Live Luna behavior requires company-laptop verification; no key was requested or real request sent.
- Demo identity is loopback-only user selection. Enterprise authentication, production deployment/integrations and broader security hardening remain roadmap work.
- Legacy Phase 1 data remains readable and receives no fabricated history/official status. Legacy pending assessments without snapshots return a clear 409 and need reassignment for immutable scoring.
- Frontend work is entirely outside this phase. No commit or push was performed.

Generated environments, dependencies, `.env`, databases, caches and build output remain ignored/untracked. The final index/change scan is scoped to current tracked/new files; it does not certify historical workbooks as nonconfidential or constitute a complete historical secret scan.

## Phase 1 verified results — 2026-09-12

| Check | Final result |
| --- | --- |
| Backend dependencies | Installed in ignored `backend/.venv`, Python 3.14.6. Runtime/test dependency closures locked in requirements files. |
| Frontend dependencies | `npm ci` completed: 204 packages, original package manifest/lock unchanged. Node 24.18.0. |
| Backend suite | **35 passed**, 0 failures/errors, 2 upstream deprecation warnings, in 2.67 seconds. |
| Python package consistency | `python -m pip check`: no broken requirements. |
| Frontend lint | `npm run lint`: exit 0. |
| Frontend build | `npm run build`: exit 0; TypeScript and Vite succeeded. Output is ignored. |
| Luna preservation | Original `backend/llm_service.py` unchanged. Fake-client tests verify transport invocation, bearer handling, model forwarding and cleanup on success/failure. No live Luna calls. |
| Provider switching | Fresh-process test switches only a temporary synthetic `.env` from mock to luna; no source changes. Restart required to reload configuration. |
| Source protection | Supplied workbooks unchanged. Tests use temporary synthetic workbooks, not company records. Missing source IDs are never synthesized. |
| Existing workbook validator | Re-run: `needs_review`, still 13 missing Finance skill references. |
| Final repository hygiene | `git diff --check` clean. No forbidden tracked/unignored environment, dependency, cache, build or database artifacts. `.env.example` is eligible for Git. |

Tests cover health, deterministic/schema-valid mock generation without RAG/Azure imports, review approval/rejection and invalid review states, approved-only/level-matched assessment selection, saved answers, exact scoring and repeatability, duplicate submissions/answers, score-band boundaries, zero/blank targets, detailed/basic/empty TNI, XP independence, source-mapped Finance/DataOps resources, missing/ambiguous mappings, unsupported provider recommendations, invalid Luna output, safe configuration errors, and `.env` switching.

The first test run found the external-network guard also blocked Windows asyncio's loopback socket pair; the guard now permits only loopback for that purpose. Initial dependency attempts hit sandbox permissions, network resets and incomplete npm extraction; the final installations succeeded. No dependency version changes were needed in the frontend.

The two remaining warnings originate in Starlette's test client: its httpx integration and the AnyIO BlockingPortal alias are deprecated. They do not fail checks; migration can be handled with a future dependency update.

## Phase 1 changed-file report

Paths below are relative to the repository root. No files were committed.

| File | Change |
| --- | --- |
| `.gitignore` | Ignore environments, dependencies, secrets, databases, caches and build output; permit `.env.example`. |
| `README.md` | Reproducible install, configuration/provider switching, run/test instructions and limitations. |
| `PROJECT_CONTEXT.md` | Mark the original audit as historical and link current results. |
| `NEXT_STEPS.md` | This verified Phase 1 report and remaining roadmap. |
| `backend/.env.example` | Mock default and empty configuration placeholders; no keys/endpoints. |
| `backend/requirements.in` | Direct runtime dependencies. |
| `backend/requirements-dev.in` | Direct test dependencies. |
| `backend/requirements.txt` | Exact installed runtime dependency versions. |
| `backend/requirements-dev.txt` | Exact installed test dependency versions plus runtime lock. |
| `backend/config.py` | Provider selection, LUNA-to-legacy-CIS compatibility and configurable SQLite URL. |
| `backend/database.py` | Use configured SQLite URL and share in-memory test DB across request threads. |
| `backend/llm_provider.py` | Typed mock/Luna boundary, deterministic fictional questions and detailed TNI, response validation and safe errors. |
| `backend/question_service.py` | Select provider; skip company RAG in mock; preserve Luna prompt/retrieval path. |
| `backend/learning_service.py` | Exact Finance/DataOps workbook joins with row provenance and no fabricated resources. |
| `backend/tni_service.py` | Deterministic gap facts plus provider narrative, source-constrained resources and provisional status; handle zero/blank targets and latest submission. |
| `backend/schemas.py` | Strict options/duplicate-answer checks, blank-target normalization, detailed TNI/resource schemas. |
| `backend/assessment_service.py` | Extract/test inherited level calculation, fix zero-target edge, guard Not Expected, select matching-level approved questions. |
| `backend/main.py` | Safe provider errors, actual draft source labels and typed TNI response. |
| `backend/pytest.ini` | Test discovery and backend import path. |
| `backend/tests/conftest.py` | Isolated SQLite, external-network guard and synthetic API/workbook fixtures. |
| `backend/tests/test_workflows.py` | Health, generation, review, assessment, scoring, level, response and TNI tests. |
| `backend/tests/test_providers_and_learning.py` | Provider/config/transport contracts, source joins and negative validation tests. |

`PROJECT_CONTEXT.md` and `NEXT_STEPS.md` were already untracked documents from the audit; they were updated during this phase. The frontend source/config/lockfile, original Luna transport, existing models, and both supplied workbooks are unchanged. Generated `.venv`, `node_modules`, caches and `dist` remain local ignored artifacts. No real `.env` or API key was created, read for display, or modified.

## Unresolved blockers and scope limits

- **Source data:** 13 Finance skill IDs remain missing from the supplied master. Their references are not repaired or fabricated. Separate approved SOP/training documents remain missing. These block authoritative internal-skill content, not synthetic Phase 1 tests.
- **Policy:** The inherited score thresholds are tested but not verified as supplied company policy. Critical-fail rules and complete proficiency frameworks still need authoritative reconciliation. All TNI levels are labelled provisional.
- **Learning:** Exact skill-mapped candidates now work. Level-specific course suitability, mapping approval, ambiguous skill names and full source-quality checks remain unresolved; the service exposes supplied scope/status rather than inferring them. No matching source means no course recommendation.
- **Luna:** Real authentication/connectivity/output behavior is unverified until run on the company laptop. DataOps production RAG and approved SOP ingestion remain future work; the existing Finance retrieval path is preserved.
- **Privacy:** Workbook masking/classification is still unverified. New tests use only synthetic fixtures. Existing APIs have no authentication/ownership scope and the general question-list route exposes answers; use local synthetic data until authorization is implemented.
- **Remaining product:** Full frontend, evidence, manager confirmation, official dashboards, immutable audit/version history, randomization, notifications and expanded gamification were deliberately excluded. Existing XP accrual was preserved and tested separately from proficiency.
- **Portability:** Dependencies were verified on Windows/Python 3.14.6/Node 24.18.0. Other company-laptop runtime versions need installation verification.

## Remaining roadmap

## P0 — establish authoritative inputs and safe local execution

- [ ] Confirm masking/classification of the two tracked workbooks for personal-laptop use. Use authorized synthetic fixtures for application tests; do not copy company records into fixtures, logs, or mock prompts.
- [ ] Reconcile the 13 missing Finance skill references against supplied sources. Validate both workbooks' role/skill keys, duplicate mappings, target frameworks, and blank-versus-zero semantics. Do not fabricate corrections.
- [ ] Obtain authorized approved SOP/training document files or masked/synthetic counterparts. Record source identity, version, approval, and permitted use. Real internal-skill generation remains blocked until approved content is available.
- [ ] Trace scoring thresholds, proficiency conversion, confirmation requirements, critical-fail rules, and learning mappings to exact supplied data. Record unresolved rules rather than choosing defaults.
- [x] Add a reproducible backend dependency manifest and local run instructions. Install locked frontend dependencies and rerun lint/build. Preserve React/Vite, FastAPI, SQLite, and service separation.
- [x] Add `LLM_PROVIDER=mock|luna` with environment-based `LUNA_*`, a placeholders-only example and ignore coverage, preserving the original transport and legacy CIS compatibility.
- [ ] Verify the real company API contract/connectivity on the company laptop; adapter tests currently use a fake transport.
- [x] Implement deterministic schema-valid synthetic mock questions and detailed TNI. Validate exact option keys, answer membership, nonempty content, count, and response types. Keep scoring outside the LLM and prevent unsupported learning resource IDs.

Acceptance: repeatable clean setup; environment-only provider switch; mocked generation repeatable and network-free; both workbook validations report precise unresolved issues; no secret values in tracked files or logs.

## P1 — enforce identity, source semantics, and assessment integrity

- [ ] Add MVP identity and authorization for Admin/L&D, Reviewer, Employee, Manager, and Leader. Add employee-to-job-role and team/function/hub/manager relationships. Keep enterprise SSO on the roadmap.
- [ ] Protect correct answers and personal results, and enforce ownership, manager relationships, and leader reporting scope. Test denial paths as well as permitted paths.
- [ ] Import validated role/skill/target data for Finance and DataOps with source references and repeatable behavior. Enforce blank target = Not Expected throughout assignment, scoring, TNI, and displays; preserve legitimate zero targets.
- [ ] Add database integrity constraints, explicit SQLite foreign-key enforcement, and a safe schema-change strategy. Make test DB selection independent of the application DB.
- [ ] Implement approved-document ingestion/retrieval for internal skills with stored document/version/location citations. Match the correct function/role/skill/level and reject missing or inadequate context. Preserve question-generation provenance.
- [ ] Add reviewer editing, approval/rejection, versioning, and auditable actor/time/reason records. Edits must produce an explicit reviewable version.
- [ ] Assign a randomized eligible set of approved question versions with the correct level and function. Store snapshots/version references and prevent answer exposure.
- [ ] Validate exactly one valid answer per assigned question. Persist deterministic score, supplied critical-fail decisions, policy version, and derived level. Prevent duplicate XP/submission effects, including concurrency/retries.

Acceptance: synthetic generate → review → assign → answer → score workflow passes; pending/rejected questions cannot enter assessments; duplicate answers and unauthorized access fail; supplied boundary/critical-fail cases pass; changing XP never changes proficiency.

## P2 — complete evidence, confirmation, and learning workflows

- [ ] Add employee evidence upload/link submission tied to skill/result, with protected storage, validation, status, and history.
- [ ] Add manager confirmation/send-back decisions with actor, timestamp, reason, and history. Store provisional and confirmed levels distinctly, including re-submission behavior.
- [ ] Build TNI across all expected role skills, including unassessed skills, with explicit result recency and confirmation status. Resolve latest-submission versus latest-assignment behavior.
- [ ] Integrate only validated supplied learning-resource mappings for both functions. Show an explicit unavailable state where mappings are missing; do not invent courses or URLs.
- [ ] Add durable audit events for question versions/reviews, assessments, evidence, and manager decisions. Add scoped in-app notifications for actionable workflow transitions.

Acceptance: evidence → send back → resubmit → confirm is persisted and auditable; provisional results cannot enter official distribution reporting; recommendations trace to supplied learning records.

## P3 — integrate the existing frontend and leader reporting

- [ ] Replace the starter screen with navigation and functional Admin/L&D, Reviewer, Employee, Manager, and Leader experiences, using the existing frontend stack.
- [ ] Connect API workflows with loading, validation, empty, error, and permission states. Keep provisional scores distinct from confirmed levels.
- [ ] Add leader aggregation APIs and charts for confirmed levels and gaps by authorized team/function/role/hub. Apply privacy controls and avoid public individual ranking.
- [ ] Add SkillQuest engagement experiences and XP history. Keep engagement mechanics independent of official proficiency.

Acceptance: one browser application supports both Finance and DataOps through all five experiences; no unauthorized data/answer disclosure; official charts use only confirmed levels.

## P4 — validate and prepare the hackathon deployment

- [ ] Add meaningful backend service/API tests using temporary SQLite, synthetic source fixtures, and mock mode. Cover negative authorization, missing RAG context, reviewer versions, approval eligibility, score boundaries, blank/zero targets, critical fails, duplicate submissions, confirmation gating, and unsupported learning mappings.
- [ ] Add a browser end-to-end flow covering generation, review, assessment, TNI, evidence, manager confirmation, and leader aggregates for both functions.
- [ ] Run lint/build and backend tests; document actual outcomes and remaining blockers. Do not treat zero collected tests as success.
- [ ] Add deploy/run configuration, persistence paths, health checks, environment documentation, and a synthetic demonstration scenario. Verify fresh-install startup and persisted state after restart.
- [ ] Validate the Luna adapter on the company laptop only, using local secrets. Keep enterprise SSO and production integrations documented separately as roadmap work.

Completion criterion: all seven MVP workflows demonstrated with synthetic data; tests pass; authorized source/policy gaps are explicitly resolved; the app is deployable with documented provider switching and no committed secrets.
