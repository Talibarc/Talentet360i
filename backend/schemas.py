from pydantic import BaseModel, ConfigDict, Field
 
 
class RoleCreate(BaseModel):
    role_code: str = Field(min_length=2, max_length=50)
    role_name: str = Field(min_length=2, max_length=150)
    business_function: str = Field(min_length=2, max_length=100)
    tower: str | None = None
    role_grade: str | None = None
    level_framework: str = "NUMERIC_0_5"
 
 
class RoleResponse(RoleCreate):
    id: int
 
    model_config = ConfigDict(from_attributes=True)
 
 
class SkillCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    max_level: int = Field(default=5, ge=1, le=5)
 
 
class SkillResponse(SkillCreate):
    id: int
 
    model_config = ConfigDict(from_attributes=True)
 
 
class RoleSkillMapCreate(BaseModel):
    role_id: int
    skill_id: int
    target_level: int | None = Field(default=None, ge=0, le=5)
    target_label: str | None = None
    is_expected: bool = True
 
 
class RoleSkillMapResponse(RoleSkillMapCreate):
    id: int
 
    model_config = ConfigDict(from_attributes=True)
class QuestionGenerateRequest(BaseModel):
    role_skill_map_id: int = Field(gt=0)
    question_count: int = Field(default=3, ge=1, le=5)
 
 
class GeneratedQuestion(BaseModel):
    question_text: str
    options: dict[str, str]
    correct_answer: str = Field(pattern="^[A-D]$")
    explanation: str
 
 
class QuestionResponse(GeneratedQuestion):
    id: int
    skill_id: int
    skill_level: int
    rag_source: str | None = None
    status: str
 
    model_config = ConfigDict(from_attributes=True)    


class QuestionReviewRequest(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    review_comment: str | None = Field(default=None, max_length=500)

class AssessmentCreate(BaseModel):
    employee_id: int = Field(gt=0)
    role_skill_map_id: int = Field(gt=0)
    question_count: int = Field(default=5, ge=1, le=20)
 
 
class AssessmentQuestionItem(BaseModel):
    question_id: int
    skill_id: int
    skill_level: int
    question_text: str
    options: dict[str, str]
 
 
class AssessmentResponse(BaseModel):
    id: int
    employee_id: int
    role_skill_map_id: int
    status: str
    total_questions: int
    correct_answers: int
    score_percentage: int | None = None
    achieved_level: int | None = None
    xp_awarded: int
 
    model_config = ConfigDict(from_attributes=True)
 
 
class AssessmentAnswerSubmit(BaseModel):
    question_id: int = Field(gt=0)
    selected_answer: str = Field(pattern="^[A-D]$")
 
 
class AssessmentSubmitRequest(BaseModel):
    answers: list[AssessmentAnswerSubmit] = Field(min_length=1)
 
 
class AssessmentResult(BaseModel):
    assessment_id: int
    status: str
    total_questions: int
    correct_answers: int
    score_percentage: int
    achieved_level: int | None = None
    xp_awarded: int

class UserCreate(BaseModel):
    employee_id: str = Field(min_length=2, max_length=50)
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=150)
    role: str = Field(
        default="employee",
        pattern="^(employee|reviewer|manager|leader)$",
    )
    department: str | None = None
 
 
class UserResponse(UserCreate):
    id: int
    xp_points: int
 
    model_config = ConfigDict(from_attributes=True)    
  
