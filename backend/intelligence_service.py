"""Deterministic, scoped skill intelligence using exact imported identities."""
from collections import Counter
from fastapi import HTTPException
import models
import config
from auth import require, profile, employee_access
from deterministic_tni import NO_COURSE

PENDING = "Pending policy validation."


def provenance(record):
    return {"workbook": record.workbook, "sheet": record.sheet, "row": record.source_row,
            "source_id": record.source_key, "fingerprint": record.fingerprint}


def validated_tni_row(db, employee_code, mapping_source, current, target):
    if not mapping_source or not mapping_source.fingerprint or current is None:
        return None
    values = mapping_source.details
    # TNI rows are employee-specific observations, never generalized into a policy.
    tni = [r for r in db.query(models.SourceRecord).filter_by(
        workbook=mapping_source.workbook, entity_type="tni") if r.fingerprint
        and r.details.get("user_id") == employee_code
        and r.details.get("role_id") == values.get("role_key")
        and r.details.get("skill_id") == values.get("skill_key")
        and r.details.get("current_level") == current
        and r.details.get("target_level") == target]
    if len(tni) != 1 or tni[0].details.get("validation_status") != "Approved":
        return None
    return tni[0]


def validated_courses(db, employee_code, mapping_source, current, target):
    row = validated_tni_row(db, employee_code, mapping_source, current, target)
    if row is None:
        return [], NO_COURSE
    tni = [row]
    course_id = tni[0].details.get("recommended_course_id")
    courses = [r for r in db.query(models.SourceRecord).filter_by(
        workbook=mapping_source.workbook, entity_type="course", source_key=course_id)
        if r.fingerprint and r.details.get("validation_status") == "Approved"]
    if not course_id or len(courses) != 1 or not courses[0].details.get("course_title"):
        return [], NO_COURSE
    return [{"course_id": course_id, "title": courses[0].details.get("course_title"),
             "details": courses[0].details, "reason": tni[0].details.get("tni_recommendation"),
             "provenance": [provenance(tni[0]), provenance(courses[0])]}], "Validated exact TNI/course mapping"


def employee_skills(db, employee):
    person = profile(db, employee.id)
    if not person or not person.job_role_id:
        return []
    role = db.get(models.Role, person.job_role_id)
    result = []
    for mapping in db.query(models.RoleSkillMap).filter_by(role_id=role.id, is_expected=True):
        if mapping.target_level is None:
            continue
        skill = db.get(models.Skill, mapping.skill_id)
        source = db.query(models.SourceRecord).filter_by(entity_type="mapping", entity_id=mapping.id).first()
        valid = bool(source and source.fingerprint)
        if config.LLM_PROVIDER == "luna" and not valid:
            continue
        official = db.query(models.OfficialLevel).filter_by(employee_id=employee.id, role_skill_map_id=mapping.id).first()
        from sqlalchemy import or_
        assessments = db.query(models.Assessment).outerjoin(models.AssessmentSkillResult).filter(
            models.Assessment.employee_id == employee.id,
            or_(models.Assessment.role_skill_map_id == mapping.id,
                models.AssessmentSkillResult.role_skill_map_id == mapping.id)).order_by(models.Assessment.id.desc()).distinct().all()
        latest = next((a for a in assessments if a.status == "submitted"), None)
        current = official.confirmed_level if official and valid else None
        gap = max(mapping.target_level - current, 0) if current is not None else None
        courses, reason = validated_courses(db, employee.employee_id, source, current, mapping.target_level)
        history = db.query(models.ManagerDecision).join(models.Assessment,
            models.ManagerDecision.assessment_id == models.Assessment.id).filter(
            models.ManagerDecision.employee_id == employee.id, models.Assessment.role_skill_map_id == mapping.id,
            models.ManagerDecision.decision == "confirm", models.ManagerDecision.confirmed_level.isnot(None)
        ).order_by(models.ManagerDecision.created_at, models.ManagerDecision.id).all() if valid else []
        movement = [{"date": h.created_at, "level": h.confirmed_level} for h in history]
        tni_row = validated_tni_row(db, employee.employee_id, source, current, mapping.target_level)
        readiness = ("Target met" if gap == 0 else "Below target") if gap is not None else "Pending validation"
        result.append({"employee_id": employee.id, "employee_name": employee.full_name,
            "role_id": source.details.get("role_key") if valid else role.role_code,
            "role_name": role.role_name, "function": person.business_function,
            "team": person.team, "hub": person.hub,
            "skill_id": source.details.get("skill_key") if valid else None, "skill_name": skill.name,
            "role_skill_map_id": mapping.id, "current_level": current,
            "provisional_level": latest.achieved_level if latest else None,
            "target_level": mapping.target_level, "gap": gap,
            "gap_severity": "No gap" if gap == 0 else (tni_row.details.get("gap_severity") or PENDING) if tni_row else PENDING,
            "readiness": readiness, "assessment_status": assessments[0].status if assessments else "not_assessed",
            "policy_status": PENDING if latest and latest.achieved_level is None else
                ("Awaiting manager confirmation" if current is None else "Confirmed"),
            "recommendations": courses, "recommendation_status": reason,
            "mapping_status": "Validated source mapping" if valid else "Missing validated role-skill mapping",
            "provenance": [provenance(source)] if valid else [], "history": movement,
            "movement": movement[-1]["level"] - movement[0]["level"] if len(movement) > 1 else None})
    return result


