import json
import pytest
import config
import models
from database import SessionLocal
from offline_rag import load_index, retrieve
from intelligence_service import validated_courses
from test_phase2 import demo, scored, decide


def record(db, kind, key, details, entity_id=None, workbook="overall_rd.xlsx"):
    row = models.SourceRecord(workbook=workbook, sheet=kind, source_row=5, source_key=key,
        entity_type=kind, entity_id=entity_id, fingerprint="fixture-fingerprint", details=details)
    db.add(row)
    return row


@pytest.fixture
def remap_data(tmp_path, monkeypatch, demo):
    monkeypatch.setattr(config, "RAG_INDEX_DIR", tmp_path)
    source = {"source_id": "TEST_SOURCE", "skill_ids": ["RD_OLD"], "version": "fixed-version",
              "ingestion_status": "Ingested", "chunk_count": 1}
    chunk = {**source, "chunk_id": "TEST_CHUNK", "text": "Synthetic fixture only",
        "function": "DataOps", "approved_for_generation": True, "synthetic_only": False,
        "document_filename": "fixture.txt"}
    index = {"sources": [source], "chunks": [chunk]}
    (tmp_path / "index.json").write_text(json.dumps(index), encoding="utf-8")
    with SessionLocal.begin() as db:
        record(db, "source_metadata", "TEST_SOURCE", {})
        for key in ("RD_OLD", "RD_NEW", "RD_SECOND"):
            record(db, "skill", key, {"name": key})
    return tmp_path, demo


def remap_payload(**changes):
    return {"skill_ids": ["RD_NEW", "RD_SECOND"], "expected_skill_ids": ["RD_OLD"],
            "comment": "Correct synthetic mapping", "confirmed": True} | changes


def test_remap_preserves_content_versions_and_audits(remap_data):
    path, demo = remap_data
    original = (path / "index.json").read_bytes()
    result = demo.call("PATCH", "/rag/sources/TEST_SOURCE/skills", demo.ld, remap_payload())
    assert result["reindex_required"] is False
    assert (path / "index.json").read_bytes() == original
    index = load_index()
    assert index["sources"][0]["skill_ids"] == ["RD_NEW", "RD_SECOND"]
    assert index["chunks"][0]["version"] == "fixed-version"
    assert retrieve(function="DataOps", skill_id="RD_NEW", intended_proficiency=None, query="fixture")["chunk_references"] == ["TEST_CHUNK"]
    with SessionLocal() as db:
        event = db.query(models.AuditEvent).filter_by(action="source.skills_remapped").one()
        assert event.details["old_skill_ids"] == ["RD_OLD"]
        assert event.details["new_skill_ids"] == ["RD_NEW", "RD_SECOND"]
        assert db.query(models.SourceSkillOverride).count() == 1
    demo.call("PATCH", "/rag/sources/TEST_SOURCE/skills", demo.ld, remap_payload(), 409)


@pytest.mark.parametrize("role", ["employee", "manager", "reviewer", "leader"])
def test_remap_requires_ld(remap_data, role):
    _, demo = remap_data
    demo.call("PATCH", "/rag/sources/TEST_SOURCE/skills", demo.DataOps[role], remap_payload(), 403)


@pytest.mark.parametrize("changes,status", [({"skill_ids": ["INVENTED"]},422), ({"skill_ids": []},422), ({"confirmed":False},422), ({"expected_skill_ids":[]},409)])
def test_remap_validation(remap_data, changes, status):
    _, demo = remap_data
    demo.call("PATCH", "/rag/sources/TEST_SOURCE/skills", demo.ld, remap_payload(**changes), status)


def test_luna_import_is_local_and_provider_unchanged(demo, monkeypatch):
    import source_import
    monkeypatch.setattr(config, "LLM_PROVIDER", "luna")
    monkeypatch.setattr(source_import, "source_plan", lambda: ([], {"issues":[],"counts":{}}))
    monkeypatch.setattr("llm_provider.LunaProvider._generate", lambda *a: pytest.fail("No model call permitted"))
    assert demo.call("POST", "/data/import", demo.ld)["changed"] == 0
    assert config.LLM_PROVIDER == "luna"
    demo.call("POST", "/data/import", demo.Finance["employee"], expected=403)


@pytest.mark.parametrize("role", ["admin", "ld", "employee", "manager", "leader"])
def test_intelligence_scope_and_pending(demo, role):
    actor = getattr(demo, role) if role in {"admin", "ld"} else demo.Finance[role]
    data = demo.call("GET", "/skill-intelligence", actor)
    if role == "leader":
        assert data["records"] == []
        assert "employee_name" not in json.dumps(data)
    else:
        assert data["records"]
        assert all(r["current_level"] is None and r["recommendations"] == [] for r in data["records"])
        if role == "employee":
            assert {r["employee_id"] for r in data["records"]} == {actor}
        if role == "manager":
            assert {r["function"] for r in data["records"]} == {"Finance"}


