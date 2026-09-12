# Talent360i Phase 2 backend demo

The backend supports Finance and DataOps in one application. This phase adds demo authorization, question history, frozen assessments, evidence submission/history, manager review, official skill levels, leader aggregates, notifications, append-only audit events, and SkillQuest/XP. No frontend work is included.

## Start a synthetic demo

From the repository root, with Phase 1 dependencies installed:

```powershell
$env:LLM_PROVIDER = 'mock'
backend/.venv/Scripts/python.exe backend/seed_demo.py
backend/.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

The explicit seed command creates only fictional demo identities and mappings. It does not read or repair the company workbooks. It prints user IDs for Admin, L&D, and Finance/DataOps Manager, Reviewer, Leader and Employee, plus the two synthetic mapping IDs. Re-running it does not duplicate the fixtures or reset existing records. A fresh demo has ten identities. The database is the ignored configured SQLite file; no application database was created during the implementation checks, which used memory/temporary files.

Open `http://127.0.0.1:8000/docs`. Every protected operation accepts an `X-Demo-User-Id` header. Enter a seeded ID appropriate to that action. Header identity selection is intentionally a **local demonstration mechanism, not authentication suitable for production**. Anyone with local access can choose a demo identity. Keep the server bound to loopback, do not put it behind a public reverse proxy, and use synthetic data. The app rejects non-loopback request clients. Health and API documentation contain no user data and remain public.

No Luna key is needed for the demo. The original Luna transport remains intact; environment-only provider switching from Phase 1 is preserved but no live Luna request was used for Phase 2 verification.

## Role permissions

| Stored user role | Demo experience and scope |
| --- | --- |
| `admin`, `ld` | Configure users/profiles, roles, skills, mappings, source-referenced scoring policies and quests; administer assessments, review question content, send notices, inspect audits and aggregates. Cannot act as a manager to confirm official proficiency. |
| `reviewer` | Generate, edit, approve/reject, and inspect question revisions within the configured business function. Cannot see employee results or evidence. |
| `employee` | Read and submit own assigned assessments, inspect own TNI, submit/resubmit evidence, request re-review, read own notifications/audit entries and claim eligible quests. Cannot assign assessments or read answer banks. |
| `manager` | Assign assessments to direct reports; inspect their results/evidence; confirm or send back results/evidence with comments. Manager and employee function assignments must match. No self-confirmation. |
| `leader` | Read only authorized aggregate reporting for the configured function, additionally restricted by team/hub when set. No other employees' assessments, TNI, evidence, answer banks or personal leaderboard. |

`User.role` retains the existing access-role design. Additive `UserProfile` records hold the separate job role, manager, business function, team and hub. Admin/L&D can configure profiles on existing Phase 1 users using `PATCH /users/{id}/profile`; changing a job role/function requires consistent supplied values. A profile change does not invent skill mappings or levels.

## End-to-end demonstration

1. **Reviewer:** `POST /questions/generate` with the function's `role_skill_map_id` and `question_count` (1–5). Mock questions are explicitly fictional, deterministic and schema-valid. Set `require_approved_sop=true` to see a controlled 409 when approved SOP content is unavailable.
2. **Reviewer:** inspect `GET /questions` and `GET /questions/{id}/history`. Edit using `PATCH /questions/{id}` with question text, options, correct answer, explanation, a comment, and the latest `expected_revision`. Each edit becomes pending review. Approve/reject using `PATCH /questions/{id}/review`. A second decision on an already reviewed version returns 409; edit a new revision first.
3. **Manager:** `POST /assessments` with a direct report's numeric `employee_id`, the mapping ID and question count. Selection is randomized across approved questions for that exact mapping and target level. Insufficient eligible questions return 400.
4. **Employee:** `GET /assessments` then `GET /assessments/{id}`. The response exposes question text/options, never correct answers. Submit exactly one A–D answer per assigned question to `POST /assessments/{id}/submit`. Duplicate/missing answers and repeat submissions fail. Question text, answer keys, target and scoring policy are frozen at assignment; later SME edits cannot alter an assigned assessment's scoring.
5. **Employee:** `GET /users/{id}/tni` shows calculated level, target, gap, review state, separate `official_confirmed_level`/`official_assessment_id`, and mapped learning resources. Unassessed expected skills have null current level/gap, not invented level zero. Missing learning sources produce explicit unavailable states and no invented courses.
6. **Employee:** `POST /evidence` with `role_skill_map_id`, optional submitted `assessment_id`, title, description and optional HTTP(S) URL. This is text/link submission; the backend never downloads links. No binary upload workflow is claimed. `GET /evidence/{id}/history` returns immutable content revisions and manager comments/decisions.
7. **Manager:** `GET /manager/reviews` lists pending direct-report evidence and results. `POST /evidence/{id}/decision` takes `decision` (`confirm` or `send_back`), nonblank `comment`, and the current evidence `expected_revision`. Send-back enables `POST /evidence/{id}/resubmit` by its owner with revised content and the prior revision number. Original content and comments remain in history.
8. **Manager:** after confirming all linked evidence, `POST /assessments/{id}/decision` with decision/comment and `review_revision` from the assessment read endpoint as `expected_revision`. A result without linked evidence can also be reviewed. Confirmation copies the calculated level into an official record; the caller cannot supply an arbitrary level. Evidence-only confirmation does not create proficiency. `GET /assessments/{id}/history` retains decisions. A sent-back result can be requeued by its employee with `POST /assessments/{id}/resubmit-review` and a comment/current revision; this does not rescore or award XP again.
9. **Leader:** `GET /leader/aggregates?group_by=role,team,function,hub,skill,level`. Only manager-confirmed employee-skill records count. Optional filters: `role_id`, `team`, `function`, `hub`, `skill_id`, `level`. Responses contain group counts, gap counts and total gap; no person IDs/names/emails/XP. Filters cannot broaden the leader's scope. A newly calculated or sent-back result does not replace an older official level. Confirming a newer result replaces the official record; an older assessment cannot overwrite it. Official records outside an employee's current expected job-role mapping are excluded.
10. **Any identity:** `GET /notifications`, `GET /notifications/unread-count`, `PATCH /notifications/{id}/read`. Read marks are idempotent and owner-only. Workflow notices are automatic; Admin/L&D and scoped managers can use `POST /notifications` for manual notices. Each creation/first read is audited.
11. **Admin/L&D:** `POST /quests` with title, description, event type (`assessment.submitted` or `evidence.submitted`), required count, XP reward and optional function. **Employee:** `GET /quests`, `POST /quests/{id}/claim`, `GET /xp`. Progress counts distinct qualifying events since quest creation. Resubmissions do not count as new evidence; rewards can be claimed once. There is no individual XP leaderboard and XP never enters calculated or official level formulas.

