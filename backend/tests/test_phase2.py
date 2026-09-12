import json
from datetime import timedelta
from types import SimpleNamespace
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import models
from database import SessionLocal, Base, engine
from auth import current_user
from main import app


@pytest.fixture
def demo(secure_client):
    with SessionLocal() as db:
        admin = models.User(employee_id="DEMO-ADMIN", full_name="Synthetic Admin",
                            email="admin@example.invalid", role="admin")
        db.add(admin)
        db.commit()
        admin_id = admin.id
    client = secure_client
    def call(method, path, actor=admin_id, data=None, expected=200):
        response = client.request(method, path, headers={"X-Demo-User-Id": str(actor)}, json=data)
        assert response.status_code == expected, response.text
        return response.json()
    accounts = {"admin": admin_id}
    for function in ("Finance", "DataOps"):
        role = call("POST", "/roles", data={"role_code": f"SYN-{function}", "role_name": f"Synthetic {function} Analyst",
                                             "business_function": function}, expected=201)
        skill = call("POST", "/skills", data={"name": f"Synthetic {function} Skill"}, expected=201)
        mapping = call("POST", "/role-skill-maps", data={"role_id": role["id"], "skill_id": skill["id"], "target_level": 3}, expected=201)
        group = {"mapping": mapping["id"], "role": role["id"], "skill": skill["id"]}
        for kind in ("manager", "reviewer", "leader", "employee", "other"):
            data = {"employee_id": f"SYN-{function}-{kind}", "full_name": f"Synthetic {function} {kind}",
                    "email": f"{function}-{kind}@example.invalid", "role": "employee" if kind == "other" else kind,
                    "business_function": function, "team": "Team A", "hub": "Hub A"}
            if kind in {"employee", "other"}:
                data.update(job_role_id=role["id"], manager_id=group["manager"])
            group[kind] = call("POST", "/users", data=data, expected=201)["id"]
        accounts[function] = group
    accounts["ld"] = call("POST", "/users", data={"employee_id": "SYN-LD", "full_name": "Synthetic LD",
        "email": "ld@example.invalid", "role": "ld"}, expected=201)["id"]
    return SimpleNamespace(client=client, call=call, **accounts)


def scored(demo, function="Finance", correct=3, count=3, employee=None):
    group = getattr(demo, function)
    employee = employee or group["employee"]
    questions = demo.call("POST", "/questions/generate", group["reviewer"],
                           {"role_skill_map_id": group["mapping"], "question_count": count}, 201)
    for q in questions:
        demo.call("PATCH", f"/questions/{q['id']}/review", group["reviewer"], {"status": "approved"})
    assessment = demo.call("POST", "/assessments", group["manager"],
        {"employee_id": employee, "role_skill_map_id": group["mapping"], "question_count": count}, 201)
    assigned = demo.call("GET", f"/assessments/{assessment['id']}", employee)
    # The randomized pool may contain previous approved batches.
    bank = {q["id"]: q for q in demo.call("GET", "/questions", group["reviewer"])}
    answers = []
    for index, q in enumerate(assigned["questions"]):
        answer = bank[q["question_id"]]["correct_answer"]
        if index >= correct:
            answer = next(k for k in "ABCD" if k != answer)
        answers.append({"question_id": q["question_id"], "selected_answer": answer})
    result = demo.call("POST", f"/assessments/{assessment['id']}/submit", employee, {"answers": answers})
    return assessment["id"], result


def decide(demo, assessment, function="Finance", decision="confirm", expected=200):
    group = getattr(demo, function)
    revision = demo.call("GET", f"/assessments/{assessment}", group["manager"])["review_revision"]
    return demo.call("POST", f"/assessments/{assessment}/decision", group["manager"],
        {"decision": decision, "comment": "Synthetic manager review", "expected_revision": revision}, expected)


