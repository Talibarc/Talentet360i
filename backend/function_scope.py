"""Function boundaries and audit attribution, independent of generation providers."""
from fastapi import HTTPException
import models

WORKBOOKS = {"Finance": "finance_assessment.xlsx", "DataOps": "overall_rd.xlsx"}


def function_scope(db, actor):
    if actor.role == "admin":
        return None
    person = db.get(models.UserProfile, actor.id) if actor.id else None
    # Legacy unscoped L&D is internal-only; never listed by the normal selector.
    return person.business_function if person else None


def check_function(db, actor, function):
    scope = function_scope(db, actor)
    if scope and scope != function:
        raise HTTPException(403, "This action is outside your function")
    if actor.role not in {"admin", "ld"} and not scope:
        raise HTTPException(403, "Your function has not been configured")


def workbook_for(db, actor):
    return WORKBOOKS.get(function_scope(db, actor))


def scoped_report(report, workbook):
    if not workbook:
        return report
    return {"counts": {workbook: report.get("counts", {}).get(workbook, {})},
            "issues": [r for r in report.get("issues", []) if r.get("workbook") == workbook],
            "changed": report.get("changed", 0),
            "limitations": ["Scoring and training suitability require approved policy."]}


def event_function(db, entity_type, entity_id, subject_id=None, details=None):
    details = details or {}
    if details.get("business_function") in WORKBOOKS:
        return details["business_function"]
    if entity_type in {"rag_batch", "source_document"}:
        return "DataOps"
    if entity_type == "source":
        record = db.get(models.SourceRecord, entity_id) if entity_id else None
        workbook = record.workbook if record else details.get("workbook")
        return next((f for f, w in WORKBOOKS.items() if w == workbook), None)
    if entity_type == "question":
        scope = db.get(models.QuestionScope, entity_id)
        return event_function(db, "mapping", scope.role_skill_map_id) if scope else None
    if entity_type in {"mapping", "role_skill_map"}:
        mapping = db.get(models.RoleSkillMap, entity_id)
        return event_function(db, "role", mapping.role_id) if mapping else None
    if entity_type == "role":
        role = db.get(models.Role, entity_id)
        return role.business_function if role else None
    if entity_type == "scoring_policy":
        policy = db.get(models.ScoringPolicy, entity_id)
        return event_function(db, "mapping", policy.role_skill_map_id) if policy else None
    if entity_type == "quest":
        quest = db.get(models.Quest, entity_id)
        return quest.business_function if quest else None
    if entity_type == "assessment":
        assessment = db.get(models.Assessment, entity_id)
        return event_function(db, "mapping", assessment.role_skill_map_id) if assessment else None
    if entity_type == "evidence":
        evidence = db.get(models.Evidence, entity_id)
        return event_function(db, "mapping", evidence.role_skill_map_id) if evidence else None
    if entity_type == "notification" and not subject_id:
        notification = db.get(models.Notification, entity_id)
        subject_id = notification.recipient_id if notification else None
    if entity_type == "user":
        subject_id = entity_id
    person = db.get(models.UserProfile, subject_id) if subject_id else None
    return person.business_function if person else None


def visible_event(db, actor, event):
    scope = function_scope(db, actor)
    return not scope or event_function(db, event.entity_type, event.entity_id,
                                      event.subject_id, event.details) == scope


def ensure_function_demo_ld(db):
    """Add only local identities to an already seeded demo; no source/data reset."""
    from event_service import audit
    for function in WORKBOOKS:
        code = f"DEMO-{function}-LD"
        user = db.query(models.User).filter_by(employee_id=code).first()
        if user:
            person = db.get(models.UserProfile, user.id)
            if user.role != "ld" or not person or person.business_function != function or not user.email.endswith("@example.invalid"):
                raise HTTPException(409, "Demo L&D identity needs administrator review")
            continue
        user = models.User(employee_id=code, full_name=f"Demo {function} L&D",
                           email=f"demo-{function.lower()}-ld@example.invalid", role="ld", department=function)
        db.add(user); db.flush()
        db.add(models.UserProfile(user_id=user.id, business_function=function))
        db.flush()
        audit(db, None, "demo.identity_created", "user", user.id, subject_id=user.id,
              details={"synthetic": True})
