"""Original workbooks are read-only; malformed cases alter parsed rows in memory."""
import copy
from collections import Counter
import hashlib

import pytest
import models
import source_import as source
from database import SessionLocal
from seed_workbook_demo import seed_workbook_demo


def make_test_preview_assessment(critical=False):
    """Exercise downstream behavior without claiming this one-item fixture is schedulable."""
    with SessionLocal.begin() as db:
        employee = db.query(models.User).filter_by(employee_id="DEMO-Finance-EMPLOYEE").one()
        question = db.query(models.Question).filter_by(status="approved").order_by(models.Question.id).first()
        if critical:
            record = next(r for r in db.query(models.SourceRecord).filter_by(entity_type="question")
                          if r.details["status"] == "approved" and r.details["is_critical"])
            question = db.get(models.Question, record.entity_id)
        scope = db.get(models.QuestionScope, question.id)
        assessment = models.Assessment(employee_id=employee.id, role_skill_map_id=scope.role_skill_map_id,
            status="assigned", total_questions=1)
        db.add(assessment); db.flush()
        db.add(models.AssessmentSnapshot(assessment_id=assessment.id, target_level=question.skill_level,
            policy={"pending_validation": True, "source_reference": "Test of source-policy boundary"}))
        item = models.AssessmentItem(assessment_id=assessment.id, question_id=question.id)
        db.add(item); db.flush()
        revision = db.query(models.QuestionRevision).filter_by(question_id=question.id).order_by(
            models.QuestionRevision.revision.desc()).first()
        db.add(models.ItemSnapshot(item_id=item.id, revision_id=revision.id, content=copy.deepcopy(revision.snapshot)))
        return assessment.id, question.id, employee.id, scope.role_skill_map_id


@pytest.fixture(scope="module")
def originals():
    return source.source_plan()


@pytest.fixture
def planned(monkeypatch, originals):
    monkeypatch.setattr(source, "source_plan", lambda: copy.deepcopy(originals))
    return originals


def test_authoritative_inventory_and_frameworks(originals):
    rows, report = originals
    assert len(report["inventory"][source.FINANCE_FILE.name]["sheets"]) == 26
    assert len(report["inventory"][source.RD_FILE.name]["sheets"]) == 11
    for path in (source.FINANCE_FILE, source.RD_FILE):
        assert report["inventory"][path.name]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert report["counts"][source.FINANCE_FILE.name] == dict(skill=28, role=9, role_description=12, mapping=60, question=49, learning=30)
    assert report["counts"][source.RD_FILE.name] == dict(skill=38, role=3, mapping=114, learning=38, question_source=1)
    rd = [r["details"] for r in rows if r["workbook"] == source.RD_FILE.name and r["entity_type"] == "mapping"]
    assert Counter(r["role_key"] for r in rd if r["is_expected"]) == {"B2": 17, "B3": 31, "B4": 38}
    assert sum(r["target_level"] is None and not r["is_expected"] for r in rd) == 28
    assert {r["target_label"]: r["target_level"] for r in rd} == {
        "Beginner": 1, "Moderate": 2, "Expert": 3, "Not Expected": None}
    question_source = next(r["details"] for r in rows if r["entity_type"] == "question_source")
    assert "Faiza" in question_source["title"]
    assert question_source["url"]
    assert question_source["use_rule"]
    assert question_source["availability_status"] == "Unavailable — excluded from MVP"
    assert question_source["audit_reference_only"] is True
    assert question_source["questions_imported"] == 0
    assert any("audit reference only" in item for item in report["limitations"])
    missing = {i["key"] for i in report["issues"] if i["reason"] == "Missing skill reference"}
    assert len(missing) == 13
    assert Counter(r["details"]["status"] for r in rows if r["entity_type"] == "question") == {
        "approved": 23, "pending_review": 26}
    assert report["finance_question_inventory"] == {
        "total_rows": 115, "incomplete_rows": 36, "safely_importable": 49}


def test_required_columns_fail_explicitly():
    with pytest.raises(ValueError, match="required columns missing"):
        source.table(source.FINANCE_FILE, "Role_Master", 3, ["unsupported_column"])


def test_import_idempotent_and_preserves_sources(planned):
    with SessionLocal.begin() as db:
        first = source.import_sources(db)
        ids = [(r.id, r.entity_id) for r in db.query(models.SourceRecord)]
        revisions = db.query(models.QuestionRevision).count()
        assert first["changed"] == 382
        assert source.import_sources(db)["changed"] == 0
        assert [(r.id, r.entity_id) for r in db.query(models.SourceRecord)] == ids
        assert db.query(models.QuestionRevision).count() == revisions
        assert "review triage only" in db.query(models.Question).first().rag_source
        assert db.query(models.Role).count() == 12
        assert db.query(models.Skill).count() == 66
        assert db.query(models.RoleSkillMap).count() == 174
        assert db.query(models.XpAward).count() == 0
    for path in (source.FINANCE_FILE, source.RD_FILE):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == planned[1]["inventory"][path.name]["sha256"]