@pytest.mark.parametrize("function", ["Finance", "DataOps"])
def test_complete_evidence_confirmation_aggregate_flow(demo, function):
    g = getattr(demo, function)
    assessment, result = scored(demo, function)
    assert result["achieved_level"] == 3
    assert demo.call("GET", "/leader/aggregates", g["leader"])["total_confirmed_records"] == 0
    evidence = demo.call("POST", "/evidence", g["employee"], {"role_skill_map_id": g["mapping"],
        "assessment_id": assessment, "title": "Synthetic work sample", "description": "Synthetic evidence text"}, 201)
    decide(demo, assessment, function, expected=409)
    demo.call("POST", f"/evidence/{evidence['id']}/decision", g["manager"],
              {"decision": "send_back", "comment": "Add synthetic context", "expected_revision": 1})
    revised = demo.call("POST", f"/evidence/{evidence['id']}/resubmit", g["employee"],
        {"expected_revision": 1, "title": "Revised synthetic sample", "description": "Added synthetic context",
         "url": "https://example.invalid/evidence"})
    assert revised["revision"] == 2
    demo.call("POST", f"/evidence/{evidence['id']}/decision", g["manager"],
              {"decision": "confirm", "comment": "Evidence verified", "expected_revision": 2})
    confirmed = decide(demo, assessment, function)
    assert confirmed["official_confirmed_level"] == 3
    profile = demo.call("GET", f"/users/{g['employee']}/tni", g["employee"])
    assert profile["skill_gaps"][0]["proficiency_status"] == "confirmed"
    assert profile["skill_gaps"][0]["official_confirmed_level"] == 3
    history = demo.call("GET", f"/evidence/{evidence['id']}/history", g["manager"])
    assert [r["revision"] for r in history["revisions"]] == [1, 2]
    assert [d["decision"] for d in history["decisions"]] == ["send_back", "confirm"]
    report = demo.call("GET", "/leader/aggregates?group_by=role,team,function,hub,skill,level", g["leader"])
    assert report["total_confirmed_records"] == 1
    row = report["groups"][0]
    assert row["level"] == 3 and row["function"] == function and row["gap_count"] == 0
    assert not any(key in json.dumps(report) for key in ["employee_id", "employee_name", "full_name", "email", "xp_points"])
    audits = demo.call("GET", "/audit-events?limit=500", demo.admin)
    actions = {a["action"] for a in audits}
    assert {"question.generated", "question.approved", "assessment.assigned", "assessment.submitted",
            "evidence.submitted", "evidence.resubmitted", "manager.evidence_decided",
            "manager.result_decided", "notification.created"} <= actions


def test_result_sendback_and_requeue_does_not_confirm(demo):
    a, _ = scored(demo)
    decide(demo, a, decision="send_back")
    g = demo.Finance
    assert demo.call("GET", "/leader/aggregates", g["leader"])["groups"] == []
    revision = demo.call("GET", f"/assessments/{a}", g["employee"])["review_revision"]
    demo.call("POST", f"/assessments/{a}/resubmit-review", g["employee"],
              {"expected_revision": revision, "comment": "Please review the supplied explanation"})
    decide(demo, a)
    assert len(demo.call("GET", f"/assessments/{a}/history", g["employee"])["decisions"]) == 2
    decide(demo, a, expected=409)


def test_new_calculated_level_does_not_replace_official(demo):
    first, _ = scored(demo)
    decide(demo, first)
    second, result = scored(demo, correct=0)
    assert result["achieved_level"] == 1
    gap = demo.call("GET", f"/users/{demo.Finance['employee']}/tni", demo.Finance["employee"])["skill_gaps"][0]
    assert gap["current_level"] == 1 and gap["official_confirmed_level"] == 3
    assert gap["proficiency_status"] == "provisional"
    assert demo.call("GET", "/leader/aggregates", demo.Finance["leader"])["groups"][0]["level"] == 3
    decide(demo, second)
    report = demo.call("GET", "/leader/aggregates", demo.Finance["leader"])
    assert report["total_confirmed_records"] == 1 and report["groups"][0]["level"] == 1
    assert report["groups"][0]["gap_count"] == 1


def test_older_result_cannot_replace_newer_confirmation(demo):
    first, _ = scored(demo)
    second, _ = scored(demo, correct=0)
    decide(demo, second)
    decide(demo, first, expected=409)


@pytest.mark.parametrize("path", ["/users", "/questions", "/roles", "/skills", "/assessments",
                                 "/evidence", "/leader/aggregates", "/notifications", "/audit-events", "/xp", "/quests"])
def test_authentication_required(secure_client, path):
    assert secure_client.get(path).status_code == 401


