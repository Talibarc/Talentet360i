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
Return a JSON array with exactly the requested number of objects, using only these fields:
{"question_text":"A complete question", "options":{"A":"First option", "B":"Second option", "C":"Third option", "D":"Fourth option"}, "correct_answer":"A", "explanation":"Source-supported rationale"}
Use the exact field names. All text must be nonempty; all four options must be distinct.
correct_answer must be one option key (A, B, C or D), never the answer text.
Source IDs, citations, skill IDs and document versions are retained by the application from retrieved context. Do not invent them.
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
        f"[{chunk['chunk_id']} | {chunk['source_id']} | {chunk['reference']} | version {chunk.get('version', 'unavailable')}] {chunk['text']}"
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
        "document_references": sorted({f"{chunk['document_filename']}@{chunk.get('version', 'version unavailable')}" for chunk in selected}),
        "ai_confidence": "mock-deterministic" if provider.name == "mock" else "Not supplied",
        "provider_name": provider.name,
        "provider_model": "deterministic-local" if provider.name == "mock" else config.CIS_MODEL,
        "synthetic_only": provider.name == "mock" or any(chunk["synthetic_only"] for chunk in selected),
    }
    return drafts, provenance


def generate_finance_mapped(db, mapping, source, payload):
    import json
    import models
    from fastapi import HTTPException
    if not source.fingerprint:
        raise HTTPException(409, "Mapping unavailable — pending source validation.")
    questions = db.query(models.Question).join(models.QuestionScope).filter(
        models.QuestionScope.role_skill_map_id == mapping.id, models.Question.status == "approved").all()
    references = []
    for question in questions:
        record = db.query(models.SourceRecord).filter_by(entity_type="question", entity_id=question.id).first()
        if record and record.fingerprint and record.details.get("status") == "approved":
            if config.LLM_PROVIDER == "luna" and "synthetic" in str(record.details.get("source_label", "")).lower():
                continue
            references.append({"id": record.source_key, "workbook": record.workbook,
                "sheet": record.sheet, "row": record.source_row, "fingerprint": record.fingerprint,
                "question": question.question_text, "options": question.options, "answer": question.correct_answer})
    if not references:
        raise HTTPException(409, "No validated approved Finance question-bank context for this mapping")
    provider = get_provider()
    skill = db.get(models.Skill, mapping.skill_id)
    drafts = provider.questions(system_prompt=SYSTEM_PROMPT,
        user_prompt=json.dumps({"mapping": source.details, "approved_question_bank": references,
            "question_count": payload.question_count, "difficulty": payload.difficulty}),
        skill_name=skill.name, target_level=mapping.target_level, question_count=payload.question_count)
    grounding = {"source_skill_id": source.details["skill_key"], "target_proficiency": mapping.target_label or str(mapping.target_level),
        "difficulty": payload.difficulty, "question_type": "multiple_choice",
        "source_ids": [r["id"] for r in references], "chunk_references": [],
        "document_references": [f"{r['workbook']}/{r['sheet']}/row {r['row']}@{r['fingerprint']}" for r in references],
        "ai_confidence": "Not supplied", "provider_name": provider.name,
        "provider_model": "deterministic-local" if provider.name == "mock" else config.CIS_MODEL,
        "synthetic_only": provider.name == "mock"}
    return drafts, grounding
