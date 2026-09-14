import random
import config
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session
import models
import schemas
from event_service import audit, notify, award_xp
from governance_service import latest_revision


def calculate_achieved_level(score_percentage: int, target_level: int) -> int:
    """Inherited prototype bands, explicitly provisional until source policy is supplied."""
    if score_percentage >= 95:
        return target_level
    if score_percentage > 80:
        return min(target_level, max(1, target_level - 1))
    return max(0, target_level - 2)


def create_assessment(db: Session, payload: schemas.AssessmentCreate, actor_id=None):
    employee = db.get(models.User, payload.employee_id)
    mapping = db.get(models.RoleSkillMap, payload.role_skill_map_id)
    if employee is None:
        raise HTTPException(404, "Employee not found")
    if mapping is None:
        raise HTTPException(404, "Role-skill mapping not found")
    if not mapping.is_expected or mapping.target_level is None:
        raise HTTPException(400, "Skill is Not Expected for this mapping")
    profile = db.get(models.UserProfile, employee.id)
    if profile and profile.job_role_id and profile.job_role_id != mapping.role_id:
        raise HTTPException(400, "Assessment mapping does not match employee job role")
    role = db.get(models.Role, mapping.role_id)
    if profile and profile.business_function and profile.business_function != role.business_function:
        raise HTTPException(400, "Assessment mapping does not match employee function")
    source_mapping = db.query(models.SourceRecord).filter_by(entity_type="mapping", entity_id=mapping.id).first()
    if source_mapping and payload.question_count != 20:
        raise HTTPException(409, "Workbook assessment starting size is 20 questions")
    questions = db.query(models.Question).join(models.QuestionScope).filter(
        models.QuestionScope.role_skill_map_id == mapping.id,
        models.Question.skill_id == mapping.skill_id, models.Question.status == "approved",
        models.Question.skill_level == mapping.target_level).all()
    if source_mapping:
        from assessment_blueprint import select_workbook_questions
        questions = select_workbook_questions(db, employee.id, mapping.role_id)
    if len(questions) < payload.question_count:
        if source_mapping:
            raise HTTPException(409, f"Workbook assessment requires 20 approved questions with 6/8/6 difficulty coverage; only {len(questions)} exactly mapped questions are available")
        raise HTTPException(400, f"Only {len(questions)} approved questions are available. Requested {payload.question_count}.")
    questions = random.SystemRandom().sample(questions, payload.question_count)
    assessment = models.Assessment(employee_id=employee.id, role_skill_map_id=mapping.id,
                                   status="assigned", total_questions=len(questions))
    db.add(assessment)
    db.flush()
    policy = db.query(models.ScoringPolicy).filter_by(role_skill_map_id=mapping.id).order_by(
        models.ScoringPolicy.id.desc()).first()
    settings = ({**policy.settings, "source_reference": policy.source_reference, "policy_id": policy.id}
                if policy else {"full_score_min": 95, "middle_score_min": 81, "critical_fail_level": None,
                                "source_reference": "Inherited prototype bands; not company-validated", "policy_id": None})
    if db.query(models.SourceRecord).filter_by(entity_type="mapping", entity_id=mapping.id).first():
        settings = {"pending_validation": True, "source_reference": "Workbook supplies no validated score-to-level policy"}
    db.add(models.AssessmentSnapshot(assessment_id=assessment.id, target_level=mapping.target_level, policy=settings))
    for question in questions:
        revision = latest_revision(db, question.id)
        if revision is None or revision.snapshot["status"] != "approved":
            raise HTTPException(409, "Approved question has no reviewed version")
        item = models.AssessmentItem(assessment_id=assessment.id, question_id=question.id)
        db.add(item)
        db.flush()
        scope = db.get(models.QuestionScope, question.id)
        db.add(models.ItemSnapshot(item_id=item.id, revision_id=revision.id,
            content={**revision.snapshot, "role_skill_map_id": scope.role_skill_map_id}))
    audit(db, actor_id, "assessment.assigned", "assessment", assessment.id, subject_id=employee.id,
          details={"question_count": len(questions), "mapping_id": mapping.id})
    notify(db, employee.id, "Assessment assigned", "An assessment is ready to complete.",
           "assessment.assigned", assessment.id, actor_id)
    db.flush()
    return assessment


def get_assessment(db: Session, assessment_id: int):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(404, "Assessment not found")
    questions = []
    for row in db.query(models.AssessmentItem).filter_by(assessment_id=assessment_id).order_by(models.AssessmentItem.id):
        snapshot = db.get(models.ItemSnapshot, row.id)
        if snapshot:
            content = snapshot.content
        else:
            # Legacy reads stay possible; legacy submission cannot silently change the answer key.
            question = db.get(models.Question, row.question_id)
            content = {key: getattr(question, key) for key in ("skill_id", "skill_level", "question_text", "options")}
        questions.append({"question_id": row.question_id,
                          **{key: content[key] for key in ("skill_id", "skill_level", "question_text", "options")}})
    review = db.get(models.ResultReview, assessment_id)
    snapshot = db.get(models.AssessmentSnapshot, assessment_id)
    skill_results = []
    for result in db.query(models.AssessmentSkillResult).filter_by(assessment_id=assessment_id):
        mapping = db.get(models.RoleSkillMap, result.role_skill_map_id)
        skill = db.get(models.Skill, mapping.skill_id)
        source = db.query(models.SourceRecord).filter_by(entity_type="skill", entity_id=skill.id).first()
        skill_results.append({"role_skill_map_id": mapping.id, "skill_name": skill.name,
            "source_skill_id": source.source_key if source else None,
            "score_percentage": result.score_percentage, "achieved_level": result.achieved_level,
            "total_questions": result.total_questions, "correct_answers": result.correct_answers})
    return {"assessment": assessment, "questions": questions,
            "skill_results": skill_results,
            "review_status": review.status if review else "not_submitted",
            "review_revision": review.revision if review else None,
            "critical_failed": snapshot.critical_failed if snapshot else False}


