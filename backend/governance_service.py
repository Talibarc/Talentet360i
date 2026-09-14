from fastapi import HTTPException
from sqlalchemy import update
import models
from auth import mapping_access, require
from event_service import audit, notify


def latest_revision(db, question_id):
    return db.query(models.QuestionRevision).filter_by(question_id=question_id).order_by(
        models.QuestionRevision.revision.desc()).first()


def record_question(db, question, actor_id, action, *, is_critical=None):
    previous = latest_revision(db, question.id)
    content = {key: getattr(question, key) for key in (
        "question_text", "options", "correct_answer", "explanation", "rag_source", "status",
        "skill_id", "skill_level", "review_comment")}
    content["is_critical"] = (is_critical if is_critical is not None else
                              bool(previous and previous.snapshot.get("is_critical")))
    revision = models.QuestionRevision(question_id=question.id,
        revision=previous.revision + 1 if previous else 1, snapshot=content,
        actor_id=actor_id, action=action)
    db.add(revision)
    db.flush()
    audit(db, actor_id, f"question.{action}", "question", question.id,
          details={"revision": revision.revision, "revision_id": revision.id})
    return revision


def scoped_question(db, actor, question_id):
    require(actor, "admin", "ld", "reviewer")
    question = db.get(models.Question, question_id)
    if question is None:
        raise HTTPException(404, "Question not found")
    scope = db.get(models.QuestionScope, question_id)
    if scope:
        mapping_access(db, actor, scope.role_skill_map_id)
    elif actor.role not in {"admin", "ld"}:
        raise HTTPException(409, "Legacy question requires an explicit role-skill scope")
    return question


def review(db, actor, question_id, payload):
    question = scoped_question(db, actor, question_id)
    source = db.query(models.SourceRecord).filter_by(entity_type="question", entity_id=question_id).first()
    revision = latest_revision(db, question_id)
    if (payload.status == "approved" and source and source.details.get("source_status") == "Needs Rewrite"
            and revision and revision.action == "source_imported"):
        raise HTTPException(409, "Workbook marks this question Needs Rewrite; edit a new revision before approval")
    # Compare-and-set avoids duplicate competing reviews in a single transition.
    changed = db.execute(update(models.Question).where(models.Question.id == question_id,
        models.Question.status == "pending_review").values(status=payload.status,
        review_comment=payload.review_comment, reviewed_at=models.utc_now(), reviewed_by_id=actor.id))
    if changed.rowcount != 1:
        raise HTTPException(409, "Question already reviewed; edit a new revision first")
    db.refresh(question)
    record_question(db, question, actor.id, payload.status)
    if question.created_by_id:
        notify(db, question.created_by_id, "Question reviewed", f"Question {question.id}: {payload.status}",
               "question.reviewed", question.id, actor.id)
    return question


def edit(db, actor, question_id, payload):
    question = scoped_question(db, actor, question_id)
    previous = latest_revision(db, question_id)
    if not previous or previous.revision != payload.expected_revision:
        raise HTTPException(409, "Question revision changed; reload before editing")
    if payload.is_critical:
        scope = db.get(models.QuestionScope, question_id)
        policy = db.query(models.ScoringPolicy).filter_by(role_skill_map_id=scope.role_skill_map_id).order_by(
            models.ScoringPolicy.id.desc()).first() if scope else None
        if not policy or policy.settings.get("critical_fail_level") is None:
            raise HTTPException(409, "Configure a source-referenced critical-fail policy first")
    for field in ("question_text", "options", "correct_answer", "explanation"):
        setattr(question, field, getattr(payload, field))
    # Editing may not claim new source provenance; original source is retained.
    question.status = "pending_review"
    question.review_comment = payload.comment
    question.reviewed_at = None
    question.reviewed_by_id = None
    db.flush()
    record_question(db, question, actor.id, "edited", is_critical=payload.is_critical)
    return question
