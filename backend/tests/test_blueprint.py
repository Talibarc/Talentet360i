import pytest
import models
from database import SessionLocal
from governance_service import record_question
from assessment_blueprint import select_workbook_questions
from fastapi import HTTPException
from test_phase2 import demo


def pool(demo, counts=(6,8,6)):
    group = demo.Finance
    with SessionLocal.begin() as db:
        for difficulty, count in zip(("Easy","Moderate","Difficult"),counts):
            for i in range(count):
                q=models.Question(skill_id=group["skill"],skill_level=3,question_text=f"Synthetic {difficulty} {i}",
                    options={k:k for k in "ABCD"},correct_answer="A",explanation="Synthetic",status="approved")
                db.add(q);db.flush()
                db.add(models.QuestionScope(question_id=q.id,role_skill_map_id=group["mapping"]))
                db.add(models.SourceRecord(workbook="fixture.xlsx",sheet="questions",source_key=str(q.id),entity_type="question",
                    entity_id=q.id,source_row=1,fingerprint="fixture",details={"difficulty":difficulty}))
                record_question(db,q,demo.admin,"approved")
        db.add(models.SourceRecord(workbook="fixture.xlsx",sheet="mapping",source_key="M",entity_type="mapping",
            entity_id=group["mapping"],source_row=1,fingerprint="fixture",details={"skill_key":"S","role_key":"R"}))


def test_blueprint_assignment_submission_and_skill_result(demo):
    pool(demo)
    g=demo.Finance
    assessment=demo.call("POST","/assessments",demo.admin,{"employee_id":g["employee"],"role_skill_map_id":g["mapping"],"question_count":20},201)
    detail=demo.call("GET",f"/assessments/{assessment['id']}",g["employee"])
    assert len(detail["questions"])==20
    assert all("correct_answer" not in q for q in detail["questions"])
    result=demo.call("POST",f"/assessments/{assessment['id']}/submit",g["employee"],{"answers":[{"question_id":q["question_id"],"selected_answer":"A"} for q in detail["questions"]]})
    assert result["score_percentage"]==100 and result["achieved_level"] is None
    detail=demo.call("GET",f"/assessments/{assessment['id']}",g["employee"])
    assert detail["skill_results"][0]["score_percentage"]==100
    demo.call("POST","/assessments",demo.admin,{"employee_id":g["employee"],"role_skill_map_id":g["mapping"],"question_count":20},409)


@pytest.mark.parametrize("counts", [(5,9,6),(6,7,7),(7,8,5)])
def test_blueprint_rejects_wrong_distribution(demo,counts):
    pool(demo,counts)
    with SessionLocal() as db:
        with pytest.raises(HTTPException):
            select_workbook_questions(db,demo.Finance["employee"],demo.Finance["role"])


def test_blueprint_missing_required_skill_blocks_assignment(demo):
    pool(demo)
    with SessionLocal.begin() as db:
        skill=models.Skill(name="Uncovered synthetic skill");db.add(skill);db.flush()
        db.add(models.RoleSkillMap(role_id=demo.Finance["role"],skill_id=skill.id,target_level=2,is_expected=True))
    with SessionLocal() as db:
        with pytest.raises(HTTPException):
            select_workbook_questions(db,demo.Finance["employee"],demo.Finance["role"])