@pytest.mark.parametrize("mutation,reason", [
    ("duplicate", "Missing or duplicate source key"),
    ("target", "Invalid target level"),
    ("answer", "Incomplete question options or answer key"),
    ("role", "Missing role reference"),
])
def test_malformed_rows_reported_without_source_copies(monkeypatch, originals, mutation, reason):
    read = source.table
    def altered(path, sheet, header, required):
        rows = copy.deepcopy(read(path, sheet, header, required))
        if sheet == "Role_Skill_Map":
            if mutation == "duplicate": rows.append(copy.deepcopy(rows[0]))
            if mutation == "target": rows[0][1]["target_proficiency_level"] = "unsupported"
            if mutation == "role": rows[0][1]["role_id"] = "absent"
        if sheet == "Assessment_QBank" and mutation == "answer":
            rows[40][1]["correct_option"] = "Z"
        return rows
    monkeypatch.setattr(source, "table", altered)
    monkeypatch.setattr(source, "inspect_sources", lambda: originals[1]["inventory"])
    _, report = source.source_plan()
    assert any(i["reason"] == reason for i in report["issues"])


def test_safe_source_update_preserves_frozen_assessment(planned, monkeypatch):
    seed_workbook_demo()
    assessment, question_id, _, _ = make_test_preview_assessment()
    with SessionLocal.begin() as db:
        frozen = copy.deepcopy(db.query(models.ItemSnapshot).filter_by(
            item_id=db.query(models.AssessmentItem).filter_by(assessment_id=assessment).one().id).one().content)
        q = db.get(models.Question, question_id)
        record = db.query(models.SourceRecord).filter_by(entity_type="question", entity_id=q.id).one()
        key = record.source_key
    rows, report = copy.deepcopy(planned)
    changed = next(r for r in rows if r["entity_type"] == "question" and r["source_key"] == key)
    changed["details"]["question_text"] += " [in-memory regression change]"
    monkeypatch.setattr(source, "source_plan", lambda: copy.deepcopy((rows, report)))
    with SessionLocal.begin() as db:
        assert source.import_sources(db)["changed"] == 1
        assert db.get(models.Question, question_id).question_text.endswith("[in-memory regression change]")
        assert db.query(models.ItemSnapshot).first().content == frozen
        assert source.import_sources(db)["changed"] == 0


def test_workbook_journey_pending_policy_and_activity_xp(planned, secure_client):
    seed = seed_workbook_demo()
    assert seed["finance_assessment"] is None
    assert "Starting size is 20" in seed["finance_assessment_blocker"]
    assert seed_workbook_demo()["changed"] == 0
    assessment, _, emp, mapping = make_test_preview_assessment()
    identities = secure_client.get("/demo/identities").json()["identities"]
    def actor(role, function=None):
        return next(u["id"] for u in identities if u["role"] == role and u["business_function"] == function)
    def call(method, path, who, body=None, expected=200):
        r = secure_client.request(method, path, headers={"x-demo-user-id": str(who)}, json=body)
        assert r.status_code == expected, r.text
        return r.json()
    assert emp == actor("employee", "Finance")
    manager = actor("manager", "Finance")
    call("GET", "/data/inventory", emp, expected=403)
    for function in ("Finance", "DataOps"):
        employee = actor("employee", function)
        roles = call("GET", "/roles", employee)
        assert all(r["business_function"] == function for r in roles)
        maps = call("GET", "/role-skill-maps", employee)
        assert all(m["role_id"] in {r["id"] for r in roles} for m in maps)
        skills = call("GET", "/skills", employee)
        assert all(s["category"] and s["source_key"] for s in skills)
        if function == "DataOps": assert call("GET", "/assessments", employee) == []
    call("GET", f"/assessments/{assessment}", actor("employee", "DataOps"), expected=403)
    call("POST", "/assessments", manager,
         {"employee_id": emp, "role_skill_map_id": mapping, "question_count": 1}, expected=409)
    call("POST", "/assessments", manager,
         {"employee_id": emp, "role_skill_map_id": mapping, "question_count": 20}, expected=409)
    detail = call("GET", f"/assessments/{assessment}", emp)
    call("POST", "/questions/generate", actor("reviewer", "Finance"),
         {"role_skill_map_id": detail["assessment"]["role_skill_map_id"], "question_count": 1}, expected=409)
    assert all("correct_answer" not in q for q in detail["questions"])
    assert not any("Synthetic Finance Practice" in q["question_text"] for q in detail["questions"])
    assert call("POST", f"/assessments/{assessment}/start", emp)["status"] == "in_progress"
    call("POST", f"/assessments/{assessment}/start", emp)
    with SessionLocal() as db:
        key = {q.id: q.correct_answer for q in db.query(models.Question)}
    answers = [{"question_id": q["question_id"], "selected_answer": key[q["question_id"]]} for q in detail["questions"]]
    result = call("POST", f"/assessments/{assessment}/submit", emp, {"answers": answers})
    assert result["score_percentage"] == 100 and result["achieved_level"] is None
    assert result["xp_awarded"] == 10
    tni = call("GET", f"/users/{emp}/tni", emp)
    assert tni["skill_gaps"][0]["current_level"] is None
    assert tni["skill_gaps"][0]["skill_gap"] is None
    assert tni["skill_gaps"][0]["official_confirmed_level"] is None
    assert tni["development_needed"] == 0
    assert call("GET", "/manager/reviews", manager)["results"]
    call("POST", f"/assessments/{assessment}/decision", manager,
         {"decision": "confirm", "comment": "Must wait for validated policy", "expected_revision": 1}, expected=409)
    call("POST", f"/assessments/{assessment}/decision", manager,
         {"decision": "confirm", "confirmed_level": 3, "comment": "Unsupported override", "expected_revision": 1}, expected=422)
    assert call("GET", "/leader/aggregates", actor("leader", "Finance"))["total_confirmed_records"] == 0
    call("POST", f"/assessments/{assessment}/decision", manager,
         {"decision": "send_back", "comment": "Policy validation required", "expected_revision": 1})
    assert call("GET", "/notifications", emp)
    call("POST", f"/assessments/{assessment}/submit", emp, {"answers": answers}, expected=400)
    with SessionLocal() as db:
        assert db.query(models.XpAward).filter_by(employee_id=emp).count() == 1
        assert db.query(models.AuditEvent).filter_by(action="assessment.started", subject_id=emp).count() == 1
        assert db.query(models.AuditEvent).filter_by(action="assessment.submitted", subject_id=emp).count() == 1
        assert db.query(models.OfficialLevel).count() == 0