def test_identity_rejects_unknown_invalid_and_remote(demo):
    from fastapi.testclient import TestClient
    assert demo.client.get("/me", headers={"X-Demo-User-Id": "99999"}).status_code == 401
    assert demo.client.get("/me", headers={"X-Demo-User-Id": "-1"}).status_code == 422
    with TestClient(app, client=("203.0.113.10", 1234)) as remote:
        assert remote.get("/me", headers={"X-Demo-User-Id": str(demo.admin)}).status_code == 403


@pytest.mark.parametrize("kind", ["employee", "other", "manager", "leader"])
def test_answer_bank_is_reviewer_only(demo, kind):
    demo.call("GET", "/questions", demo.Finance[kind], expected=403)


def test_no_role_escalation_or_cross_employee_access(demo):
    g = demo.Finance
    assessment, _ = scored(demo)
    demo.call("POST", "/users", g["employee"], {"employee_id": "FAKE", "full_name": "Synthetic", "email": "x@example.invalid", "role": "admin"}, 403)
    for actor in (g["other"], g["reviewer"], g["leader"], demo.DataOps["manager"]):
        demo.call("GET", f"/assessments/{assessment}", actor, expected=403)
        demo.call("GET", f"/users/{g['employee']}/tni", actor, expected=403)
    assert [u["id"] for u in demo.call("GET", "/users", g["employee"])] == [g["employee"]]
    demo.call("POST", "/assessments", demo.DataOps["manager"],
              {"employee_id": g["employee"], "role_skill_map_id": g["mapping"], "question_count": 1}, 403)


def test_only_assigned_manager_decides(demo):
    a, _ = scored(demo)
    for actor in (demo.admin, demo.ld, demo.Finance["employee"], demo.Finance["reviewer"], demo.DataOps["manager"]):
        demo.call("POST", f"/assessments/{a}/decision", actor,
                  {"decision": "confirm", "comment": "Not authorized", "expected_revision": 1}, 403)
    demo.call("POST", f"/assessments/{a}/decision", demo.Finance["manager"],
              {"decision": "confirm", "comment": " ", "expected_revision": 1}, 422)
    demo.call("POST", f"/assessments/{a}/decision", demo.Finance["manager"],
              {"decision": "confirm", "comment": "Stale", "expected_revision": 99}, 409)


def test_cross_function_reviewer_and_leader_scope(demo):
    demo.call("POST", "/questions/generate", demo.DataOps["reviewer"],
              {"role_skill_map_id": demo.Finance["mapping"]}, 403)
    a, _ = scored(demo)
    decide(demo, a)
    assert demo.call("GET", "/leader/aggregates", demo.DataOps["leader"])["groups"] == []
    demo.call("GET", "/leader/aggregates", demo.Finance["employee"], expected=403)
    demo.call("GET", "/leader/aggregates?group_by=employee", demo.Finance["leader"], expected=422)
    assert demo.call("GET", "/leader/aggregates?function=DataOps", demo.Finance["leader"])["groups"] == []
    assert demo.call("GET", "/leader/aggregates?team=NoSuchTeam", demo.Finance["leader"])["groups"] == []


def test_notifications_are_scoped_and_idempotent(demo):
    g = demo.Finance
    notification = demo.call("POST", "/notifications", demo.ld,
        {"recipient_id": g["employee"], "title": "Synthetic update", "message": "Synthetic message"}, 201)
    demo.call("POST", "/notifications", g["employee"],
        {"recipient_id": g["other"], "title": "No", "message": "No"}, 403)
    demo.call("PATCH", f"/notifications/{notification['id']}/read", g["other"], expected=403)
    assert demo.call("GET", "/notifications/unread-count", g["employee"])["unread_count"] == 1
    assert demo.call("GET", "/notifications", g["other"]) == []
    first = demo.call("PATCH", f"/notifications/{notification['id']}/read", g["employee"])
    second = demo.call("PATCH", f"/notifications/{notification['id']}/read", g["employee"])
    assert first["read_at"] == second["read_at"]
    assert demo.call("GET", "/notifications/unread-count", g["employee"])["unread_count"] == 0
    events = demo.call("GET", "/audit-events?action=notification.read", g["employee"])
    assert len(events) == 1


