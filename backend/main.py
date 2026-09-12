from typing import Annotated
from assessment_service import (
    create_assessment,
    get_assessment,
    submit_assessment,
)
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from question_service import generate_question_drafts
from excel_loader import validate_workbooks
from rag_service import retrieve_finance_context
from tni_service import get_employee_tni

import models
import schemas
from database import Base, engine, get_db

Base.metadata.create_all(bind=engine)
DbSession = Annotated[Session, Depends(get_db)]
app = FastAPI(
    title="Talent360i API",
    version="1.1.0",
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
 
@app.get("/")
def home():
    return {"message": "Talent360i backend is running"}
 
 
@app.get("/health")
def health_check():
    return {"status": "healthy"}
 
 
@app.post(
    "/roles",
    response_model=schemas.RoleResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Roles"],
)
def create_role(
    payload: schemas.RoleCreate,
    db: DbSession,
):
    role = models.Role(**payload.model_dump())
    db.add(role)
 
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role code already exists",
        ) from error
 
    db.refresh(role)
    return role
 
 
@app.get(
    "/roles",
    response_model=list[schemas.RoleResponse],
    tags=["Roles"],
)
def list_roles(db: DbSession):
    return db.query(models.Role).order_by(models.Role.id).all()
 
@app.get("/data/validate", tags=["Data Validation"])
def validate_source_data():
    return validate_workbooks()

@app.get("/rag/context", tags=["RAG"])
def get_rag_context(role_name: str, skill_name: str):
    return retrieve_finance_context(role_name, skill_name)
 

@app.post(
    "/skills",
    response_model=schemas.SkillResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Skills"],
)
def create_skill(
    payload: schemas.SkillCreate,
    db: DbSession,
):
    skill = models.Skill(**payload.model_dump())
    db.add(skill)
 
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Skill name already exists",
        ) from error
 
    db.refresh(skill)
    return skill
 
 
@app.get(
    "/skills",
    response_model=list[schemas.SkillResponse],
    tags=["Skills"],
)
def list_skills(db: DbSession):
    return db.query(models.Skill).order_by(models.Skill.id).all()
 
 
@app.post(
    "/role-skill-maps",
    response_model=schemas.RoleSkillMapResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Role Skill Mapping"],
)
def create_role_skill_map(
    payload: schemas.RoleSkillMapCreate,
    db: DbSession,
):
    role = db.get(models.Role, payload.role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )
 
    skill = db.get(models.Skill, payload.skill_id)
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )
 
    existing_mapping = (
        db.query(models.RoleSkillMap)
        .filter(
            models.RoleSkillMap.role_id == payload.role_id,
            models.RoleSkillMap.skill_id == payload.skill_id,
        )
        .first()
    )
 
    if existing_mapping is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This role and skill mapping already exists",
        )
 
    mapping = models.RoleSkillMap(**payload.model_dump())
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping
 
 
@app.get(
    "/role-skill-maps",
    response_model=list[schemas.RoleSkillMapResponse],
    tags=["Role Skill Mapping"],
)
def list_role_skill_maps(db: DbSession):
    return db.query(models.RoleSkillMap).order_by(models.RoleSkillMap.id).all()
@app.post(
    "/questions/generate",
    response_model=list[schemas.QuestionResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["Question Bank"],
)
def generate_questions(
    payload: schemas.QuestionGenerateRequest,
    db: DbSession,
):
    mapping = db.get(models.RoleSkillMap, payload.role_skill_map_id)
 
    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role-skill mapping not found",
        )
 
    if not mapping.is_expected or mapping.target_level is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Questions cannot be generated for a non-expected skill",
        )
 
    role = db.get(models.Role, mapping.role_id)
    skill = db.get(models.Skill, mapping.skill_id)
 
    if role is None or skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapped role or skill not found",
        )
 
    target_label = mapping.target_label or f"Level {mapping.target_level}"
 
    source_context = (
        f"Role: {role.role_name}. "
        f"Business function: {role.business_function}. "
        f"Tower: {role.tower or 'Not specified'}. "
        f"Skill: {skill.name}. "
        f"Skill definition: {skill.description or 'Not provided'}. "
        f"Required proficiency: Level {mapping.target_level} - {target_label}."
    )
 
    drafts = generate_question_drafts(
        role_name=role.role_name,
        skill_name=skill.name,
        target_level=mapping.target_level,
        target_label=target_label,
        source_context=source_context,
        question_count=payload.question_count,
    )
 
    questions = []
 
    for draft in drafts:
        question = models.Question(
            skill_id=skill.id,
            skill_level=mapping.target_level,
            question_text=draft.question_text,
            options=draft.options,
            correct_answer=draft.correct_answer,
            explanation=draft.explanation,
            rag_source="Finance Excel RAG",
            status="pending_review",
        )
        db.add(question)
        questions.append(question)
 
    db.commit()
 
    for question in questions:
        db.refresh(question)
 
    return questions

@app.get(
    "/questions",
    response_model=list[schemas.QuestionResponse],
    tags=["Question Bank"],
)
def list_questions(db: DbSession):
    return (
        db.query(models.Question)
        .order_by(models.Question.id.desc())
        .all()
    )

@app.patch(
    "/questions/{question_id}/review",
    response_model=schemas.QuestionResponse,
    tags=["Reviewer Approval"],
)
def review_question(
    question_id: int,
    payload: schemas.QuestionReviewRequest,
    db: DbSession,
):
    question = db.get(models.Question, question_id)
 
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )
 
    question.status = payload.status
    question.review_comment = payload.review_comment
    question.reviewed_at = models.utc_now()
 
    db.commit()
    db.refresh(question)
 
    return question 

@app.post(
    "/users",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
)
def create_user(
    payload: schemas.UserCreate,
    db: DbSession,
):
    existing_user = (
        db.query(models.User)
        .filter(
            (models.User.employee_id == payload.employee_id)
            | (models.User.email == payload.email)
        )
        .first()
    )
 
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee ID or email already exists",
        )
 
    user = models.User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
 
 
@app.get(
    "/users",
    response_model=list[schemas.UserResponse],
    tags=["Users"],
)
def list_users(db: DbSession):
    return db.query(models.User).order_by(models.User.id).all()


 

@app.post(
    "/assessments",
    response_model=schemas.AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Employee Assessment"],
)
def assign_assessment(
    payload: schemas.AssessmentCreate,
    db: DbSession,
):
    return create_assessment(db, payload)
 
 
@app.get(
    "/assessments/{assessment_id}",
    tags=["Employee Assessment"],
)
def read_assessment(
    assessment_id: int,
    db: DbSession,
):
    return get_assessment(db, assessment_id)
 
 
@app.post(
    "/assessments/{assessment_id}/submit",
    response_model=schemas.AssessmentResult,
    tags=["Employee Assessment"],
)
def complete_assessment(
    assessment_id: int,
    payload: schemas.AssessmentSubmitRequest,
    db: DbSession,
):
    return submit_assessment(db, assessment_id, payload)

@app.get(
    "/users/{employee_id}/tni",
    tags=["Skill Profile & TNI"],
)
def read_employee_tni(
    employee_id: int,
    db: DbSession,
):
    return get_employee_tni(db, employee_id) 


if __name__ == "__main__":
    import uvicorn
 
    uvicorn.run(app, host="127.0.0.1", port=8000) 