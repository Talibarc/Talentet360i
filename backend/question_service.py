import schemas
from llm_provider import get_provider, ProviderError
from rag_service import build_finance_rag_context

SYSTEM_PROMPT = """
You are Talent360i, an enterprise skill-assessment specialist.
Create fair, scenario-based multiple-choice questions.
Use only the supplied source context.
Return only valid JSON without markdown or extra text.
Each question must have exactly four options: A, B, C and D.
Only one option can be correct.
"""
 
 
def generate_question_drafts(
    role_name: str,
    skill_name: str,
    target_level: int,
    target_label: str,
    source_context: str,
    question_count: int,
) -> list[schemas.GeneratedQuestion]:
    provider = get_provider()
    if provider.name == "mock":
        rag_context = "Synthetic practice only; no company source retrieval."
    else:
        try:
            rag_context = build_finance_rag_context(role_name, skill_name)
        except (ValueError, FileNotFoundError, KeyError):
            raise ProviderError("Required Finance source context is unavailable") from None
    user_prompt = f"""
Role: {role_name}
Skill: {skill_name}
Target level: {target_level} - {target_label}
Number of questions: {question_count}

Retrieved company source context:
{rag_context}
 
Use the retrieved company context as the primary source of truth.
Do not invent company policies, responsibilities, controls, or skill expectations.
Set rag_source exactly to "Finance Excel RAG".
 
 
Source context:
{source_context}
 
Return this JSON structure:
[
  {{
    "question_text": "Scenario-based question",
    "options": {{
      "A": "Option A",
      "B": "Option B",
      "C": "Option C",
      "D": "Option D"
    }},
    "correct_answer": "A",
    "explanation": "Why the answer is correct"
  }}
]
"""
 
    return provider.questions(
        system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt,
        skill_name=skill_name, target_level=target_level, question_count=question_count,
    )