def test_quests_xp_do_not_change_official_and_cannot_double_claim(demo):
    g = demo.Finance
    quest = demo.call("POST", "/quests", demo.ld, {"title": "Synthetic Quest", "description": "Submit a practice result",
        "event_type": "assessment.submitted", "required_count": 1, "xp_reward": 50, "business_function": "Finance"}, 201)
    demo.call("POST", f"/quests/{quest['id']}/claim", g["employee"], expected=409)
    a, _ = scored(demo)
    decide(demo, a)
    before = demo.call("GET", "/xp", g["employee"])["xp_points"]
    demo.call("POST", f"/quests/{quest['id']}/claim", g["employee"])
    demo.call("POST", f"/quests/{quest['id']}/claim", g["employee"])
    assert demo.call("GET", "/xp", g["employee"])["xp_points"] == before + 50
    assert demo.call("GET", "/leader/aggregates", g["leader"])["groups"][0]["level"] == 3
    demo.call("POST", f"/quests/{quest['id']}/claim", demo.DataOps["employee"], expected=403)


def test_evidence_only_confirms_evidence_not_proficiency(demo):
    g = demo.Finance
    evidence = demo.call("POST", "/evidence", g["employee"], {"role_skill_map_id": g["mapping"],
        "title": "Synthetic standalone", "description": "Synthetic work"}, 201)
    demo.call("POST", f"/evidence/{evidence['id']}/decision", g["manager"],
              {"decision": "confirm", "comment": "Evidence verified", "expected_revision": 1})
    assert demo.call("GET", "/leader/aggregates", g["leader"])["total_confirmed_records"] == 0
    demo.call("GET", f"/evidence/{evidence['id']}/history", g["other"], expected=403)
    demo.call("POST", f"/evidence/{evidence['id']}/resubmit", g["employee"],
              {"expected_revision": 1, "title": "Wrong state", "description": "Not sent back"}, 409)
    demo.call("POST", "/evidence", g["employee"], {"role_skill_map_id": g["mapping"],
        "title": "Unsafe URL", "description": "Synthetic", "url": "file:///private"}, 422)