def submit_assessment(db: Session, assessment_id: int, payload: schemas.AssessmentSubmitRequest, actor_id=None):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(404, "Assessment not found")
    if assessment.status == "submitted":
        raise HTTPException(400, "Assessment has already been submitted")
    mapping = db.get(models.RoleSkillMap, assessment.role_skill_map_id)
    if mapping is None or not mapping.is_expected or mapping.target_level is None:
        raise HTTPException(400, "Skill is Not Expected for this mapping")
    snapshot = db.get(models.AssessmentSnapshot, assessment_id)
    if snapshot is None:
        raise HTTPException(409, "Legacy assessment lacks frozen questions/policy; assign a new assessment")
    rows = db.query(models.AssessmentItem).filter_by(assessment_id=assessment_id).all()
    answers = {answer.question_id: answer.selected_answer for answer in payload.answers}
    if set(answers) != {row.question_id for row in rows}:
        raise HTTPException(400, "Submit one answer for every assigned question")
    if db.execute(update(models.Assessment).where(models.Assessment.id == assessment_id,
        models.Assessment.status.in_(["assigned", "in_progress"])).values(status="submitted")).rowcount != 1:
        raise HTTPException(409, "Assessment has already been submitted")
    correct, critical_failed, critical_incorrect = 0, False, 0
    for row in rows:
        item = db.get(models.ItemSnapshot, row.id)
        if item is None:
            raise HTTPException(409, "Missing question snapshot")
        row.selected_answer = answers[row.question_id]
        row.is_correct = row.selected_answer == item.content["correct_answer"]
        row.answered_at = models.utc_now()
        correct += int(row.is_correct)
        critical_incorrect += int(bool(item.content.get("is_critical") and not row.is_correct))
        critical_failed |= bool(item.content.get("is_critical") and not row.is_correct)
    score = round(correct * 100 / assessment.total_questions)
    target = snapshot.target_level
    policy = snapshot.policy
    if policy.get("pending_validation"):
        level = None
    elif score >= policy["full_score_min"]:
        level = target
    elif score >= policy["middle_score_min"]:
        level = min(target, max(1, target - 1))
    else:
        level = max(0, target - 2)
    workbook_backed = bool(db.query(models.SourceRecord).filter_by(entity_type="mapping", entity_id=assessment.role_skill_map_id).first())
    if level is not None and critical_failed and not workbook_backed and policy.get("critical_fail_level") is not None:
        level = min(level, policy["critical_fail_level"])
    snapshot.critical_failed = critical_failed and not workbook_backed
    assessment.correct_answers, assessment.score_percentage = correct, score
    assessment.achieved_level, assessment.xp_awarded = level, correct * 10
    assessment.submitted_at = models.utc_now()
    if workbook_backed:
        from collections import defaultdict
        scores = defaultdict(lambda: [0, 0])
        for row in rows:
            item = db.get(models.ItemSnapshot, row.id)
            mapped = item.content.get("role_skill_map_id", assessment.role_skill_map_id)
            scores[mapped][0] += 1
            scores[mapped][1] += int(row.is_correct)
        for mapped, (total, right) in scores.items():
            db.add(models.AssessmentSkillResult(assessment_id=assessment.id,
                role_skill_map_id=mapped, total_questions=total, correct_answers=right,
                score_percentage=round(right*100/total), achieved_level=None))
    db.add(models.ResultReview(assessment_id=assessment.id, status="pending_review"))
    award_xp(db, assessment.employee_id, correct * 10, f"assessment:{assessment.id}", actor_id)
    audit(db, actor_id, "assessment.submitted", "assessment", assessment.id, subject_id=assessment.employee_id,
          details={"score": score, "calculated_level": level, "critical_failed": critical_failed and not workbook_backed,
                   "policy": policy, "critical_incorrect_count": critical_incorrect,
                   "critical_review_flag": critical_incorrect > 0})
    profile = db.get(models.UserProfile, assessment.employee_id)
    if profile and profile.manager_id:
        notify(db, profile.manager_id, "Result awaiting review", "A direct report submitted an assessment.",
               "assessment.submitted", assessment.id, actor_id)
    db.flush()
    return {"assessment_id": assessment.id, "status": "submitted", "total_questions": assessment.total_questions,
            "correct_answers": correct, "score_percentage": score, "achieved_level": level, "xp_awarded": correct * 10}


def assessment_visible(db, assessment):
    if config.LLM_PROVIDER == "mock":
        return True
    source = db.query(models.SourceRecord).filter_by(entity_type="mapping", entity_id=assessment.role_skill_map_id).first()
    if not source or not source.fingerprint:
        return False
    items = db.query(models.ItemSnapshot).join(models.AssessmentItem).filter(models.AssessmentItem.assessment_id == assessment.id).all()
    return not any("synthetic" in str(item.content.get("rag_source", "")).lower() for item in items)