Audit access is `GET /audit-events` with optional `action`, `after_id` and bounded `limit`. Admin/L&D see all; employees see their own entries; managers additionally see their direct reports; other roles see only entries involving themselves. Audit payloads reference question revisions rather than exposing answer keys. There are no history update/delete APIs. SQLite triggers reject UPDATE/DELETE on audit, question/evidence revision, manager-decision, XP-award and scoring-policy tables.

## Scoring and source limitations

- Without supplied policy, the Phase 1 provisional thresholds remain unchanged. These demo calculations are not certification of company policy.
- Admin/L&D may add a versioned policy at `POST /role-skill-maps/{id}/scoring-policy`, supplying `full_score_min`, `middle_score_min`, optional `critical_fail_level`, and a required `source_reference`. A reviewer may mark a question `is_critical=true` only after such a critical-fail policy exists. Wrong critical answers cap calculated level according to the frozen policy. The tests configure fictional policy references only; no company thresholds are fabricated.
- `GET /sources/status` and Admin/L&D `GET /data/validate` report missing sources and missing Finance references. The 13 unresolved references remain unchanged. Retrieval now requires the exact source skill and complete indicator, rather than substituting a similar skill. No automatic source import or invented replacement mapping occurs.
- Approved SOP documents have not been supplied/registered. Production internal-skill RAG remains blocked. Mock exercises remain available, explicitly synthetic. DataOps production document retrieval and durable document approval/provenance require supplied content and further work.
- Learning resources retain Phase 1 workbook joins and source-row provenance. A skill mapping does not prove course approval or level suitability; supplied scope/status is exposed. Missing/ambiguous matches yield no resources.

## Persistence, transactions and verification

Startup adds 15 new tables without changing the original seven table column layouts. No destructive migration or invented historical backfill runs. Existing Phase 1 records remain readable. Previously assigned assessments without frozen question/policy records must be reassigned; submission returns an explicit 409 rather than guessing historical answer versions. Historic assessments do not become official automatically.

Each protected request commits its business changes, audit records and notices together before sending a successful response; failures roll back the transaction. Conditional state/revision changes and unique reward keys prevent repeated decisions/rewards. SQLite foreign keys and a busy timeout are enabled. Concurrent assessment submission is tested against a file-backed DB with separate connections.

Run from the repository root:

```powershell
backend/.venv/Scripts/python.exe -B -m pytest -c backend/pytest.ini backend/tests -q
backend/.venv/Scripts/python.exe -m pip check
git diff --check
```

Phase 1 assertions remain unchanged. Their client fixture now uses an explicit privileged test dependency override so those existing workflow tests can run behind authorization. New Phase 2 tests use real demo headers and exercise authorization without that override. All tests disable actual dotenv loading and remove inherited Luna/CIS credentials. Provider contract tests use synthetic placeholders/fake transports only. No real Luna call occurs. Persistence tests use temporary SQLite files, and learning tests use temporary fictional workbooks.
