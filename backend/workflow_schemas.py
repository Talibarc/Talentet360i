from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator
from schemas import GeneratedQuestion


class QuestionEdit(GeneratedQuestion):
    expected_revision: int = Field(ge=1)
    comment: str = Field(min_length=1, max_length=1000)
    is_critical: bool = False


class PolicyCreate(BaseModel):
    full_score_min: int = Field(default=95, ge=1, le=100)
    middle_score_min: int = Field(default=81, ge=0, le=99)
    critical_fail_level: int | None = Field(default=None, ge=0, le=5)
    source_reference: str = Field(min_length=3, max_length=1000)

    @model_validator(mode="after")
    def ordered_bands(self):
        if self.middle_score_min >= self.full_score_min:
            raise ValueError("Score bands must be ordered")
        return self


class EvidenceContent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    url: HttpUrl | None = None


class EvidenceCreate(EvidenceContent):
    role_skill_map_id: int = Field(gt=0)
    assessment_id: int | None = Field(default=None, gt=0)


class EvidenceResubmit(EvidenceContent):
    expected_revision: int = Field(ge=1)


class DecisionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    decision: Literal["confirm", "send_back"]
    comment: str = Field(min_length=1, max_length=2000)
    expected_revision: int = Field(ge=1)


class ReviewResubmit(BaseModel):
    expected_revision: int = Field(ge=1)
    comment: str = Field(min_length=1, max_length=2000)


class NotificationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    recipient_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)


class QuestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    event_type: Literal["assessment.submitted", "evidence.submitted"]
    required_count: int = Field(ge=1, le=100)
    xp_reward: int = Field(ge=0, le=1000)
    business_function: str | None = None


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_role_id: int | None = Field(default=None, gt=0)
    manager_id: int | None = Field(default=None, gt=0)
    business_function: str | None = Field(default=None, max_length=100)
    team: str | None = Field(default=None, max_length=100)
    hub: str | None = Field(default=None, max_length=100)


class SourceRemap(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill_ids: list[str] = Field(min_length=1, max_length=100)
    expected_skill_ids: list[str]
    comment: str = Field(min_length=3, max_length=1000)
    confirmed: Literal[True]


class QuestionManage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    confirmed: Literal[True]
    comment: str = Field(min_length=3, max_length=1000)
