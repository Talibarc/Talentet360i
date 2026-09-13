"""Import original sources and seed identities for a policy-safe Phase 4 demo.

Use a dedicated DATABASE_URL to retain the Phase 3 database as historical demo data.
"""
import json
import config
import models
from database import Base, engine, SessionLocal
from source_import import import_sources
from seed_demo import seed_demo


def seed_workbook_demo():
    if config.LLM_PROVIDER != "mock":
        raise RuntimeError("Workbook demo requires mock mode")
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        if db.query(models.Role).filter(models.Role.role_code.like("DEMO-%")).first():
            raise RuntimeError("Use a dedicated Phase 4 DATABASE_URL; retain the Phase 3 database as history")
        report = import_sources(db)
    identities = seed_demo(source_mode=True)
    with SessionLocal.begin() as db:
        employee = db.query(models.User).filter_by(employee_id="DEMO-Finance-EMPLOYEE").one()
        profile = db.get(models.UserProfile, employee.id)
        mapping = db.query(models.RoleSkillMap).join(models.QuestionScope,
            models.QuestionScope.role_skill_map_id == models.RoleSkillMap.id).join(models.Question,
            models.Question.id == models.QuestionScope.question_id).filter(
            models.RoleSkillMap.role_id == profile.job_role_id, models.Question.status == "approved"
        ).order_by(models.RoleSkillMap.id).first()
        if mapping:
            approved = db.query(models.Question).join(models.QuestionScope).filter(
                models.QuestionScope.role_skill_map_id == mapping.id, models.Question.status == "approved").count()
            report["finance_assessment"] = None
            report["finance_assessment_blocker"] = (
                f"Starting size is 20 with 6/8/6 difficulty coverage; only {approved} approved questions are exactly mapped to the selected skill.")
        report["demo_identities"] = len(identities["identities"])
    return report


if __name__ == "__main__":
    print(json.dumps(seed_workbook_demo(), indent=2))
