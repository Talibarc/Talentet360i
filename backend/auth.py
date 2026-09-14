"""Loopback-only demo identity selection. No public login or self-assigned privileges."""
from typing import Annotated
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
import models
import config

Db = Annotated[Session, Depends(get_db, scope="function")]
ADMIN_ROLES = {"admin", "ld"}


def current_user(request: Request, db: Db,
                 x_demo_user_id: Annotated[int | None, Header(gt=0)] = None):
    if request.client and request.client.host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(403, "Demo identity is available on loopback only")
    if not config.DEMO_IDENTITIES_ENABLED:
        raise HTTPException(403, "Demo identities are disabled in this environment.")
    if x_demo_user_id is None:
        raise HTTPException(401, "Select a demo identity with X-Demo-User-Id")
    user = db.get(models.User, x_demo_user_id)
    if user is None:
        raise HTTPException(401, "Unknown demo identity")
    return user


Actor = Annotated[models.User, Depends(current_user, scope="function")]


def require(actor, *roles):
    if actor.role not in roles:
        raise HTTPException(403, "Role does not permit this action")


def profile(db, user_id):
    return db.get(models.UserProfile, user_id) if user_id else None


def employee_access(db, actor, employee_id, *, write=False):
    employee = db.get(models.User, employee_id)
    if employee is None:
        raise HTTPException(404, "Employee not found")
    if actor.role in ADMIN_ROLES or actor.id == employee_id:
        return employee
    details = profile(db, employee_id)
    if not write and actor.role == "manager" and details and details.manager_id == actor.id:
        return employee
    raise HTTPException(403, "Employee is outside your scope")


def manager_access(db, actor, employee_id):
    require(actor, "manager")
    details = profile(db, employee_id)
    if actor.id == employee_id or not details or details.manager_id != actor.id:
        raise HTTPException(403, "Only the assigned manager may decide this result")
    manager_profile = profile(db, actor.id)
    if not manager_profile or not manager_profile.business_function or manager_profile.business_function != details.business_function:
        raise HTTPException(403, "Manager and employee function assignment must match")


def mapping_access(db, actor, mapping_id):
    mapping = db.get(models.RoleSkillMap, mapping_id)
    if mapping is None:
        raise HTTPException(404, "Role-skill mapping not found")
    if actor.role in ADMIN_ROLES:
        return mapping
    role = db.get(models.Role, mapping.role_id)
    details = profile(db, actor.id)
    if not details or details.business_function != role.business_function:
        raise HTTPException(403, "Mapping is outside your function")
    if actor.role == "employee" and details.job_role_id != mapping.role_id:
        raise HTTPException(403, "Mapping is outside your job role")
    return mapping
