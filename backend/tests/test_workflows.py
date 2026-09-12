import pytest

from assessment_service import calculate_achieved_level
from database import SessionLocal
import models
from schemas import EmployeeTniResponse, GeneratedQuestion


def generate(client, seeded, count=5):
    response = client.post("/questions/generate", json={
        "role_skill_map_id": seeded["mapping"]["id"], "question_count": count})
    assert response.status_code == 201, response.text
    return response.json()


def assign(client, seeded, count=5):
    response = client.post("/assessments", json={
        "employee_id": seeded["user"]["id"], "role_skill_map_id": seeded["mapping"]["id"],
        "question_count": count})
    assert response.status_code == 201, response.text
    return response.json()


def approve(client, questions):
    for question in questions:
        assert client.patch(f"/questions/{question['id']}/review", json={"status": "approved"}).status_code == 200


def submit(client, assessment, questions, correct_count):
    answers = [{"question_id": q["id"], "selected_answer": q["correct_answer"] if i < correct_count
                else next(k for k in "ABCD" if k != q["correct_answer"])} for i, q in enumerate(questions)]
    return client.post(f"/assessments/{assessment['id']}/submit", json={"answers": answers})


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_mock_questions_deterministic_without_rag(client, seeded, monkeypatch):
    def forbidden(*args):
        raise AssertionError("Mock must not retrieve company source")
    monkeypatch.setattr("question_service.build_finance_rag_context", forbidden)
    first, second = generate(client, seeded), generate(client, seeded)
    assert len(first) == 5
    for a, b in zip(first, second):
        assert GeneratedQuestion.model_validate(a) == GeneratedQuestion.model_validate(b)
        assert a["status"] == "pending_review"
        assert set(a["options"]) == set("ABCD")
        assert "Synthetic" in a["rag_source"]


def test_review_and_approved_assessment(client, seeded):
    questions = generate(client, seeded, 3)
    assert client.patch(f"/questions/{questions[0]['id']}/review", json={"status": "approved", "review_comment": "Fixture accepted"}).status_code == 200
    assert client.patch(f"/questions/{questions[1]['id']}/review", json={"status": "rejected", "review_comment": "Fixture rejected"}).status_code == 200
    assert client.patch(f"/questions/{questions[2]['id']}/review", json={"status": "invalid"}).status_code == 422
    assert client.patch("/questions/9999/review", json={"status": "approved"}).status_code == 404
    response = client.post("/assessments", json={"employee_id": seeded["user"]["id"],
        "role_skill_map_id": seeded["mapping"]["id"], "question_count": 2})
    assert response.status_code == 400
    assessment = assign(client, seeded, 1)
    payload = client.get(f"/assessments/{assessment['id']}").json()
    assert [q["question_id"] for q in payload["questions"]] == [questions[0]["id"]]
    assert "correct_answer" not in payload["questions"][0]
    with SessionLocal() as db:
        rejected = db.get(models.Question, questions[1]["id"])
        assert rejected.status == "rejected" and rejected.review_comment == "Fixture rejected"
        assert rejected.reviewed_at is not None


@pytest.mark.parametrize("correct, score, achieved", [(0, 0, 1), (4, 80, 1), (5, 100, 3)])
def test_scoring_persistence_and_repeatability(client, seeded, correct, score, achieved):
    questions = generate(client, seeded)
    approve(client, questions)
    for _ in range(2):
        assessment = assign(client, seeded)
        response = submit(client, assessment, questions, correct)
        assert response.status_code == 200, response.text
        result = response.json()
        assert (result["score_percentage"], result["achieved_level"], result["xp_awarded"]) == (score, achieved, correct * 10)
        assert submit(client, assessment, questions, correct).status_code == 400
        with SessionLocal() as db:
            rows = db.query(models.AssessmentItem).filter_by(assessment_id=assessment["id"]).all()
            assert len(rows) == 5
            assert sum(r.is_correct for r in rows) == correct
            assert all(r.answered_at is not None and r.selected_answer in "ABCD" for r in rows)
    assert client.get("/users").json()[0]["xp_points"] == 2 * correct * 10


@pytest.mark.parametrize("score,target,level", [(80,3,1), (81,3,2), (94,3,2), (95,3,3),
                                               (100,3,3), (81,0,0), (0,0,0), (95,0,0), (81,1,1)])
