from fastapi import HTTPException, status
from sqlalchemy.orm import Session
 
import models
 
 
def get_employee_tni(db: Session, employee_id: int):
    employee = db.get(models.User, employee_id)
 
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )
 
    assessments = (
        db.query(models.Assessment)
        .filter(
            models.Assessment.employee_id == employee_id,
            models.Assessment.status == "submitted",
        )
        .order_by(models.Assessment.id.desc())
        .all()
    )
 
    seen_mapping_ids = set()
    skill_gaps = []
 
    for assessment in assessments:
        if assessment.role_skill_map_id in seen_mapping_ids:
            continue
 
        seen_mapping_ids.add(assessment.role_skill_map_id)
 
        mapping = db.get(
            models.RoleSkillMap,
            assessment.role_skill_map_id,
        )
        if mapping is None:
            continue
 
        skill = db.get(models.Skill, mapping.skill_id)
        if skill is None:
            continue
 
        current_level = int(assessment.achieved_level or 0)
        target_level = int(mapping.target_level or 1)
        skill_gap = max(target_level - current_level, 0)
 
        expert_confirmation_required = current_level >= 3
 
        if skill_gap == 0 and expert_confirmation_required:
            gap_status = "Target met - confirmation pending"
            recommendation = (
                "Submit complex-work evidence for manager or SME confirmation."
            )
        elif skill_gap == 0:
            gap_status = "Target met"
            recommendation = "Continue practice to maintain this skill level."
        elif skill_gap == 1:
            gap_status = "Development needed"
            recommendation = (
                f"Complete Level {target_level} learning and reassess."
            )
        else:
            gap_status = "Priority development needed"
            next_level = min(current_level + 1, target_level)
            recommendation = (
                f"Start Level {next_level} learning and reassess."
            )
 
        skill_gaps.append(
            {
                "assessment_id": assessment.id,
                "role_skill_map_id": mapping.id,
                "skill_id": skill.id,
                "skill_name": skill.name,
                "score_percentage": assessment.score_percentage,
                "current_level": current_level,
                "target_level": target_level,
                "skill_gap": skill_gap,
                "gap_status": gap_status,
                "expert_confirmation_required": (
                    expert_confirmation_required
                ),
                "recommendation": recommendation,
            }
        )
 
    target_met = sum(
        item["skill_gap"] == 0 for item in skill_gaps
    )
 
    return {
        "employee_id": employee.id,
        "employee_code": employee.employee_id,
        "employee_name": employee.full_name,
        "xp_points": employee.xp_points,
        "skills_assessed": len(skill_gaps),
        "target_met": target_met,
        "development_needed": len(skill_gaps) - target_met,
        "skill_gaps": skill_gaps,
    }
 