def test_source_needs_rewrite_cannot_be_approved_without_edit(planned, secure_client):
    seed_workbook_demo()
    with SessionLocal() as db:
        reviewer = db.query(models.User).filter_by(employee_id="DEMO-Finance-REVIEWER").one().id
        question = next(r.entity_id for r in db.query(models.SourceRecord).filter_by(entity_type="question")
                        if r.details["source_status"] == "Needs Rewrite")
    r = secure_client.patch(f"/questions/{question}/review", json={"status": "approved"},
                            headers={"x-demo-user-id": str(reviewer)})
    assert r.status_code == 409 and "Needs Rewrite" in r.json()["detail"]


def test_workbook_critical_error_is_an_insight_not_a_failure(planned, secure_client):
    seed_workbook_demo()
    assessment, question_id, employee, _ = make_test_preview_assessment(critical=True)
    headers = {"x-demo-user-id": str(employee)}
    detail = secure_client.get(f"/assessments/{assessment}", headers=headers).json()
    with SessionLocal() as db:
        question = db.get(models.Question, question_id)
        wrong = next(option for option in question.options if option != question.correct_answer)
    result = secure_client.post(f"/assessments/{assessment}/submit", headers=headers,
        json={"answers": [{"question_id": detail["questions"][0]["question_id"], "selected_answer": wrong}]})
    assert result.status_code == 200 and result.json()["achieved_level"] is None
    with SessionLocal() as db:
        snapshot = db.query(models.AssessmentSnapshot).filter_by(assessment_id=assessment).one()
        event = db.query(models.AuditEvent).filter_by(action="assessment.submitted", subject_id=employee).one()
        assert snapshot.critical_failed is False
        assert event.details["critical_failed"] is False
        assert event.details["critical_review_flag"] is True


def test_exact_learning_provenance_and_no_invented_courses(planned):
    from tni_service import source_learning
    with SessionLocal.begin() as db:
        source.import_sources(db)
        for record in db.query(models.SourceRecord).filter_by(entity_type="skill"):
            skill = db.get(models.Skill, record.entity_id)
            resources, _ = source_learning(db, skill, "Finance" if record.workbook == source.FINANCE_FILE.name else "DataOps")
            assert all(r.source_skill_id == record.source_key and r.source_file == record.workbook for r in resources)
        # Duplicate display names are qualified, but learning joins still use exact source IDs.
        qualified = db.query(models.Skill).filter(models.Skill.name.like("%[%]")).all()
        assert qualified


def test_removed_learning_mapping_is_withheld_and_restored_safely(planned, monkeypatch):
    from tni_service import source_learning
    with SessionLocal.begin() as db:
        source.import_sources(db)
    rows, report = copy.deepcopy(planned)
    removed = next(r for r in rows if r["entity_type"] == "learning")
    rows.remove(removed)
    monkeypatch.setattr(source, "source_plan", lambda: copy.deepcopy((rows, report)))
    with SessionLocal.begin() as db:
        result = source.import_sources(db)
        assert any("requires reconciliation" in i["reason"] for i in result["issues"])
        record = db.query(models.SourceRecord).filter_by(entity_type="skill", workbook=removed["workbook"],
            source_key=removed["details"]["skill_key"]).one()
        skill = db.get(models.Skill, record.entity_id)
        resources, _ = source_learning(db, skill, "Finance")
        assert removed["details"]["resource_id"] not in {r.resource_id for r in resources}
        monkeypatch.setattr(source, "source_plan", lambda: copy.deepcopy(planned))
        assert source.import_sources(db)["changed"] == 1
        resources, _ = source_learning(db, skill, "Finance")
        assert removed["details"]["resource_id"] in {r.resource_id for r in resources}