def test_achieved_level_boundaries(score, target, level):
    assert calculate_achieved_level(score, target) == level


def test_duplicate_and_incomplete_answers_rejected(client, seeded):
    questions = generate(client, seeded, 2)
    approve(client, questions)
    assessment = assign(client, seeded, 2)
    answer = dict(question_id=questions[0]["id"], selected_answer="A")
    assert client.post(f"/assessments/{assessment['id']}/submit", json={"answers": [answer, answer]}).status_code == 422
    assert client.post(f"/assessments/{assessment['id']}/submit", json={"answers": [answer]}).status_code == 400


@pytest.mark.parametrize("target,expected", [(None, True), (3, False)])
def test_not_expected_cannot_generate_or_assign(client, seeded, target, expected):
    with SessionLocal() as db:
        mapping = db.get(models.RoleSkillMap, seeded["mapping"]["id"])
        mapping.target_level, mapping.is_expected = target, expected
        db.commit()
    assert client.post("/questions/generate", json={"role_skill_map_id": seeded["mapping"]["id"]}).status_code == 400
    assert client.post("/assessments", json={"employee_id": seeded["user"]["id"],
        "role_skill_map_id": seeded["mapping"]["id"], "question_count": 1}).status_code == 400


def test_wrong_level_questions_excluded(client, seeded):
    questions = generate(client, seeded, 1)
    approve(client, questions)
    with SessionLocal() as db:
        db.get(models.Question, questions[0]["id"]).skill_level = 1
        db.commit()
    assert client.post("/assessments", json={"employee_id": seeded["user"]["id"],
        "role_skill_map_id": seeded["mapping"]["id"], "question_count": 1}).status_code == 400


def test_detailed_tni_supported_learning(client, seeded, learning_workbooks):
    questions = generate(client, seeded)
    approve(client, questions)
    assert submit(client, assign(client, seeded), questions, 4).status_code == 200
    url = f"/users/{seeded['user']['id']}/tni"
    response = client.get(url)
    assert response.status_code == 200, response.text
    result = response.json()
    EmployeeTniResponse.model_validate(result)
    assert result == client.get(url).json()
    gap = result["skill_gaps"][0]
    assert (gap["current_level"], gap["target_level"], gap["skill_gap"]) == (1, 3, 2)
    assert gap["proficiency_status"] == "provisional"
    assert len(gap["detail"]["next_steps"]) == 2
    resource = gap["learning_resources"][0]
    assert resource["title"] == "Synthetic Practice Resource"
    assert resource["source_row"] == 4 and resource["mapping_row"] == 4
    assert resource["url"] is None
    with SessionLocal() as db:
        db.get(models.User, seeded["user"]["id"]).xp_points = 99999
        db.commit()
    assert client.get(url).json()["skill_gaps"][0]["current_level"] == 1


def test_tni_without_sources_and_empty_profile(client, seeded):
    url = f"/users/{seeded['user']['id']}/tni"
    assert client.get(url).json()["skill_gaps"] == []
    assert client.get("/users/9999/tni").status_code == 404
    questions = generate(client, seeded, 1)
    approve(client, questions)
    submit(client, assign(client, seeded, 1), questions, 1)
    gap = client.get(url).json()["skill_gaps"][0]
    assert gap["learning_resources"] == []
    assert gap["detail"]["recommended_resource_ids"] == []
    assert "unavailable" in gap["learning_status"]


def test_zero_target_and_changed_not_expected(client, seeded):
    with SessionLocal() as db:
        db.get(models.RoleSkillMap, seeded["mapping"]["id"]).target_level = 0
        db.commit()
    questions = generate(client, seeded, 1)
    approve(client, questions)
    assessment = assign(client, seeded, 1)
    result = submit(client, assessment, questions, 1).json()
    assert result["achieved_level"] == 0
    gap = client.get(f"/users/{seeded['user']['id']}/tni").json()["skill_gaps"][0]
    assert gap["target_level"] == 0 and gap["skill_gap"] == 0
    another = assign(client, seeded, 1)
    with SessionLocal() as db:
        db.get(models.RoleSkillMap, seeded["mapping"]["id"]).target_level = None
        db.commit()
    assert submit(client, another, questions, 1).status_code == 400
    assert client.get(f"/users/{seeded['user']['id']}/tni").json()["skill_gaps"] == []
