from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from learning_service import get_learning_resources
from llm_provider import get_provider, ProviderError
from schemas import EmployeeTniResponse, TniSkillGap


def get_employee_tni(db: Session, employee_id: int):
    employee = db.get(models.User, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    provider = get_provider()
    assessments = (
        db.query(models.Assessment)
        .filter(models.Assessment.employee_id == employee_id,
                models.Assessment.status == "submitted")
        .order_by(models.Assessment.submitted_at.desc(), models.Assessment.id.desc()).all()
    )
    seen = set()
    gaps = []
    for assessment in assessments:
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
        current = assessment.achieved_level or 0
        gap = max(mapping.target_level - current, 0)
        resources, learning_status = get_learning_resources(skill.name, role.business_function)
        facts = dict(skill_name=skill.name, score_percentage=assessment.score_percentage,
                     current_level=current, target_level=mapping.target_level, skill_gap=gap)
        detail = provider.tni(facts, [r.model_dump() for r in resources])
        allowed = {r.resource_id: r for r in resources}
        selected = detail.recommended_resource_ids
        if len(set(selected)) != len(selected) or any(key not in allowed for key in selected):
            raise ProviderError("Provider recommended a resource absent from supplied mappings")
        # Resource titles, URLs and citations come from workbook rows, never the LLM.
        recommended = [allowed[key] for key in selected]
        official = db.query(models.OfficialLevel).filter_by(employee_id=employee_id,
                                                           role_skill_map_id=mapping.id).first()
        review = db.get(models.ResultReview, assessment.id)
        gaps.append(TniSkillGap(
            assessment_id=assessment.id, role_skill_map_id=mapping.id, skill_id=skill.id,
            **facts, gap_status="Target met" if gap == 0 else "Development needed",
            expert_confirmation_required=current >= 3, recommendation=detail.development_focus,
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
            if mapping.target_level is not None and mapping.id not in seen:
                skill = db.get(models.Skill, mapping.skill_id)
                resources, learning_status = get_learning_resources(skill.name, profile.business_function or "")
                unassessed.append({"role_skill_map_id": mapping.id, "skill_id": skill.id, "skill_name": skill.name,
                    "current_level": None, "target_level": mapping.target_level, "skill_gap": None,
                    "status": "not_assessed", "learning_resources": [r.model_dump() for r in resources],
                    "learning_status": learning_status})
    target_met = sum(item.skill_gap == 0 for item in gaps)
    return EmployeeTniResponse(
        employee_id=employee.id, employee_code=employee.employee_id,
        employee_name=employee.full_name, xp_points=employee.xp_points,
        skills_assessed=len(gaps), target_met=target_met,
        development_needed=len(gaps) - target_met, provider=provider.name, skill_gaps=gaps,
        unassessed_skills=unassessed,
    )
