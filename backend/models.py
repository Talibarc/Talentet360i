from datetime import datetime, timezone

from database import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)


def utc_now():
    return datetime.now(timezone.utc)
 
 
class User(Base):
    __tablename__ = "users"
 
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    role = Column(String(30), nullable=False)
    department = Column(String(100), nullable=True)
    xp_points = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
 
 
class Skill(Base):
    __tablename__ = "skills"
 
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    max_level = Column(Integer, default=3, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class Role(Base):
    __tablename__ = "roles"
 
    id = Column(Integer, primary_key=True, index=True)
    role_code = Column(String(50), unique=True, nullable=False, index=True)
    role_name = Column(String(150), nullable=False)
    business_function = Column(String(100), nullable=False, index=True)
    tower = Column(String(50), nullable=True)
    role_grade = Column(String(30), nullable=True)
    level_framework = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
 
 
class RoleSkillMap(Base):
    __tablename__ = "role_skill_maps"
 
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(ForeignKey("roles.id"), nullable=False, index=True)
    skill_id = Column(ForeignKey("skills.id"), nullable=False, index=True)
 
    target_level = Column(Integer, nullable=True)
    target_label = Column(String(30), nullable=True)
    is_expected = Column(Boolean, default=True, nullable=False)
 
    created_at = Column(DateTime(timezone=True), default=utc_now)
  
 
class Question(Base):
    __tablename__ = "questions"
 
    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(ForeignKey("skills.id"), nullable=False, index=True)
    skill_level = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)
    correct_answer = Column(String(10), nullable=False)
    explanation = Column(Text, nullable=True)
    rag_source = Column(Text, nullable=True)
 
    status = Column(String(30), default="pending_review", nullable=False)
    created_by_id = Column(ForeignKey("users.id"), nullable=True)
    reviewed_by_id = Column(ForeignKey("users.id"), nullable=True)
    review_comment = Column(Text, nullable=True)
 
    created_at = Column(DateTime(timezone=True), default=utc_now)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

class Assessment(Base):
    __tablename__ = "assessments"
 
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(ForeignKey("users.id"), nullable=False, index=True)
    role_skill_map_id = Column(
        ForeignKey("role_skill_maps.id"),
        nullable=False,
        index=True,
    )
    status = Column(String(30), default="assigned", nullable=False)
    total_questions = Column(Integer, default=0, nullable=False)
    correct_answers = Column(Integer, default=0, nullable=False)
    score_percentage = Column(Integer, nullable=True)
    achieved_level = Column(Integer, nullable=True)
    xp_awarded = Column(Integer, default=0, nullable=False)
    assigned_at = Column(DateTime(timezone=True), default=utc_now)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
   
 
 
class AssessmentItem(Base):
    __tablename__ = "assessment_items"
 
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(
        ForeignKey("assessments.id"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        ForeignKey("questions.id"),
        nullable=False,
        index=True,
    )
    selected_answer = Column(String(10), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=True)
