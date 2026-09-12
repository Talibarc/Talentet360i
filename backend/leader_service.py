from collections import defaultdict
from fastapi import HTTPException
from sqlalchemy import select
import models
from auth import require, profile


def aggregate(db, actor, group_by, filters):
    require(actor, "admin", "ld", "leader")
    dimensions = [value.strip() for value in group_by.split(",")]
    allowed = {"role", "team", "function", "hub", "skill", "level"}
    if not dimensions or len(set(dimensions)) != len(dimensions) or set(dimensions) - allowed:
        raise HTTPException(422, "Group by unique dimensions: role, team, function, hub, skill, level")
    query = select(models.OfficialLevel, models.RoleSkillMap, models.Role, models.Skill, models.UserProfile).join(
        models.RoleSkillMap, models.OfficialLevel.role_skill_map_id == models.RoleSkillMap.id).join(
        models.Role, models.RoleSkillMap.role_id == models.Role.id).join(
        models.Skill, models.RoleSkillMap.skill_id == models.Skill.id).join(
        models.UserProfile, models.OfficialLevel.employee_id == models.UserProfile.user_id).join(
        models.ManagerDecision, models.OfficialLevel.decision_id == models.ManagerDecision.id).where(
        models.ManagerDecision.decision == "confirm", models.ManagerDecision.assessment_id == models.OfficialLevel.assessment_id,
        models.RoleSkillMap.is_expected.is_(True), models.RoleSkillMap.target_level.is_not(None),
        models.UserProfile.job_role_id == models.Role.id,
        models.UserProfile.business_function == models.Role.business_function)
    if actor.role == "leader":
        scope = profile(db, actor.id)
        if not scope or not scope.business_function:
            raise HTTPException(403, "Leader reporting scope has not been configured")
        query = query.where(models.UserProfile.business_function == scope.business_function)
        for key in ("team", "hub"):
            if getattr(scope, key):
                query = query.where(getattr(models.UserProfile, key) == getattr(scope, key))
    columns = {"role_id": models.Role.id, "team": models.UserProfile.team,
               "function": models.UserProfile.business_function, "hub": models.UserProfile.hub,
               "skill_id": models.Skill.id, "level": models.OfficialLevel.confirmed_level}
    for key, value in filters.items():
        if value is not None:
            query = query.where(columns[key] == value)
    groups = defaultdict(lambda: {"count": 0, "gap_count": 0, "total_gap": 0})
    total = 0
    for official, mapping, role, skill, member in db.execute(query):
        values = {"role": (role.id, role.role_name), "skill": (skill.id, skill.name), "team": member.team,
                  "function": member.business_function, "hub": member.hub, "level": official.confirmed_level}
        key = tuple(values[d] for d in dimensions)
        gap = max(mapping.target_level - official.confirmed_level, 0)
        groups[key]["count"] += 1
        groups[key]["gap_count"] += int(gap > 0)
        groups[key]["total_gap"] += gap
        total += 1
    rows = []
    for key, metrics in sorted(groups.items(), key=lambda entry: repr(entry[0])):
        row = dict(zip(dimensions, key))
        for dimension in ("role", "skill"):
            if dimension in row:
                row[dimension + "_id"], row[dimension] = row[dimension]
        rows.append({**row, **metrics})
    return {"basis": "manager_confirmed_only", "unit": "employee-skill records",
            "total_confirmed_records": total, "groups": rows}
