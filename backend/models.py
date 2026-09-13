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
    UniqueConstraint,
    event,
    DDL,
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


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id = Column(ForeignKey("users.id"), primary_key=True)
    job_role_id = Column(ForeignKey("roles.id"), nullable=True)
    manager_id = Column(ForeignKey("users.id"), nullable=True)
    business_function = Column(String(100), nullable=True)
    team = Column(String(100), nullable=True)
    hub = Column(String(100), nullable=True)


class QuestionScope(Base):
    __tablename__ = "question_scopes"
    question_id = Column(ForeignKey("questions.id"), primary_key=True)
    role_skill_map_id = Column(ForeignKey("role_skill_maps.id"), nullable=False)


class QuestionRevision(Base):
    __tablename__ = "question_revisions"
    id = Column(Integer, primary_key=True)
    question_id = Column(ForeignKey("questions.id"), nullable=False)
    revision = Column(Integer, nullable=False)
    action = Column(String(30), nullable=False)
    snapshot = Column(JSON, nullable=False)
    actor_id = Column(ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint("question_id", "revision"),)


class QuestionGrounding(Base):
    """Provider-independent provenance for source-grounded generated drafts."""
    __tablename__ = "question_groundings"
    question_id = Column(ForeignKey("questions.id"), primary_key=True)
    source_skill_id = Column(String(100), nullable=False, index=True)
    target_proficiency = Column(String(50), nullable=False)
    difficulty = Column(String(30), nullable=False)
    question_type = Column(String(50), nullable=False)
    source_ids = Column(JSON, nullable=False)
    chunk_references = Column(JSON, nullable=False)
    document_references = Column(JSON, nullable=False)
    ai_confidence = Column(String(30), nullable=False)
    provider_name = Column(String(30), nullable=False)
    provider_model = Column(String(100), nullable=False)
    synthetic_only = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class SourceRecord(Base):
    """Stable workbook identity and provenance; no source files are rewritten."""
    __tablename__ = "source_records"
    id = Column(Integer, primary_key=True)
    workbook = Column(String(100), nullable=False)
    sheet = Column(String(100), nullable=False)
    source_key = Column(String(250), nullable=False)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(Integer, nullable=True)
    source_row = Column(Integer, nullable=False)
    fingerprint = Column(String(64), nullable=False)
    details = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint("workbook", "sheet", "source_key"),)


class ScoringPolicy(Base):
    __tablename__ = "scoring_policies"
    id = Column(Integer, primary_key=True)
    role_skill_map_id = Column(ForeignKey("role_skill_maps.id"), nullable=False)
    settings = Column(JSON, nullable=False)
    source_reference = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class AssessmentSnapshot(Base):
    __tablename__ = "assessment_snapshots"
    assessment_id = Column(ForeignKey("assessments.id"), primary_key=True)
    target_level = Column(Integer, nullable=False)
    policy = Column(JSON, nullable=False)
    critical_failed = Column(Boolean, default=False, nullable=False)


class ItemSnapshot(Base):
    __tablename__ = "item_snapshots"
    item_id = Column(ForeignKey("assessment_items.id"), primary_key=True)
    revision_id = Column(ForeignKey("question_revisions.id"), nullable=True)
    content = Column(JSON, nullable=False)


class ResultReview(Base):
    __tablename__ = "result_reviews"
    assessment_id = Column(ForeignKey("assessments.id"), primary_key=True)
    status = Column(String(30), default="pending_review", nullable=False)
    revision = Column(Integer, default=1, nullable=False)


class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Integer, primary_key=True)
    employee_id = Column(ForeignKey("users.id"), nullable=False)
    role_skill_map_id = Column(ForeignKey("role_skill_maps.id"), nullable=False)
    assessment_id = Column(ForeignKey("assessments.id"), nullable=True)
    status = Column(String(30), default="submitted", nullable=False)
    revision = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class EvidenceRevision(Base):
    __tablename__ = "evidence_revisions"
    id = Column(Integer, primary_key=True)
    evidence_id = Column(ForeignKey("evidence.id"), nullable=False)
    revision = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    actor_id = Column(ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint("evidence_id", "revision"),)


class ManagerDecision(Base):
    __tablename__ = "manager_decisions"
    id = Column(Integer, primary_key=True)
    manager_id = Column(ForeignKey("users.id"), nullable=False)
    employee_id = Column(ForeignKey("users.id"), nullable=False)
    assessment_id = Column(ForeignKey("assessments.id"), nullable=True)
    evidence_id = Column(ForeignKey("evidence.id"), nullable=True)
    decision = Column(String(20), nullable=False)
    comment = Column(Text, nullable=False)
    reviewed_revision = Column(Integer, nullable=False)
    confirmed_level = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class OfficialLevel(Base):
    __tablename__ = "official_levels"
    id = Column(Integer, primary_key=True)
    employee_id = Column(ForeignKey("users.id"), nullable=False)
    role_skill_map_id = Column(ForeignKey("role_skill_maps.id"), nullable=False)
    assessment_id = Column(ForeignKey("assessments.id"), nullable=False)
    decision_id = Column(ForeignKey("manager_decisions.id"), nullable=False)
    confirmed_level = Column(Integer, nullable=False)
    confirmed_at = Column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint("employee_id", "role_skill_map_id"),)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    recipient_id = Column(ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    event_type = Column(String(60), nullable=False)
    entity_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    read_at = Column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True)
    actor_id = Column(ForeignKey("users.id"), nullable=True)
    subject_id = Column(ForeignKey("users.id"), nullable=True)
    action = Column(String(80), nullable=False)
    entity_type = Column(String(60), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Quest(Base):
    __tablename__ = "quests"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    event_type = Column(String(40), nullable=False)
    required_count = Column(Integer, nullable=False)
    xp_reward = Column(Integer, nullable=False)
    business_function = Column(String(100), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class XpAward(Base):
    __tablename__ = "xp_awards"
    id = Column(Integer, primary_key=True)
    employee_id = Column(ForeignKey("users.id"), nullable=False)
    source_key = Column(String(100), nullable=False)
    points = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint("employee_id", "source_key"),)


# Enforced by SQLite as well as by the absence of update/delete APIs.
for immutable in (AuditEvent, QuestionRevision, EvidenceRevision, ManagerDecision, XpAward, ScoringPolicy):
    for operation in ("UPDATE", "DELETE"):
        event.listen(immutable.__table__, "after_create", DDL(
            f"CREATE TRIGGER IF NOT EXISTS {immutable.__tablename__}_no_{operation.lower()} "
            f"BEFORE {operation} ON {immutable.__tablename__} BEGIN "
            "SELECT RAISE(ABORT, 'append-only history'); END"
        ).execute_if(dialect="sqlite"))