def intelligence(db, actor, employee_id=None):
    require(actor, "admin", "ld", "employee", "manager", "leader")
    users = db.query(models.User).filter_by(role="employee")
    if employee_id is not None:
        if actor.role == "leader":
            raise HTTPException(403, "Leader views contain aggregates only")
        employee_access(db, actor, employee_id)
        users = users.filter(models.User.id == employee_id)
    elif actor.role == "employee":
        users = users.filter(models.User.id == actor.id)
    elif actor.role in {"manager", "leader"}:
        person = profile(db, actor.id)
        users = users.join(models.UserProfile, models.UserProfile.user_id == models.User.id).filter(models.UserProfile.business_function == (person.business_function if person else ""))
        if actor.role == "leader" and person:
            for field in ("team", "hub"):
                if getattr(person, field):
                    users = users.filter(getattr(models.UserProfile, field) == getattr(person, field))
        if actor.role == "manager":
            users = users.filter(models.UserProfile.manager_id == actor.id)
    employees = users.all()
    rows = [row for user in employees for row in employee_skills(db, user)]
    coverage = {"expected_records": len(rows), "validated_mappings": sum(bool(r["provenance"]) for r in rows),
        "validated_recommendations": sum(bool(r["recommendations"]) for r in rows),
        "missing_role_assignments": sum(not profile(db, u.id) or not profile(db, u.id).job_role_id for u in employees)}
    summary = dict(Counter(r["readiness"] for r in rows))
    groups = {}
    for row in rows:
        key = tuple(row[k] for k in ("function", "role_id", "team", "hub", "skill_id", "skill_name", "current_level", "readiness"))
        group = groups.setdefault(key, {k: row[k] for k in ("function", "role_id", "team", "hub", "skill_id", "skill_name", "current_level", "readiness") } | {"count": 0, "gap_count": 0, "movement_total": 0, "movement_records": 0})
        group["count"] += 1
        group["gap_count"] += int(row["gap"] is not None and row["gap"] > 0)
        if row["movement"] is not None:
            group["movement_total"] += row["movement"]
            group["movement_records"] += 1
    return {"basis": "Official confirmed levels; exact workbook joins; no AI recommendations",
        "coverage": coverage, "readiness": summary, "groups": list(groups.values()),
        "records": [] if actor.role == "leader" else rows,
        "limitations": [PENDING, "Gap severity and role-wide readiness thresholds require approved policy.",
            "No validated course recommendation available unless the exact TNI and catalogue records are approved."]}