def test_intelligence_privacy(demo):
    demo.call("GET", "/skill-intelligence", demo.Finance["reviewer"], expected=403)
    demo.call("GET", f"/skill-intelligence?employee_id={demo.DataOps['employee']}", demo.Finance["manager"], expected=403)
    demo.call("GET", f"/skill-intelligence?employee_id={demo.Finance['employee']}", demo.Finance["leader"], expected=403)


@pytest.mark.parametrize("change", [None, "wrong_skill", "wrong_role", "wrong_user", "wrong_level", "unapproved", "duplicate"])
def test_exact_course_join(change):
    with SessionLocal.begin() as db:
        mapping = record(db,"mapping","M",{"role_key":"R","skill_key":"S"})
        data = {"user_id":"E", "role_id":"R", "skill_id":"S", "current_level":1,"target_level":2,
                "recommended_course_id":"C", "validation_status":"Approved", "tni_recommendation":"Supplied rule"}
        if change == "wrong_skill": data["skill_id"] = "S-similar"
        if change == "wrong_role": data["role_id"] = "Other"
        if change == "wrong_user": data["user_id"] = "Other"
        if change == "wrong_level": data["current_level"] = 2
        if change == "unapproved": data["validation_status"] = "Pending"
        record(db,"tni","T",data)
        if change == "duplicate": record(db,"tni","T2",data)
        record(db,"course","C",{"course_title":"Synthetic course","validation_status":"Approved"})
        db.flush()
        courses, _ = validated_courses(db,"E",mapping,1,2)
        assert bool(courses) == (change is None)
        if courses:
            assert courses[0]["course_id"] == "C"
            assert len(courses[0]["provenance"]) == 2
        assert validated_courses(db,"E",mapping,None,2)[0] == []


def test_luna_tni_never_calls_provider(demo, monkeypatch):
    scored(demo)
    monkeypatch.setattr(config,"LLM_PROVIDER","luna")
    monkeypatch.setattr("llm_provider.LunaProvider._generate", lambda *a: pytest.fail("No model call permitted"))
    data = demo.call("GET", f"/users/{demo.Finance['employee']}/tni", demo.Finance["employee"])
    assert data["provider"] == "luna"
    assert demo.call("GET", "/skill-intelligence", demo.Finance["employee"])["records"] == []


def test_synthetic_catalog_hidden_in_luna(demo, monkeypatch):
    monkeypatch.setattr(config,"LLM_PROVIDER","luna")
    for endpoint in ("/roles","/skills","/role-skill-maps","/questions"):
        assert demo.call("GET",endpoint,demo.ld)==[]
    assert demo.call("GET","/skill-intelligence/mappings",demo.ld)["mappings"]==[]
    demo.call("GET","/skill-intelligence/mappings",demo.Finance["employee"],expected=403)


def test_regeneration_preserves_original_and_audits(demo):
    g=demo.Finance
    q=demo.call("POST","/questions/generate",demo.ld,{"role_skill_map_id":g["mapping"],"question_count":1},201)[0]
    new=demo.call("POST",f"/questions/{q['id']}/regenerate",g["reviewer"],expected=201)[0]
    assert new["id"] != q["id"] and new["status"] == "pending_review"
    demo.call("POST",f"/questions/{q['id']}/regenerate",g["employee"],expected=403)
    with SessionLocal() as db:
        assert db.get(models.Question,q["id"]).question_text == q["question_text"]
        event=db.query(models.AuditEvent).filter_by(action="question.regenerated").one()
        assert event.details["new_question_ids"] == [new["id"]]


def test_luna_hides_synthetic_assessments_and_aggregates(demo, monkeypatch):
    first, _ = scored(demo)
    decide(demo, first)
    scored(demo)
    g = demo.Finance
    assert demo.call("GET", "/leader/aggregates", g["leader"])["total_confirmed_records"] == 1
    assert demo.call("GET", "/manager/reviews", g["manager"])["results"]
    monkeypatch.setattr(config, "LLM_PROVIDER", "luna")
    assert demo.call("GET", "/leader/aggregates", g["leader"])["total_confirmed_records"] == 0
    assert demo.call("GET", "/manager/reviews", g["manager"])["results"] == []
    assert demo.call("GET", "/assessments", g["employee"]) == []
    demo.call("GET", f"/assessments/{first}", g["employee"], expected=409)
