from fastapi import HTTPException, status
from sqlalchemy.orm import Session
 
import models
import schemas


def calculate_achieved_level(score_percentage: int, target_level: int) -> int:
    """Existing prototype bands, not yet certified against company scoring policy."""
    if score_percentage >= 95:
        return target_level
    if score_percentage > 80:
        return min(target_level, max(1, target_level - 1))
    return max(0, target_level - 2)
 
 
def create_assessment(
    db: Session,
    payload: schemas.AssessmentCreate,
):
    employee = db.get(models.User, payload.employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )
 
    mapping = db.get(models.RoleSkillMap, payload.role_skill_map_id)
    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role-skill mapping not found",
        )
 
    if not mapping.is_expected or mapping.target_level is None:
        raise HTTPException(status_code=400, detail="Skill is Not Expected for this mapping")

    questions = (
        db.query(models.Question)
        .filter(
            models.Question.skill_id == mapping.skill_id,
            models.Question.status == "approved",
            models.Question.skill_level == mapping.target_level,
        )
        .order_by(models.Question.id.desc())
        .limit(payload.question_count)
        .all()
    )
 
    if len(questions) < payload.question_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Only {len(questions)} approved questions are available. "
                f"Requested {payload.question_count}."
            ),
        )
 
    assessment = models.Assessment(
        employee_id=payload.employee_id,
        role_skill_map_id=payload.role_skill_map_id,
        status="assigned",
        total_questions=len(questions),
    )
    db.add(assessment)
    db.flush()
 
    for question in questions:
        db.add(
            models.AssessmentItem(
                assessment_id=assessment.id,
                question_id=question.id,
            )
        )
 
    db.commit()
    db.refresh(assessment)
    return assessment
 
 
def get_assessment(db: Session, assessment_id: int):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )
 
    answer_rows = (
        db.query(models.AssessmentItem)
        .filter(models.AssessmentItem.assessment_id == assessment_id)
        .all()
    )
 
    questions = []
    for answer_row in answer_rows:
        question = db.get(models.Question, answer_row.question_id)
        questions.append(
            {
                "question_id": question.id,
                "skill_id": question.skill_id,
                "skill_level": question.skill_level,
                "question_text": question.question_text,
                "options": question.options,
            }
        )
 
    return {
        "assessment": assessment,
        "questions": questions,
    }
 
 
def submit_assessment(
    db: Session,
    assessment_id: int,
    payload: schemas.AssessmentSubmitRequest,
):
    assessment = db.get(models.Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
           
            detail="Assessment not found",
        )
 
    if assessment.status == "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment has already been submitted",
        )

    mapping = db.get(models.RoleSkillMap, assessment.role_skill_map_id)
    if mapping is None or not mapping.is_expected or mapping.target_level is None:
        raise HTTPException(status_code=400, detail="Skill is Not Expected for this mapping")
 
    answer_rows = (
        db.query(models.AssessmentItem)
        .filter(models.AssessmentItem.assessment_id == assessment_id)
        .all()
    )
 
    submitted_answers = {
        answer.question_id: answer.selected_answer.upper()
        for answer in payload.answers
    }
 
    expected_question_ids = {row.question_id for row in answer_rows}
 
    if set(submitted_answers) != expected_question_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submit one answer for every assigned question",
        )
 
    correct_answers = 0
 
    for answer_row in answer_rows:
        question = db.get(models.Question, answer_row.question_id)
        selected = submitted_answers[answer_row.question_id]
 
        answer_row.selected_answer = selected
        answer_row.is_correct = selected == question.correct_answer.upper()
        answer_row.answered_at = models.utc_now()
 
        if answer_row.is_correct:
            correct_answers += 1
 
    score_percentage = round(
        correct_answers * 100 / assessment.total_questions
    )
    xp_awarded = correct_answers * 10
 
    target_level = mapping.target_level
 
    achieved_level = calculate_achieved_level(score_percentage, target_level)
 
    assessment.correct_answers = correct_answers
    assessment.score_percentage = score_percentage
    assessment.achieved_level = achieved_level
    assessment.xp_awarded = xp_awarded
    assessment.status = "submitted"
    assessment.submitted_at = models.utc_now()
    employee = db.get(models.User, assessment.employee_id)
    employee.xp_points += xp_awarded
 
    db.commit()
 
    return {
        "assessment_id": assessment.id,
        "status": assessment.status,
        "total_questions": assessment.total_questions,
        "correct_answers": assessment.correct_answers,
        "score_percentage": assessment.score_percentage,
        "achieved_level": assessment.achieved_level,
        "xp_awarded": assessment.xp_awarded,
    }