@pytest.mark.parametrize("table", ["audit_events", "question_revisions", "evidence_revisions", "manager_decisions", "xp_awards"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_history_is_database_append_only(demo, table, operation):
    a, _ = scored(demo)
    g = demo.Finance
    e = demo.call("POST", "/evidence", g["employee"], {"role_skill_map_id": g["mapping"],
        "title": "Synthetic", "description": "Synthetic"}, 201)
    demo.call("POST", f"/evidence/{e['id']}/decision", g["manager"],
              {"decision": "confirm", "comment": "Synthetic review", "expected_revision": 1})
    with SessionLocal() as db:
        statement = f"UPDATE {table} SET id=id" if operation == "UPDATE" else f"DELETE FROM {table}"
        with pytest.raises(IntegrityError, match="append-only history"):
            db.execute(text(statement))
        db.rollback()


def test_question_versions_and_assessment_freeze(demo):
    g = demo.Finance
    q = demo.call("POST", "/questions/generate", g["reviewer"], {"role_skill_map_id": g["mapping"], "question_count": 1}, 201)[0]
    demo.call("PATCH", f"/questions/{q['id']}/review", g["reviewer"], {"status": "approved"})
    a = demo.call("POST", "/assessments", g["manager"], {"employee_id": g["employee"],
        "role_skill_map_id": g["mapping"], "question_count": 1}, 201)
    changed = {k: q[k] for k in ("question_text", "options", "correct_answer", "explanation")}
    changed.update(question_text="Revised fictional scenario", correct_answer="B", expected_revision=2, comment="Synthetic edit")
    demo.call("PATCH", f"/questions/{q['id']}", g["reviewer"], changed)
    demo.call("PATCH", f"/questions/{q['id']}", g["reviewer"], changed, 409)
    assert demo.call("GET", f"/assessments/{a['id']}", g["employee"])["questions"][0]["question_text"] == q["question_text"]
    result = demo.call("POST", f"/assessments/{a['id']}/submit", g["employee"],
        {"answers": [{"question_id": q["id"], "selected_answer": q["correct_answer"]}]})
    assert result["score_percentage"] == 100
    assert [r["action"] for r in demo.call("GET", f"/questions/{q['id']}/history", g["reviewer"])] == ["generated", "approved", "edited"]
    demo.call("GET", f"/questions/{q['id']}/history", g["employee"], expected=403)


def test_configured_critical_fail_policy_is_snapshotted(demo):
    g = demo.Finance
    demo.call("POST", f"/role-skill-maps/{g['mapping']}/scoring-policy", demo.ld,
              {"critical_fail_level": 0, "source_reference": "Synthetic test policy only"}, 201)
    q = demo.call("POST", "/questions/generate", g["reviewer"], {"role_skill_map_id": g["mapping"], "question_count": 1}, 201)[0]
    edited = {k: q[k] for k in ("question_text", "options", "correct_answer", "explanation")}
    edited.update(expected_revision=1, comment="Synthetic critical requirement", is_critical=True)
    demo.call("PATCH", f"/questions/{q['id']}", g["reviewer"], edited)
    demo.call("PATCH", f"/questions/{q['id']}/review", g["reviewer"], {"status": "approved"})
    a = demo.call("POST", "/assessments", g["manager"], {"employee_id": g["employee"],
        "role_skill_map_id": g["mapping"], "question_count": 1}, 201)
    demo.call("POST", f"/role-skill-maps/{g['mapping']}/scoring-policy", demo.ld,
              {"critical_fail_level": 2, "source_reference": "Later synthetic policy"}, 201)
    result = demo.call("POST", f"/assessments/{a['id']}/submit", g["employee"],
              {"answers": [{"question_id": q["id"], "selected_answer": "D"}]})
    assert result["achieved_level"] == 0
    assert demo.call("GET", f"/assessments/{a['id']}", g["employee"])["critical_failed"] is True


def test_sources_fail_gracefully_without_fabrication(demo, monkeypatch):
    def missing():
        raise FileNotFoundError("private path must not escape")
    monkeypatch.setattr("main.validate_workbooks", missing)
    assert demo.call("GET", "/data/validate", demo.admin)["status"] == "blocked"
    assert "private" not in json.dumps(demo.call("GET", "/sources/status", demo.admin))
    demo.call("POST", "/questions/generate", demo.admin,
              {"role_skill_map_id": demo.Finance["mapping"], "require_approved_sop": True}, 409)
    monkeypatch.setattr("main.validate_workbooks", lambda: {"issues": [{"missing_skill_count": 13}]})
    assert demo.call("GET", "/sources/status", demo.admin)["missing_finance_skill_references"] == 13


def test_unassessed_tni_is_not_level_zero(demo):
    g = demo.Finance
    result = demo.call("GET", f"/users/{g['employee']}/tni", g["employee"])
    assert result["skill_gaps"] == []
    assert result["unassessed_skills"][0]["current_level"] is None
    assert result["unassessed_skills"][0]["skill_gap"] is None


def test_failed_notification_rolls_back_business_event(demo, monkeypatch):
    g = demo.Finance
    def fail(*args, **kwargs):
        raise HTTPException(503, "Synthetic notification failure")
    from fastapi import HTTPException
    monkeypatch.setattr("main.notify", fail)
    demo.call("POST", "/questions/generate", g["reviewer"], {"role_skill_map_id": g["mapping"]}, 503)
    assert demo.call("GET", "/questions", g["reviewer"]) == []
    assert demo.call("GET", "/audit-events?action=question.generated", demo.admin) == []


def test_manager_inbox_and_profile_scope(demo):
    g = demo.Finance
    a, _ = scored(demo)
    inbox = demo.call("GET", "/manager/reviews", g["manager"])
    assert [r["assessment"]["id"] for r in inbox["results"]] == [a]
    assert demo.call("GET", "/manager/reviews", demo.DataOps["manager"])["results"] == []
    demo.call("GET", "/manager/reviews", g["employee"], expected=403)
    demo.call("PATCH", f"/users/{g['employee']}/profile", g["employee"], {"manager_id": demo.DataOps["manager"]}, 403)
    demo.call("PATCH", f"/users/{g['employee']}/profile", demo.admin, {"manager_id": demo.DataOps["manager"]}, 400)
    decide(demo, a)
    demo.call("PATCH", f"/users/{g['employee']}/profile", demo.admin, {"hub": "Hub B"})
    assert demo.call("GET", "/leader/aggregates", g["leader"])["groups"] == []
    assert demo.call("GET", "/leader/aggregates?hub=Hub B", demo.admin)["total_confirmed_records"] == 1


def test_unauthorized_evidence_and_audit_scope(demo):
    g = demo.Finance
    a, _ = scored(demo)
    demo.call("POST", "/evidence", g["other"], {"role_skill_map_id": g["mapping"], "assessment_id": a,
        "title": "Synthetic", "description": "Not the owner"}, 403)
    e = demo.call("POST", "/evidence", g["employee"], {"role_skill_map_id": g["mapping"],
        "title": "Synthetic", "description": "Synthetic"}, 201)
    demo.call("POST", f"/evidence/{e['id']}/decision", demo.DataOps["manager"],
              {"decision": "confirm", "comment": "Outside scope", "expected_revision": 1}, 403)
    events = demo.call("GET", "/audit-events?limit=500", demo.DataOps["leader"])
    assert all(event["subject_id"] != g["employee"] for event in events)
    assert demo.call("GET", "/leaderboard", g["leader"], expected=404)["detail"] == "Not Found"


def test_randomized_selection_calls_sampler_and_is_scoped(demo, monkeypatch):
    g = demo.Finance
    questions = demo.call("POST", "/questions/generate", g["reviewer"],
                          {"role_skill_map_id": g["mapping"], "question_count": 5}, 201)
    for q in questions:
        demo.call("PATCH", f"/questions/{q['id']}/review", g["reviewer"], {"status": "approved"})
    calls = []
    def sample(self, population, count):
        calls.append(len(population))
        return list(reversed(population))[:count]
    monkeypatch.setattr("assessment_service.random.SystemRandom.sample", sample)
    a = demo.call("POST", "/assessments", g["manager"], {"employee_id": g["employee"],
        "role_skill_map_id": g["mapping"], "question_count": 2}, 201)
    assigned = demo.call("GET", f"/assessments/{a['id']}", g["employee"])["questions"]
    assert calls == [5]
    assert [q["question_id"] for q in assigned] == [questions[-1]["id"], questions[-2]["id"]]


def test_missing_rag_skill_reference_is_never_substituted(monkeypatch):
    from rag_service import retrieve_finance_context
    rows = {"Role_Descriptions": [{"role_id": "SYN-R", "role_name": "Synthetic Role"}],
            "Skill_Master": [], "Role_Skill_Map": [{"role_id": "SYN-R", "skill_id": "MISSING", "skill": "Synthetic Skill",
                                                       "target_proficiency_level": 3}]}
    monkeypatch.setattr("rag_service.read_sheet", lambda file, sheet, header: rows[sheet])
    with pytest.raises(ValueError, match="reference"):
        retrieve_finance_context("Synthetic Role", "Synthetic Skill")
    with pytest.raises(ValueError, match="mapping"):
        retrieve_finance_context("Synthetic Role", "Synthetic")
    rows["Skill_Master"] = [{"skill_id": "MISSING", "L3_indicator": "Synthetic indicator fixture"}]
    context = retrieve_finance_context("Synthetic Role", "Synthetic Skill")
    assert len(context["matched_skills"]) == 1


def test_no_client_level_override_or_self_confirmation(demo):
    a, _ = scored(demo)
    g = demo.Finance
    demo.call("POST", f"/assessments/{a}/decision", g["manager"],
              {"decision": "confirm", "comment": "Synthetic", "expected_revision": 1, "confirmed_level": 5}, 422)
    with SessionLocal() as db:
        result = db.get(models.Assessment, a)
        result.employee_id = g["manager"]
        db.commit()
    demo.call("POST", f"/assessments/{a}/decision", g["manager"],
              {"decision": "confirm", "comment": "Self review", "expected_revision": 1}, 403)


def test_evidence_quest_counts_submission_not_resubmission(demo):
    g = demo.Finance
    quest = demo.call("POST", "/quests", demo.admin, {"title": "Synthetic evidence quest", "description": "Two submissions",
        "event_type": "evidence.submitted", "required_count": 2, "xp_reward": 25}, 201)
    e = demo.call("POST", "/evidence", g["employee"], {"role_skill_map_id": g["mapping"],
        "title": "Synthetic", "description": "Synthetic"}, 201)
    demo.call("POST", f"/evidence/{e['id']}/decision", g["manager"],
              {"decision": "send_back", "comment": "Add context", "expected_revision": 1})
    demo.call("POST", f"/evidence/{e['id']}/resubmit", g["employee"],
              {"expected_revision": 1, "title": "Synthetic revised", "description": "Synthetic revised"})
    progress = demo.call("GET", "/quests", g["employee"])[0]
    assert progress["progress"] == 1
    demo.call("POST", f"/quests/{quest['id']}/claim", g["employee"], expected=409)
