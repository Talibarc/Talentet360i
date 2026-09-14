"""Allocate the SME-approved 20-item blueprint without inventing difficulty labels."""
from functools import lru_cache
from fastapi import HTTPException
import models
import config


def select_workbook_questions(db, employee_id, role_id):
    mappings = db.query(models.RoleSkillMap).filter_by(role_id=role_id, is_expected=True).all()
    expected = {m.id: m for m in mappings if m.target_level is not None}
    if len(expected) > 20:
        raise HTTPException(409, "Twenty questions cannot cover every required role skill. Pending SME allocation policy.")
    previous = {q for (q,) in db.query(models.AssessmentItem.question_id).join(models.Assessment).filter(
        models.Assessment.employee_id == employee_id, models.Assessment.status == "submitted")}
    groups = [[] for _ in range(6)]
    by_skill = {key: {} for key in expected}
    for question, scope in db.query(models.Question, models.QuestionScope).join(models.QuestionScope).filter(
        models.Question.status == "approved", models.QuestionScope.role_skill_map_id.in_(expected)):
        if question.skill_level != expected[scope.role_skill_map_id].target_level:
            continue
        grounding = db.get(models.QuestionGrounding, question.id)
        source = db.query(models.SourceRecord).filter_by(entity_type="question", entity_id=question.id).first()
        if config.LLM_PROVIDER == "luna" and ((grounding and grounding.synthetic_only)
                or "synthetic" in (question.rag_source or "").lower()):
            continue
        difficulty = grounding.difficulty if grounding else source.details.get("difficulty") if source and source.fingerprint else None
        if difficulty not in ("Easy", "Moderate", "Difficult"):
            continue
        group = ("Easy", "Moderate", "Difficult").index(difficulty) * 2 + int(question.id in previous)
        groups[group].append(question)
        by_skill[scope.role_skill_map_id].setdefault(group, []).append(question)
    required = sorted(by_skill, key=lambda key: len(by_skill[key]))
    quotas = (6, 8, 6)
    totals = tuple(len(g) for g in groups)

    @lru_cache(None)
    def cover(index, counts):
        if sum(counts[1::2]) > 6:
            return None
        if index == len(required):
            final = list(counts)
            for difficulty, quota in enumerate(quotas):
                new, old = difficulty*2, difficulty*2+1
                missing = quota-final[new]-final[old]
                added = min(missing, totals[new]-final[new])
                final[new] += added
                final[old] += missing-added
                if final[old] > totals[old]:
                    return None
            return () if sum(final[1::2]) <= 6 else None
        for group in by_skill[required[index]]:
            if counts[group//2*2] + counts[group//2*2+1] >= quotas[group//2]:
                continue
            updated = list(counts)
            updated[group] += 1
            rest = cover(index+1, tuple(updated))
            if rest is not None:
                return (group,) + rest
        return None

    choices = cover(0, (0,)*6)
    if choices is None:
        raise HTTPException(409, "Insufficient approved pool: need 20 questions, 6 Easy / 8 Moderate / 6 Difficult, every required role skill, and at least 70% new questions on reassessment.")
    chosen = [by_skill[key][group][0] for key, group in zip(required, choices)]
    used = {q.id for q in chosen}
    for difficulty, quota in enumerate(quotas):
        missing = quota-sum(choices.count(group) for group in (difficulty*2,difficulty*2+1))
        for group in (difficulty*2,difficulty*2+1):
            for question in groups[group]:
                if missing and question.id not in used:
                    chosen.append(question); used.add(question.id); missing -= 1
    if sum(q.id in previous for q in chosen) > 6 or len(chosen) != 20:
        raise HTTPException(409, "Insufficient approved reassessment pool")
    return chosen
