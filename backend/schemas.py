from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
 
 
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

    @model_validator(mode="after")
    def blank_is_not_expected(self):
        if self.target_level is None:
            self.is_expected = False
        return self
 
 
class RoleSkillMapResponse(RoleSkillMapCreate):
    id: int
 
    model_config = ConfigDict(from_attributes=True)
class QuestionGenerateRequest(BaseModel):
    role_skill_map_id: int = Field(gt=0)
    question_count: int = Field(default=3, ge=1, le=5)
 
 
class GeneratedQuestion(BaseModel):
    question_text: str = Field(min_length=1)
    options: dict[str, str]
    correct_answer: str = Field(pattern="^[A-D]$")
    explanation: str = Field(min_length=1)
    rag_source: str | None = None

    @model_validator(mode="after")
    def validate_options(self):
        if set(self.options) != set("ABCD") or any(
            not option.strip() for option in self.options.values()
        ):
            raise ValueError("Questions require four nonempty options A, B, C, D")
        if len(set(self.options.values())) != 4:
            raise ValueError("Question options must be distinct")
        return self
 
 
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

    @model_validator(mode="after")
    def unique_answers(self):
        if len({answer.question_id for answer in self.answers}) != len(self.answers):
            raise ValueError("Submit exactly one answer per question")
        return self


class LearningResource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: str
    title: str
    url: str | None = None
    source_file: str
    source_sheet: str
    source_row: int
    mapping_sheet: str
    mapping_row: int
    source_skill_id: str
    level_scope: str | None = None
    review_status: str | None = None


class TniNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1)
    development_focus: str = Field(min_length=1)
    next_steps: list[str] = Field(min_length=1)
    recommended_resource_ids: list[str]
    limitations: list[str]


class TniSkillGap(BaseModel):
    assessment_id: int
    role_skill_map_id: int
    skill_id: int
    skill_name: str
    score_percentage: int
    current_level: int
    target_level: int
    skill_gap: int
    gap_status: str
    expert_confirmation_required: bool
    recommendation: str
    detail: TniNarrative
    learning_resources: list[LearningResource]
    learning_status: str
    proficiency_status: Literal["provisional"] = "provisional"


class EmployeeTniResponse(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    xp_points: int
    skills_assessed: int
    target_met: int
    development_needed: int
    provider: Literal["mock", "luna"]
    skill_gaps: list[TniSkillGap]
 
 
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
  
