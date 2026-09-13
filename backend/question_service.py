import schemas
import config
from llm_provider import get_provider, ProviderError
from rag_service import build_finance_rag_context
from offline_rag import retrieve, RagError

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


def generate_rd_question_drafts(
    role_band: str,
    source_skill_id: str,
    skill_name: str,
    target_level: int,
    target_label: str,
    difficulty: str,
    question_count: int,
):
    """Generate a DataOps draft only from eligible, locally indexed context."""
    try:
        grounding = retrieve(
            function="DataOps",
            skill_id=source_skill_id,
            intended_proficiency=target_label,
            query=f"{skill_name} {role_band} {target_label} {difficulty}",
            limit=max(question_count, 3),
        )
    except RagError as error:
        raise ProviderError(str(error)) from None
    context = "\n\n".join(
        f"[{chunk['chunk_id']} | {chunk['source_id']} | {chunk['reference']}] {chunk['text']}"
        for chunk in grounding["selected_chunks"]
    )
    user_prompt = f"""
Function: RD/DataOps
Role band: {role_band}
Skill_ID: {source_skill_id}
Skill: {skill_name}
Target proficiency: {target_label} ({target_level})
Requested difficulty: {difficulty}
Number of questions: {question_count}

Approved retrieved context:
{context}

Use only the retrieved context. Do not use outside knowledge. Return the requested JSON questions.
"""
    provider = get_provider()
    drafts = provider.questions(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        skill_name=skill_name,
        target_level=target_level,
        question_count=question_count,
        grounding=grounding,
    )
    selected = grounding["selected_chunks"]
    provenance = {
        "source_skill_id": source_skill_id,
        "target_proficiency": target_label,
        "difficulty": difficulty,
        "question_type": "multiple_choice",
        "source_ids": grounding["source_ids"],
        "chunk_references": grounding["chunk_references"],
        "document_references": grounding["document_references"],
        "ai_confidence": "mock-deterministic" if provider.name == "mock" else "provider-supplied",
        "provider_name": provider.name,
        "provider_model": "deterministic-local" if provider.name == "mock" else config.CIS_MODEL,
        "synthetic_only": bool(selected) and all(chunk["synthetic_only"] for chunk in selected),
    }
    return drafts, provenance
