import json
from typing import Any

import schemas
from llm_service import generate_text
from rag_service import build_finance_rag_context

SYSTEM_PROMPT = """
You are Talent360i, an enterprise skill-assessment specialist.
Create fair, scenario-based multiple-choice questions.
Use only the supplied source context.
Return only valid JSON without markdown or extra text.
Each question must have exactly four options: A, B, C and D.
Only one option can be correct.
"""
 
 
def _extract_json_array(raw_text: str) -> list[dict[str, Any]]:
    start = raw_text.find("[")
    end = raw_text.rfind("]")
 
    if start == -1 or end == -1:
        raise ValueError("Luna did not return a valid JSON array")
 
    data = json.loads(raw_text[start : end + 1])
 
    if not isinstance(data, list):
        raise TypeError("Luna response must be a JSON array")
 
    return data
 
 
def generate_question_drafts(
    role_name: str,
    skill_name: str,
    target_level: int,
    target_label: str,
    source_context: str,
    question_count: int,
) -> list[schemas.GeneratedQuestion]:
    rag_context = build_finance_rag_context(
    role_name,
    skill_name,
)
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
 
    raw_response = generate_text(SYSTEM_PROMPT, user_prompt)
    items = _extract_json_array(raw_response)

    for item in items:
     item["rag_source"] = "Finance Excel RAG"
 
    return [
        schemas.GeneratedQuestion.model_validate(item)
        for item in items
    ]