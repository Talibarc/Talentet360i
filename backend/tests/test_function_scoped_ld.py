"""Normal L&D personas are function-scoped; the internal administrator remains separate."""
import models
from database import SessionLocal
from test_phase2 import demo


def scoped_ld(demo, function):
    return demo.call("POST", "/users", demo.admin, {
        "employee_id": f"SYN-{function}-LD",
        "full_name": f"Synthetic {function} L&D",
        "email": f"{function.lower()}-ld@example.invalid",
        "role": "ld",
        "business_function": function,
    }, 201)["id"]


def mapping_record(workbook, mapping_id, skill_id):
    return models.SourceRecord(
        workbook=workbook, sheet="Role Skill Map", source_row=mapping_id,
        source_key=f"mapping-{mapping_id}", entity_type="mapping", entity_id=mapping_id,
        fingerprint="fixture", details={"role_key": "Synthetic role", "skill_key": skill_id,
        "target_label": "Level 3", "is_expected": True},
    )


def test_scoped_ld_catalog_question_assessment_and_audit_boundaries(demo):
    finance_ld = scoped_ld(demo, "Finance")
    dataops_ld = scoped_ld(demo, "DataOps")
    finance, dataops = demo.Finance, demo.DataOps

    finance_question = demo.call("POST", "/questions/generate", finance["reviewer"], {
        "role_skill_map_id": finance["mapping"], "question_count": 1,
    }, 201)[0]
    dataops_question = demo.call("POST", "/questions/generate", dataops["reviewer"], {
        "role_skill_map_id": dataops["mapping"], "question_count": 1,
    }, 201)[0]
    for group, question in ((finance, finance_question), (dataops, dataops_question)):
        demo.call("PATCH", f"/questions/{question['id']}/review", group["reviewer"], {
            "status": "approved",
        })

    assert [row["id"] for row in demo.call("GET", "/questions", finance_ld)] == [finance_question["id"]]
    assert [row["id"] for row in demo.call("GET", "/questions", dataops_ld)] == [dataops_question["id"]]
    demo.call("GET", f"/questions/{dataops_question['id']}/history", finance_ld, expected=403)
    demo.call("POST", "/questions/generate", finance_ld, {
        "role_skill_map_id": dataops["mapping"], "question_count": 1,
    }, expected=403)

    finance_assessment = demo.call("POST", "/assessments", finance["manager"], {
        "employee_id": finance["employee"], "role_skill_map_id": finance["mapping"], "question_count": 1,
    }, 201)
    dataops_assessment = demo.call("POST", "/assessments", dataops["manager"], {
        "employee_id": dataops["employee"], "role_skill_map_id": dataops["mapping"], "question_count": 1,
    }, 201)
    assert [row["id"] for row in demo.call("GET", "/assessments", finance_ld)] == [finance_assessment["id"]]
    assert [row["id"] for row in demo.call("GET", "/assessments", dataops_ld)] == [dataops_assessment["id"]]
    demo.call("POST", "/assessments", finance_ld, {
        "employee_id": dataops["employee"], "role_skill_map_id": dataops["mapping"], "question_count": 1,
    }, expected=403)

    with SessionLocal.begin() as db:
        db.add_all([
            mapping_record("finance_assessment.xlsx", finance["mapping"], "FIN-SKILL"),
            mapping_record("overall_rd.xlsx", dataops["mapping"], "RD-SKILL"),
        ])

    finance_mappings = demo.call("GET", "/skill-intelligence/mappings", finance_ld)["mappings"]
    dataops_mappings = demo.call("GET", "/skill-intelligence/mappings", dataops_ld)["mappings"]
    assert [row["skill_id"] for row in finance_mappings] == ["FIN-SKILL"]
    assert [row["skill_id"] for row in dataops_mappings] == ["RD-SKILL"]
    finance_audit = demo.call("GET", "/audit-events?limit=500", finance_ld)
    dataops_audit = demo.call("GET", "/audit-events?limit=500", dataops_ld)
    finance_question_events = [event for event in finance_audit if event["entity_type"] == "question"]
    dataops_question_events = [event for event in dataops_audit if event["entity_type"] == "question"]
    assert any(event["entity_id"] == finance_question["id"] for event in finance_question_events)
    assert not any(event["entity_id"] == dataops_question["id"] for event in finance_question_events)
    assert any(event["entity_id"] == dataops_question["id"] for event in dataops_question_events)


def test_only_scoped_ld_can_archive_or_send_questions_for_review(demo):
    finance_ld = scoped_ld(demo, "Finance")
    dataops_ld = scoped_ld(demo, "DataOps")
    question = demo.call("POST", "/questions/generate", demo.Finance["reviewer"], {
        "role_skill_map_id": demo.Finance["mapping"], "question_count": 1,
    }, 201)[0]
    demo.call("PATCH", f"/questions/{question['id']}/review", demo.Finance["reviewer"], {
        "status": "approved",
    })
    payload = {"expected_revision": 2, "confirmed": True, "comment": "Retire this obsolete practice item"}
    for actor in (demo.Finance["reviewer"], demo.Finance["employee"], demo.Finance["manager"], demo.Finance["leader"]):
        demo.call("DELETE", f"/questions/{question['id']}", actor, payload, expected=403)
    demo.call("POST", f"/questions/{question['id']}/send-for-review", dataops_ld, payload, expected=403)
    reset = demo.call("POST", f"/questions/{question['id']}/send-for-review", finance_ld, payload)
    assert reset["status"] == "pending_review"
    history = demo.call("GET", f"/questions/{question['id']}/history", finance_ld)
    assert [row["action"] for row in history] == ["generated", "approved", "sent_for_review"]
    removed = demo.call("DELETE", f"/questions/{question['id']}", finance_ld, {
        **payload, "expected_revision": history[-1]["revision"],
    })
    assert removed["status"] == "archived"
    assert demo.call("GET", "/questions", finance_ld) == []
    history = demo.call("GET", f"/questions/{question['id']}/history", finance_ld)
    assert [row["action"] for row in history] == ["generated", "approved", "sent_for_review", "archived"]
    events = demo.call("GET", "/audit-events?action=question.archived", finance_ld)
    assert len(events) == 1 and events[0]["details"]["business_function"] == "Finance"
