"""Provider selection. Mock never imports the Azure adapter or retrieves company data."""

import json
from typing import Protocol

import config
from schemas import GeneratedQuestion, TniNarrative


class ProviderError(RuntimeError):
    """Safe client-facing error, with no credentials or remote response contents."""


class LlmProvider(Protocol):
    name: str

    def questions(self, *, system_prompt: str, user_prompt: str, skill_name: str,
                  target_level: int, question_count: int) -> list[GeneratedQuestion]: ...

    def tni(self, facts: dict, resources: list[dict]) -> TniNarrative: ...


class MockProvider:
    name = "mock"

    def questions(self, *, system_prompt: str, user_prompt: str, skill_name: str,
                  target_level: int, question_count: int) -> list[GeneratedQuestion]:
        # Explicit fictional exercises: never represent these as company SOP rules.
        exercises = [
            ("a practice checklist requires comparing a total with its source before submission",
             "The totals differ. What follows the checklist?",
             "Investigate the difference against the source before submitting",
             ["Submit without checking", "Change the source to force agreement", "Hide the difference"]),
            ("a practice runbook requires recording the failed check before retrying",
             "A check fails. What should happen first?", "Record the failed check",
             ["Retry without a record", "Mark the check successful", "Delete the failed result"]),
            ("a practice handoff requires a status and an unresolved-issues note",
             "An issue remains open. Which handoff is complete?",
             "Include the current status and the unresolved issue",
             ["Provide only a success label", "Omit the open issue", "Send an empty handoff"]),
            ("a practice dataset requires unique record identifiers",
             "Two records share an identifier. What meets that requirement?",
             "Resolve the duplicate identifiers before accepting the dataset",
             ["Accept the duplicates", "Ignore identifiers entirely", "Rename unrelated fields only"]),
            ("a practice procedure requires checking the current approved instruction",
             "Two instruction versions differ. What follows the procedure?",
             "Check which instruction is current and approved",
             ["Choose whichever is shorter", "Use an unapproved draft", "Combine conflicting steps arbitrarily"]),
        ]
        result = []
        for i in range(question_count):
            context, scenario, correct, distractors = exercises[i % len(exercises)]
            correct_key = "ABCD"[i % 4]
            alternatives = iter(distractors)
            options = {key: correct if key == correct_key else next(alternatives) for key in "ABCD"}
            result.append(GeneratedQuestion(
                question_text=(f"[Synthetic practice {i + 1}] {skill_name}, level {target_level}: "
                               f"In this fictional exercise, {context}. {scenario}"),
                options=options, correct_answer=correct_key,
                explanation=f"The fictional instruction states that {context}. No company policy is implied.",
                rag_source="Synthetic mock fixture; not company SOP evidence",
            ))
        return result

    def tni(self, facts: dict, resources: list[dict]) -> TniNarrative:
        gap = facts["skill_gap"]
        return TniNarrative(
            summary=(f"{facts['skill_name']}: provisional level {facts['current_level']} "
                     f"against target {facts['target_level']}; gap {gap}."),
            development_focus=(f"Review demonstrated gaps in {facts['skill_name']} before reassessment."
                               if gap else "Maintain the demonstrated skill and review the provisional result."),
            next_steps=(
                ["Review the supplied mapped resources and their stated scope with the reviewer.",
                 "Reassess after addressing the identified gap."] if resources else
                ["Ask L&D to validate an applicable learning mapping before selecting training.",
                 "Review the assessment result with the reviewer."]
            ),
            recommended_resource_ids=[r["resource_id"] for r in resources],
            limitations=["Mock narrative; achieved levels use the existing provisional scoring rule.",
                         "Manager confirmation is not implemented in Phase 1.",
                         "Resource mappings do not establish document approval or level suitability."],
        )


class LunaProvider:
    name = "luna"

    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        if not config.CIS_BASE_URL or not config.CIS_API_KEY or not config.CIS_MODEL:
            raise ProviderError("Configure the Luna endpoint, key, and model on the company laptop")
        # Keep the original transport/authentication implementation intact.
        from llm_service import generate_text
        try:
            return generate_text(system_prompt, user_prompt)
        except Exception:
            raise ProviderError("Luna request failed; check company-laptop configuration") from None

    def questions(self, *, system_prompt: str, user_prompt: str, skill_name: str,
                  target_level: int, question_count: int) -> list[GeneratedQuestion]:
        raw = self._generate(system_prompt, user_prompt)
        try:
            # Preserve support for the existing adapter's wrapped JSON responses.
            data = json.loads(raw[raw.index("["):raw.rindex("]") + 1])
            if not isinstance(data, list) or len(data) != question_count:
                raise ValueError("Wrong question count")
            return [GeneratedQuestion.model_validate({**item, "rag_source": "Finance Excel RAG"})
                    for item in data]
        except (ValueError, TypeError):
            raise ProviderError("Luna returned invalid question data") from None

    def tni(self, facts: dict, resources: list[dict]) -> TniNarrative:
        raw = self._generate(
            "Return a JSON TNI narrative using only supplied facts and learning resources. "
            "Do not calculate or change proficiency. Do not invent courses, URLs, or policies. "
            "Use only supplied resource IDs, with an empty list if none exist. "
            "Return summary, development_focus, next_steps (string array), "
            "recommended_resource_ids (string array), limitations (string array).",
            json.dumps({"facts": facts, "available_resources": resources}),
        )
        try:
            return TniNarrative.model_validate_json(raw)
        except ValueError:
            raise ProviderError("Luna returned invalid TNI data") from None


def get_provider() -> LlmProvider:
    if config.LLM_PROVIDER == "mock":
        return MockProvider()
    if config.LLM_PROVIDER == "luna":
        return LunaProvider()
    raise ProviderError("LLM_PROVIDER must be mock or luna")
