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
