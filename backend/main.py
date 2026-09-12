from typing import Annotated
from zipfile import BadZipFile
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import update, or_
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

import models
import schemas
import workflow_schemas as ws
import workflow_service as workflows
from database import Base, engine, get_db
from auth import Actor, current_user, require, mapping_access, employee_access, manager_access, profile
from event_service import audit, notify
from governance_service import record_question, scoped_question, latest_revision, edit, review
from assessment_service import create_assessment, get_assessment, submit_assessment
from question_service import generate_question_drafts
from llm_provider import ProviderError
from excel_loader import validate_workbooks
from rag_service import retrieve_finance_context
from leader_service import aggregate
from tni_service import get_employee_tni

# Additive tables only: the seven Phase 1 tables retain their original columns.
Base.metadata.create_all(bind=engine)
DbSession = Annotated[Session, Depends(get_db, scope="function")]
app = FastAPI(title="Talent360i API", version="2.0.0",
              description="Local synthetic demo. Select an identity with X-Demo-User-Id. Not enterprise authentication.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ProviderError)
async def provider_error_handler(request, error):
    return JSONResponse(status_code=503, content={"detail": str(error)})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request, error):
    return JSONResponse(status_code=409, content={"detail": "Conflicting record or concurrent change; reload and retry"})


@app.exception_handler(OperationalError)
async def database_error_handler(request, error):
    return JSONResponse(status_code=503, content={"detail": "Database unavailable or busy; retry the request"})


