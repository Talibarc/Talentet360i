"""Explicit, idempotent synthetic demo setup. Never imports or repairs company workbooks."""
import json
import config
import models
from database import Base, engine, SessionLocal
from event_service import audit


def seed_demo():
    if config.LLM_PROVIDER != "mock":
        raise RuntimeError("Synthetic demo setup requires LLM_PROVIDER=mock")
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        identities = []
        def user(code, role, business_function=None, job_role_id=None, manager_id=None):
            existing = db.query(models.User).filter_by(employee_id=code).first()
            if existing:
                if existing.role != role or not existing.email.endswith("@example.invalid"):
                    raise RuntimeError("Demo identity conflicts with an existing non-demo record")
                identities.append({"id": existing.id, "role": role, "function": business_function})
                return existing
            row = models.User(employee_id=code, full_name=f"Synthetic {code}",
                email=f"{code.lower()}@example.invalid", role=role, department=business_function)
            db.add(row)
            db.flush()
            db.add(models.UserProfile(user_id=row.id, job_role_id=job_role_id, manager_id=manager_id,
                business_function=business_function, team="Synthetic Team" if business_function else None,
                hub="Synthetic Hub" if business_function else None))
            audit(db, None, "demo.identity_created", "user", row.id, subject_id=row.id, details={"synthetic": True})
            identities.append({"id": row.id, "role": role, "function": business_function})
            return row
        admin = user("DEMO-ADMIN", "admin")
        user("DEMO-LD", "ld")
        mappings = []
        for function in ("Finance", "DataOps"):
            role = db.query(models.Role).filter_by(role_code=f"DEMO-{function}").first()
            if not role:
                role = models.Role(role_code=f"DEMO-{function}", role_name=f"Synthetic {function} Analyst",
                                   business_function=function, level_framework="SYNTHETIC_DEMO_0_5")
                db.add(role)
                db.flush()
            skill = db.query(models.Skill).filter_by(name=f"Synthetic {function} Practice").first()
            if not skill:
                skill = models.Skill(name=f"Synthetic {function} Practice", max_level=5,
                                     description="Fictional demo fixture, not a company skill or repaired source reference")
                db.add(skill)
                db.flush()
            mapping = db.query(models.RoleSkillMap).filter_by(role_id=role.id, skill_id=skill.id).first()
            if not mapping:
                mapping = models.RoleSkillMap(role_id=role.id, skill_id=skill.id, target_level=3,
                                              target_label="Synthetic demo target", is_expected=True)
                db.add(mapping)
                db.flush()
                audit(db, admin.id, "demo.mapping_created", "mapping", mapping.id, details={"synthetic": True})
            manager = user(f"DEMO-{function}-MANAGER", "manager", function)
            user(f"DEMO-{function}-REVIEWER", "reviewer", function)
            user(f"DEMO-{function}-LEADER", "leader", function)
            user(f"DEMO-{function}-EMPLOYEE", "employee", function, role.id, manager.id)
            mappings.append({"function": function, "role_skill_map_id": mapping.id})
        return {"synthetic_only": True, "identities": identities, "mappings": mappings}


if __name__ == "__main__":
    print(json.dumps(seed_demo(), indent=2))
