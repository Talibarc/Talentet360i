from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from learning_service import get_learning_resources
import config
from deterministic_tni import narrative
from schemas import EmployeeTniResponse, TniSkillGap, TniNarrative


def get_employee_tni(db: Session, employee_id: int):
    employee = db.get(models.User, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    assessments = (
        db.query(models.Assessment)
        .filter(models.Assessment.employee_id == employee_id,
                models.Assessment.status == "submitted")
        .order_by(models.Assessment.submitted_at.desc(), models.Assessment.id.desc()).all()
    )
    from types import SimpleNamespace
    expanded = []
    for assessment in assessments:
        details = db.query(models.AssessmentSkillResult).filter_by(assessment_id=assessment.id).all()
        expanded.extend([SimpleNamespace(id=assessment.id, role_skill_map_id=row.role_skill_map_id,
            achieved_level=row.achieved_level, score_percentage=row.score_percentage) for row in details] or [assessment])
    assessments = expanded
    seen = set()
    gaps = []
    for assessment in assessments:
        if config.LLM_PROVIDER == "luna" and not db.query(models.SourceRecord).filter_by(entity_type="mapping", entity_id=assessment.role_skill_map_id).first():
            continue
        if assessment.role_skill_map_id in seen:
            continue
        seen.add(assessment.role_skill_map_id)
        mapping = db.get(models.RoleSkillMap, assessment.role_skill_map_id)
        if mapping is None or not mapping.is_expected or mapping.target_level is None:
            continue
        skill = db.get(models.Skill, mapping.skill_id)
        role = db.get(models.Role, mapping.role_id)
        if skill is None or role is None:
            continue
        current = assessment.achieved_level
        gap = max(mapping.target_level - current, 0) if current is not None else None
        resources, learning_status = source_learning(db, skill, role.business_function)
        facts = dict(skill_name=skill.name, score_percentage=assessment.score_percentage,
                     current_level=current, target_level=mapping.target_level, skill_gap=gap)
        detail = (narrative(facts, [r.model_dump() for r in resources]) if current is not None else
            TniNarrative(summary="Result pending policy validation. No proficiency level or gap has been inferred.",
                development_focus="Validate the score-to-level policy before confirming proficiency.",
                next_steps=["Ask L&D for an approved scoring and proficiency policy."],
                recommended_resource_ids=[], limitations=["Workbook example results are not a validated scoring policy."]))
        allowed = {r.resource_id: r for r in resources}
        selected = detail.recommended_resource_ids
        if len(set(selected)) != len(selected) or any(key not in allowed for key in selected):
            raise ValueError("Invalid deterministic resource mapping")
        # Official recommendations use the same deterministic engine as Skill Intelligence.
        source_mapping = db.query(models.SourceRecord).filter_by(entity_type="mapping", entity_id=mapping.id).first()
        if source_mapping:
            from intelligence_service import validated_courses
            from schemas import LearningResource
            official_for_courses = db.query(models.OfficialLevel).filter_by(employee_id=employee_id, role_skill_map_id=mapping.id).first()
            courses, learning_status = validated_courses(db, employee.employee_id, source_mapping,
                official_for_courses.confirmed_level if official_for_courses else None, mapping.target_level)
            resources = [LearningResource(resource_id=c["course_id"], title=c["title"],
                source_file=c["provenance"][1]["workbook"], source_sheet=c["provenance"][1]["sheet"],
                source_row=c["provenance"][1]["row"], mapping_sheet=c["provenance"][0]["sheet"],
                mapping_row=c["provenance"][0]["row"], source_skill_id=source_mapping.details["skill_key"],
                review_status="Approved") for c in courses]
            allowed = {r.resource_id:r for r in resources}
            selected = list(allowed)
            detail.recommended_resource_ids = selected
            if not selected:
                detail.next_steps = ["No validated course recommendation available."]
        recommended = [] if current is None else [allowed[key] for key in selected]
        if current is None and resources:
            learning_status = "Recommendation pending policy validation; exact workbook mappings remain source metadata"
        official = db.query(models.OfficialLevel).filter_by(employee_id=employee_id,
                                                           role_skill_map_id=mapping.id).first()
        review = db.get(models.ResultReview, assessment.id)
        gaps.append(TniSkillGap(
            assessment_id=assessment.id, role_skill_map_id=mapping.id, skill_id=skill.id,
            **facts, gap_status="Pending policy validation" if gap is None else ("Target met" if gap == 0 else "Development needed"),
            expert_confirmation_required=current is None or current >= 3, recommendation=detail.development_focus,
            detail=detail, learning_resources=recommended, learning_status=learning_status,
            official_confirmed_level=official.confirmed_level if official else None,
            official_assessment_id=official.assessment_id if official else None,
            proficiency_status="confirmed" if official and official.assessment_id == assessment.id else "provisional",
            review_status=review.status if review else "pending_review",
        ))
    unassessed = []
    profile = db.get(models.UserProfile, employee_id)
    if profile and profile.job_role_id:
        for mapping in db.query(models.RoleSkillMap).filter_by(role_id=profile.job_role_id, is_expected=True):
            if config.LLM_PROVIDER == "luna" and not db.query(models.SourceRecord).filter_by(entity_type="mapping", entity_id=mapping.id).first():
                continue
            if mapping.target_level is not None and mapping.id not in seen:
                skill = db.get(models.Skill, mapping.skill_id)
                resources, learning_status = source_learning(db, skill, profile.business_function or "")
                if resources:
                    learning_status = "Recommendation pending assessment; exact workbook mappings remain source metadata"
                unassessed.append({"role_skill_map_id": mapping.id, "skill_id": skill.id, "skill_name": skill.name,
                    "current_level": None, "target_level": mapping.target_level, "target_label": mapping.target_label, "skill_gap": None,
                    "status": "not_assessed", "learning_resources": [],
                    "learning_status": learning_status})
    target_met = sum(item.skill_gap == 0 for item in gaps)
    return EmployeeTniResponse(
        employee_id=employee.id, employee_code=employee.employee_id,
        employee_name=employee.full_name, xp_points=employee.xp_points,
        skills_assessed=len(gaps), target_met=target_met,
        development_needed=sum(item.skill_gap is not None and item.skill_gap > 0 for item in gaps), provider=config.LLM_PROVIDER, skill_gaps=gaps,
        unassessed_skills=unassessed,
    )


def source_learning(db, skill, function):
    from schemas import LearningResource
    source = db.query(models.SourceRecord).filter_by(entity_type="skill", entity_id=skill.id).first()
    if not source:
        return get_learning_resources(skill.name, function)
    rows = db.query(models.SourceRecord).filter_by(entity_type="learning", workbook=source.workbook).all()
    resources = [LearningResource(**{k: v for k, v in row.details.items() if k != "skill_key"})
                 for row in rows if row.fingerprint and row.details.get("skill_key") == source.source_key]
    return resources, ("Workbook-mapped resources; approval and suitability require review" if resources
                       else "Mapping unavailable — pending source validation.")