@app.get("/")
def home():
    return {"message": "Talent360i backend is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


def user_response(db, user):
    data = schemas.UserResponse.model_validate(user).model_dump()
    details = profile(db, user.id)
    if details:
        data.update({key: getattr(details, key) for key in PROFILE_FIELDS})
    return data


PROFILE_FIELDS = ("job_role_id", "manager_id", "business_function", "team", "hub")


@app.get("/me")
def me(db: DbSession, actor: Actor):
    return user_response(db, actor)


@app.post("/users", response_model=schemas.UserResponse, status_code=201)
def create_user(payload: schemas.UserCreate, db: DbSession, actor: Actor):
    require(actor, "admin", "ld")
    data = payload.model_dump()
    details = {key: data.pop(key) for key in PROFILE_FIELDS}
    if details["job_role_id"]:
        role = db.get(models.Role, details["job_role_id"])
        if not role:
            raise HTTPException(404, "Job role not found")
        if details["business_function"] and details["business_function"] != role.business_function:
            raise HTTPException(400, "Job role/function mismatch")
        details["business_function"] = role.business_function
    if details["manager_id"]:
        manager = db.get(models.User, details["manager_id"])
        if not manager or manager.role != "manager":
            raise HTTPException(400, "Assigned manager must have the manager role")
        manager_profile = profile(db, manager.id)
        if manager_profile and manager_profile.business_function != details["business_function"]:
            raise HTTPException(400, "Manager/function mismatch")
    if payload.role in {"leader", "reviewer", "manager"} and not details["business_function"]:
        raise HTTPException(400, "Configure a business function for this role")
    user = models.User(**data)
    db.add(user)
    db.flush()
    db.add(models.UserProfile(user_id=user.id, **details))
    audit(db, actor.id, "user.created", "user", user.id, subject_id=user.id, details={"role": user.role})
    return user_response(db, user)


@app.get("/users", response_model=list[schemas.UserResponse])
def list_users(db: DbSession, actor: Actor):
    query = db.query(models.User)
    if actor.role not in {"admin", "ld"}:
        if actor.role == "manager":
            query = query.outerjoin(models.UserProfile, models.UserProfile.user_id == models.User.id).filter(
                or_(models.User.id == actor.id, models.UserProfile.manager_id == actor.id))
        else:
            query = query.filter(models.User.id == actor.id)
    return [user_response(db, user) for user in query.order_by(models.User.id)]


@app.patch("/users/{user_id}/profile", response_model=schemas.UserResponse)
def update_profile(user_id: int, payload: ws.ProfileUpdate, db: DbSession, actor: Actor):
    require(actor, "admin", "ld")
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    details = profile(db, user_id)
    data = {key: getattr(details, key) if details else None for key in PROFILE_FIELDS}
    data.update(payload.model_dump(exclude_unset=True))
    if data["job_role_id"]:
        job = db.get(models.Role, data["job_role_id"])
        if not job:
            raise HTTPException(404, "Job role not found")
        if data["business_function"] and job.business_function != data["business_function"]:
            raise HTTPException(400, "Job role/function mismatch")
        data["business_function"] = job.business_function
    if data["manager_id"]:
        manager = db.get(models.User, data["manager_id"])
        manager_details = profile(db, data["manager_id"])
        if (data["manager_id"] == user_id or not manager or manager.role != "manager" or
            not manager_details or manager_details.business_function != data["business_function"]):
            raise HTTPException(400, "Assigned manager/function is invalid")
    if user.role in {"leader", "reviewer", "manager"} and not data["business_function"]:
        raise HTTPException(400, "This role requires a business function")
    if details is None:
        details = models.UserProfile(user_id=user_id)
        db.add(details)
    for key, value in data.items():
        setattr(details, key, value)
    audit(db, actor.id, "user.profile_updated", "user", user_id, subject_id=user_id, details=data)
    return user_response(db, user)


@app.post("/roles", response_model=schemas.RoleResponse, status_code=201)
def create_role(payload: schemas.RoleCreate, db: DbSession, actor: Actor):
    require(actor, "admin", "ld")
    role = models.Role(**payload.model_dump())
    db.add(role)
    db.flush()
    audit(db, actor.id, "role.created", "role", role.id)
    return role


@app.get("/roles", response_model=list[schemas.RoleResponse])
def list_roles(db: DbSession, actor: Actor):
    query = db.query(models.Role)
    if actor.role not in {"admin", "ld"}:
        details = profile(db, actor.id)
        query = query.filter(models.Role.business_function == (details.business_function if details else ""))
    return query.order_by(models.Role.id).all()


@app.post("/skills", response_model=schemas.SkillResponse, status_code=201)
def create_skill(payload: schemas.SkillCreate, db: DbSession, actor: Actor):
    require(actor, "admin", "ld")
    skill = models.Skill(**payload.model_dump())
    db.add(skill)
    db.flush()
    audit(db, actor.id, "skill.created", "skill", skill.id)
    return skill


@app.get("/skills", response_model=list[schemas.SkillResponse])
def list_skills(db: DbSession, actor: Actor):
    return db.query(models.Skill).order_by(models.Skill.id).all()


@app.post("/role-skill-maps", response_model=schemas.RoleSkillMapResponse, status_code=201)
def create_mapping(payload: schemas.RoleSkillMapCreate, db: DbSession, actor: Actor):
    require(actor, "admin", "ld")
    skill = db.get(models.Skill, payload.skill_id)
    if not db.get(models.Role, payload.role_id) or not skill:
        raise HTTPException(404, "Role or skill not found")
    if payload.target_level is not None and payload.target_level > skill.max_level:
        raise HTTPException(400, "Target level exceeds the supplied skill framework")
    if db.query(models.RoleSkillMap).filter_by(role_id=payload.role_id, skill_id=payload.skill_id).first():
        raise HTTPException(409, "Role-skill mapping already exists")
    mapping = models.RoleSkillMap(**payload.model_dump())
    db.add(mapping)
    db.flush()
    audit(db, actor.id, "mapping.created", "mapping", mapping.id)
    return mapping


@app.get("/role-skill-maps", response_model=list[schemas.RoleSkillMapResponse])
def list_mappings(db: DbSession, actor: Actor):
    query = db.query(models.RoleSkillMap)
    if actor.role not in {"admin", "ld"}:
        details = profile(db, actor.id)
        query = query.join(models.Role).filter(models.Role.business_function == (details.business_function if details else ""))
        if actor.role == "employee":
            query = query.filter(models.RoleSkillMap.role_id == (details.job_role_id if details else -1))
    return query.order_by(models.RoleSkillMap.id).all()


@app.post("/role-skill-maps/{mapping_id}/scoring-policy", status_code=201)
def configure_policy(mapping_id: int, payload: ws.PolicyCreate, db: DbSession, actor: Actor):
    require(actor, "admin", "ld")
    mapping_access(db, actor, mapping_id)
    policy = models.ScoringPolicy(role_skill_map_id=mapping_id,
        settings=payload.model_dump(exclude={"source_reference"}), source_reference=payload.source_reference)
    db.add(policy)
    db.flush()
    audit(db, actor.id, "scoring_policy.created", "scoring_policy", policy.id)
    return policy


@app.get("/data/validate")
def validate_source_data(db: DbSession, actor: Actor):
    require(actor, "admin", "ld")
    try:
        return validate_workbooks()
    except (OSError, ValueError, KeyError, BadZipFile):
        return {"status": "blocked", "issues": [{"issue": "Required workbook or sheet unavailable"}]}


@app.get("/sources/status")
def source_status(db: DbSession, actor: Actor):
    require(actor, "admin", "ld", "reviewer")
    try:
        result = validate_workbooks()
        missing = sum(issue.get("missing_skill_count", 0) for issue in result["issues"])
    except (OSError, ValueError, KeyError, BadZipFile):
        return {"status": "blocked", "reason": "Required source workbook unavailable", "approved_sop_available": False}
    return {"status": "needs_review", "missing_finance_skill_references": missing,
            "approved_sop_available": False,
            "reason": "Approved SOP/training documents have not been supplied or registered; mock exercises are synthetic"}


@app.get("/rag/context")
def rag_context(role_name: str, skill_name: str, db: DbSession, actor: Actor):
    require(actor, "admin", "ld", "reviewer")
    if actor.role == "reviewer" and (not profile(db, actor.id) or profile(db, actor.id).business_function != "Finance"):
        raise HTTPException(403, "Finance source context is outside your scope")
    try:
        return retrieve_finance_context(role_name, skill_name)
    except (OSError, ValueError, KeyError):
        raise HTTPException(409, "Required source context is missing or incomplete") from None


@app.post("/questions/generate", response_model=list[schemas.QuestionResponse], status_code=201)
def generate_questions(payload: schemas.QuestionGenerateRequest, db: DbSession, actor: Actor):
    require(actor, "admin", "ld", "reviewer")
    mapping = mapping_access(db, actor, payload.role_skill_map_id)
    if not mapping.is_expected or mapping.target_level is None:
        raise HTTPException(400, "Questions cannot be generated for a non-expected skill")
    if payload.require_approved_sop:
        raise HTTPException(409, "Approved SOP/training documents are unavailable; use explicitly synthetic mock exercises")
    role, skill = db.get(models.Role, mapping.role_id), db.get(models.Skill, mapping.skill_id)
    drafts = generate_question_drafts(role.role_name, skill.name, mapping.target_level,
        mapping.target_label or f"Level {mapping.target_level}", skill.description or "", payload.question_count)
    questions = []
    for draft in drafts:
        question = models.Question(skill_id=skill.id, skill_level=mapping.target_level,
            **draft.model_dump(), status="pending_review", created_by_id=actor.id)
        db.add(question)
        db.flush()
        db.add(models.QuestionScope(question_id=question.id, role_skill_map_id=mapping.id))
        record_question(db, question, actor.id, "generated")
        questions.append(question)
    reviewers = db.query(models.User).join(models.UserProfile, models.User.id == models.UserProfile.user_id).filter(
        models.User.role == "reviewer", models.UserProfile.business_function == role.business_function).all()
    for reviewer in reviewers:
        notify(db, reviewer.id, "Questions awaiting review", f"{len(questions)} draft questions require review.",
               "questions.generated", mapping.id, actor.id)
    return questions


@app.get("/questions", response_model=list[schemas.QuestionResponse])
def list_questions(db: DbSession, actor: Actor):
    require(actor, "admin", "ld", "reviewer")
    query = db.query(models.Question)
    if actor.role == "reviewer":
        details = profile(db, actor.id)
        query = query.join(models.QuestionScope).join(models.RoleSkillMap,
            models.QuestionScope.role_skill_map_id == models.RoleSkillMap.id).join(models.Role).filter(
            models.Role.business_function == (details.business_function if details else ""))
    return query.order_by(models.Question.id.desc()).all()


@app.patch("/questions/{question_id}/review", response_model=schemas.QuestionResponse)
def review_question(question_id: int, payload: schemas.QuestionReviewRequest, db: DbSession, actor: Actor):
    return review(db, actor, question_id, payload)


@app.patch("/questions/{question_id}", response_model=schemas.QuestionResponse)
def edit_question(question_id: int, payload: ws.QuestionEdit, db: DbSession, actor: Actor):
    return edit(db, actor, question_id, payload)


@app.get("/questions/{question_id}/history")
def question_history(question_id: int, db: DbSession, actor: Actor):
    scoped_question(db, actor, question_id)
    return db.query(models.QuestionRevision).filter_by(question_id=question_id).order_by(models.QuestionRevision.revision).all()


@app.post("/assessments", response_model=schemas.AssessmentResponse, status_code=201)
def assign_assessment(payload: schemas.AssessmentCreate, db: DbSession, actor: Actor):
    require(actor, "admin", "ld", "manager")
    if actor.role == "manager":
        manager_access(db, actor, payload.employee_id)
    return create_assessment(db, payload, actor.id)


@app.get("/assessments")
def list_assessments(db: DbSession, actor: Actor, employee_id: int | None = None):
    if employee_id is not None:
        employee_access(db, actor, employee_id)
        query = db.query(models.Assessment).filter_by(employee_id=employee_id)
    elif actor.role in {"admin", "ld"}:
        query = db.query(models.Assessment)
    elif actor.role == "manager":
        query = db.query(models.Assessment).join(models.UserProfile,
            models.Assessment.employee_id == models.UserProfile.user_id).filter(models.UserProfile.manager_id == actor.id)
    else:
        query = db.query(models.Assessment).filter_by(employee_id=actor.id)
    return query.order_by(models.Assessment.id.desc()).all()


def accessible_assessment(db, actor, assessment_id, write=False):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(404, "Assessment not found")
    employee_access(db, actor, assessment.employee_id, write=write)
    return assessment


@app.get("/assessments/{assessment_id}")
def read_assessment(assessment_id: int, db: DbSession, actor: Actor):
    accessible_assessment(db, actor, assessment_id)
    return get_assessment(db, assessment_id)


@app.post("/assessments/{assessment_id}/submit", response_model=schemas.AssessmentResult)
def complete_assessment(assessment_id: int, payload: schemas.AssessmentSubmitRequest, db: DbSession, actor: Actor):
    require(actor, "admin", "ld", "employee")
    accessible_assessment(db, actor, assessment_id, write=True)
    return submit_assessment(db, assessment_id, payload, actor.id)


@app.get("/users/{employee_id}/tni", response_model=schemas.EmployeeTniResponse)
def employee_tni(employee_id: int, db: DbSession, actor: Actor):
    employee_access(db, actor, employee_id)
    return get_employee_tni(db, employee_id)


@app.post("/evidence", status_code=201)
def evidence_create(payload: ws.EvidenceCreate, db: DbSession, actor: Actor):
    return workflows.submit_evidence(db, actor, payload)


@app.get("/evidence")
def evidence_list(db: DbSession, actor: Actor, employee_id: int | None = None):
    target = employee_id if employee_id is not None else actor.id
    employee_access(db, actor, target)
    return [workflows.evidence_content(db, e) for e in db.query(models.Evidence).filter_by(employee_id=target).order_by(models.Evidence.id)]


@app.get("/evidence/{evidence_id}/history")
def evidence_history(evidence_id: int, db: DbSession, actor: Actor):
    return workflows.evidence_history(db, actor, evidence_id)


@app.post("/evidence/{evidence_id}/resubmit")
def evidence_resubmit(evidence_id: int, payload: ws.EvidenceResubmit, db: DbSession, actor: Actor):
    return workflows.submit_evidence(db, actor, payload, evidence_id)


@app.post("/evidence/{evidence_id}/decision")
def evidence_decision(evidence_id: int, payload: ws.DecisionCreate, db: DbSession, actor: Actor):
    return workflows.decide_evidence(db, actor, evidence_id, payload)


@app.post("/assessments/{assessment_id}/decision")
def result_decision(assessment_id: int, payload: ws.DecisionCreate, db: DbSession, actor: Actor):
    return workflows.decide_result(db, actor, assessment_id, payload)


@app.post("/assessments/{assessment_id}/resubmit-review")
def result_resubmit(assessment_id: int, payload: ws.ReviewResubmit, db: DbSession, actor: Actor):
    return workflows.resubmit_result(db, actor, assessment_id, payload)


@app.get("/assessments/{assessment_id}/history")
def assessment_history(assessment_id: int, db: DbSession, actor: Actor):
    accessible_assessment(db, actor, assessment_id)
    return {"review": db.get(models.ResultReview, assessment_id),
            "decisions": db.query(models.ManagerDecision).filter_by(assessment_id=assessment_id).order_by(models.ManagerDecision.id).all()}


@app.get("/manager/reviews")
def manager_inbox(db: DbSession, actor: Actor):
    require(actor, "manager")
    reports = [p.user_id for p in db.query(models.UserProfile).filter_by(manager_id=actor.id,
        business_function=profile(db, actor.id).business_function if profile(db, actor.id) else "")]
    results = db.query(models.Assessment, models.ResultReview).join(models.ResultReview).filter(
        models.Assessment.employee_id.in_(reports), models.ResultReview.status == "pending_review").all()
    return {"results": [{"assessment": assessment, "review": review} for assessment, review in results],
            "evidence": [workflows.evidence_content(db, e) for e in db.query(models.Evidence).filter(
                models.Evidence.employee_id.in_(reports), models.Evidence.status == "submitted")]}


@app.get("/leader/aggregates")
def leader_aggregates(db: DbSession, actor: Actor, group_by: str = "skill,level", role_id: int | None = None,
                      team: str | None = None, function: str | None = None, hub: str | None = None,
                      skill_id: int | None = None, level: Annotated[int | None, Query(ge=0, le=5)] = None):
    return aggregate(db, actor, group_by, dict(role_id=role_id, team=team, function=function,
                                             hub=hub, skill_id=skill_id, level=level))


@app.post("/notifications", status_code=201)
def create_notification(payload: ws.NotificationCreate, db: DbSession, actor: Actor):
    require(actor, "admin", "ld", "manager")
    employee_access(db, actor, payload.recipient_id)
    return notify(db, payload.recipient_id, payload.title, payload.message, "manual", actor_id=actor.id)


@app.get("/notifications")
def list_notifications(db: DbSession, actor: Actor, unread_only: bool = False,
                       limit: Annotated[int, Query(ge=1, le=200)] = 100):
    query = db.query(models.Notification).filter_by(recipient_id=actor.id)
    if unread_only:
        query = query.filter(models.Notification.read_at.is_(None))
    return query.order_by(models.Notification.id.desc()).limit(limit).all()


@app.get("/notifications/unread-count")
def notification_count(db: DbSession, actor: Actor):
    return {"unread_count": db.query(models.Notification).filter_by(recipient_id=actor.id, read_at=None).count()}


@app.patch("/notifications/{notification_id}/read")
def mark_read(notification_id: int, db: DbSession, actor: Actor):
    row = db.get(models.Notification, notification_id)
    if not row:
        raise HTTPException(404, "Notification not found")
    if row.recipient_id != actor.id:
        raise HTTPException(403, "Notification belongs to another user")
    changed = db.execute(update(models.Notification).where(models.Notification.id == row.id,
        models.Notification.read_at.is_(None)).values(read_at=models.utc_now()))
    if changed.rowcount:
        audit(db, actor.id, "notification.read", "notification", row.id, subject_id=actor.id)
    db.refresh(row)
    return row


@app.get("/audit-events")
def audit_events(db: DbSession, actor: Actor, action: str | None = None,
                 limit: Annotated[int, Query(ge=1, le=500)] = 100, after_id: int = 0):
    query = db.query(models.AuditEvent).filter(models.AuditEvent.id > after_id)
    if actor.role not in {"admin", "ld"}:
        subjects = [actor.id]
        if actor.role == "manager":
            subjects += [p.user_id for p in db.query(models.UserProfile).filter_by(manager_id=actor.id)]
        query = query.filter(or_(models.AuditEvent.subject_id.in_(subjects), models.AuditEvent.actor_id == actor.id))
    if action:
        query = query.filter(models.AuditEvent.action == action)
    return query.order_by(models.AuditEvent.id).limit(limit).all()


@app.post("/quests", status_code=201)
def create_quest(payload: ws.QuestCreate, db: DbSession, actor: Actor):
    require(actor, "admin", "ld")
    quest = models.Quest(**payload.model_dump())
    db.add(quest)
    db.flush()
    audit(db, actor.id, "quest.created", "quest", quest.id)
    return quest


@app.get("/quests")
def list_quests(db: DbSession, actor: Actor):
    require(actor, "admin", "ld", "employee")
    query = db.query(models.Quest).filter_by(active=True)
    if actor.role == "employee":
        details = profile(db, actor.id)
        query = query.filter(or_(models.Quest.business_function.is_(None),
                                models.Quest.business_function == (details.business_function if details else "")))
        return [workflows.quest_progress(db, actor, quest) for quest in query.order_by(models.Quest.id)]
    return query.order_by(models.Quest.id).all()


@app.post("/quests/{quest_id}/claim")
def claim_quest(quest_id: int, db: DbSession, actor: Actor):
    return workflows.claim_quest(db, actor, quest_id)


@app.get("/xp")
def xp_history(db: DbSession, actor: Actor):
    return {"xp_points": actor.xp_points,
            "awards": db.query(models.XpAward).filter_by(employee_id=actor.id).order_by(models.XpAward.id).all(),
            "affects_proficiency": False}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
