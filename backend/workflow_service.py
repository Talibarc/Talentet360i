from fastapi import HTTPException
from sqlalchemy import update
import models
from auth import employee_access, manager_access, mapping_access, require
from event_service import audit, notify, award_xp


def get_evidence(db, evidence_id):
    evidence = db.get(models.Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(404, "Evidence not found")
    return evidence


def evidence_content(db, evidence):
    content = db.query(models.EvidenceRevision).filter_by(evidence_id=evidence.id,
                                                         revision=evidence.revision).one()
    return {"id": evidence.id, "employee_id": evidence.employee_id,
            "role_skill_map_id": evidence.role_skill_map_id, "assessment_id": evidence.assessment_id,
            "status": evidence.status, "revision": evidence.revision,
            "title": content.title, "description": content.description, "url": content.url,
            "created_at": evidence.created_at}


def evidence_history(db, actor, evidence_id):
    evidence = get_evidence(db, evidence_id)
    employee_access(db, actor, evidence.employee_id)
    return {"evidence": evidence_content(db, evidence),
            "revisions": db.query(models.EvidenceRevision).filter_by(evidence_id=evidence_id).order_by(models.EvidenceRevision.id).all(),
            "decisions": db.query(models.ManagerDecision).filter_by(evidence_id=evidence_id).order_by(models.ManagerDecision.id).all()}


def refresh_review(db, evidence):
    if evidence.assessment_id:
        review = db.get(models.ResultReview, evidence.assessment_id)
        if not review or review.status == "confirmed":
            raise HTTPException(409, "Confirmed or legacy results cannot accept new evidence; submit a new assessment")
        if db.execute(update(models.ResultReview).where(
            models.ResultReview.assessment_id == evidence.assessment_id,
            models.ResultReview.revision == review.revision,
            models.ResultReview.status != "confirmed").values(
                status="pending_review", revision=models.ResultReview.revision + 1)).rowcount != 1:
            raise HTTPException(409, "Result review changed; reload before submitting evidence")


def submit_evidence(db, actor, payload, evidence_id=None):
    require(actor, "employee")
    if evidence_id is None:
        mapping = mapping_access(db, actor, payload.role_skill_map_id)
        if not mapping.is_expected or mapping.target_level is None:
            raise HTTPException(400, "Skill is Not Expected")
        if payload.assessment_id:
            assessment = db.get(models.Assessment, payload.assessment_id)
            if not assessment or assessment.employee_id != actor.id or assessment.role_skill_map_id != mapping.id:
                raise HTTPException(403, "Assessment does not belong to this employee and skill")
            if assessment.status != "submitted":
                raise HTTPException(409, "Submit the assessment before attaching evidence")
        evidence = models.Evidence(employee_id=actor.id, role_skill_map_id=mapping.id,
                                   assessment_id=payload.assessment_id, revision=1, status="submitted")
        db.add(evidence)
        db.flush()
        action = "evidence.submitted"
    else:
        evidence = get_evidence(db, evidence_id)
        employee_access(db, actor, evidence.employee_id, write=True)
        if db.execute(update(models.Evidence).where(models.Evidence.id == evidence.id,
            models.Evidence.revision == payload.expected_revision, models.Evidence.status == "sent_back")
            .values(revision=models.Evidence.revision + 1, status="submitted")).rowcount != 1:
            raise HTTPException(409, "Only the current sent-back revision may be resubmitted")
        db.refresh(evidence)
        action = "evidence.resubmitted"
    refresh_review(db, evidence)
    db.add(models.EvidenceRevision(evidence_id=evidence.id, revision=evidence.revision,
        title=payload.title, description=payload.description, url=str(payload.url) if payload.url else None,
        actor_id=actor.id))
    audit(db, actor.id, action, "evidence", evidence.id, subject_id=actor.id,
          details={"revision": evidence.revision, "assessment_id": evidence.assessment_id})
    profile = db.get(models.UserProfile, actor.id)
    if profile and profile.manager_id:
        notify(db, profile.manager_id, "Evidence awaiting review", "A direct report submitted evidence.",
               action, evidence.id, actor.id)
    db.flush()
    return evidence_content(db, evidence)


def decide_evidence(db, actor, evidence_id, payload):
    evidence = get_evidence(db, evidence_id)
    manager_access(db, actor, evidence.employee_id)
    status = "confirmed" if payload.decision == "confirm" else "sent_back"
    if db.execute(update(models.Evidence).where(models.Evidence.id == evidence_id,
        models.Evidence.revision == payload.expected_revision, models.Evidence.status == "submitted")
        .values(status=status)).rowcount != 1:
        raise HTTPException(409, "Evidence state/revision changed; reload before deciding")
    decision = models.ManagerDecision(manager_id=actor.id, employee_id=evidence.employee_id,
        evidence_id=evidence.id, decision=payload.decision, comment=payload.comment,
        reviewed_revision=payload.expected_revision)
    db.add(decision)
    db.flush()
    audit(db, actor.id, "manager.evidence_decided", "evidence", evidence.id,
          subject_id=evidence.employee_id, details={"decision_id": decision.id, "decision": payload.decision})
    notify(db, evidence.employee_id, "Evidence reviewed", payload.comment,
           "evidence.reviewed", evidence.id, actor.id)
    db.refresh(evidence)
    return {"evidence": evidence_content(db, evidence), "decision": decision}


def decide_result(db, actor, assessment_id, payload):
    assessment = db.get(models.Assessment, assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    manager_access(db, actor, assessment.employee_id)
    if assessment.status != "submitted":
        raise HTTPException(409, "Only submitted results can be reviewed")
    if payload.decision == "confirm" and assessment.achieved_level is None:
        raise HTTPException(409, "Result pending policy validation; no official level can be inferred")
    mapping = db.get(models.RoleSkillMap, assessment.role_skill_map_id)
    member = db.get(models.UserProfile, assessment.employee_id)
    if not mapping or not mapping.is_expected or mapping.target_level is None or member.job_role_id != mapping.role_id:
        raise HTTPException(409, "Result no longer matches an expected skill in the employee job role")
    pending = db.query(models.Evidence).filter_by(assessment_id=assessment_id).all()
    if payload.decision == "confirm" and any(e.status != "confirmed" for e in pending):
        raise HTTPException(409, "Review and confirm all linked evidence before confirming the result")
    official = db.query(models.OfficialLevel).filter_by(employee_id=assessment.employee_id,
        role_skill_map_id=assessment.role_skill_map_id).first()
    if official and payload.decision == "confirm":
        prior = db.get(models.Assessment, official.assessment_id)
        if (prior.submitted_at, prior.id) > (assessment.submitted_at, assessment.id):
            raise HTTPException(409, "A newer assessment is already official")
    if db.execute(update(models.ResultReview).where(models.ResultReview.assessment_id == assessment_id,
        models.ResultReview.status == "pending_review", models.ResultReview.revision == payload.expected_revision)
        .values(status="confirmed" if payload.decision == "confirm" else "sent_back",
                revision=models.ResultReview.revision + 1)).rowcount != 1:
        raise HTTPException(409, "Review state/revision changed; reload before deciding")
    decision = models.ManagerDecision(manager_id=actor.id, employee_id=assessment.employee_id,
        assessment_id=assessment_id, decision=payload.decision, comment=payload.comment,
        reviewed_revision=payload.expected_revision,
        confirmed_level=assessment.achieved_level if payload.decision == "confirm" else None)
    db.add(decision)
    db.flush()
    if payload.decision == "confirm":
        if official is None:
            official = models.OfficialLevel(employee_id=assessment.employee_id,
                                             role_skill_map_id=assessment.role_skill_map_id)
            db.add(official)
        official.assessment_id, official.decision_id = assessment.id, decision.id
        official.confirmed_level = assessment.achieved_level
        official.confirmed_at = models.utc_now()
    audit(db, actor.id, "manager.result_decided", "assessment", assessment_id,
          subject_id=assessment.employee_id, details={"decision_id": decision.id, "decision": payload.decision,
                                                     "confirmed_level": decision.confirmed_level})
    notify(db, assessment.employee_id, "Assessment result reviewed", payload.comment,
           "result.reviewed", assessment_id, actor.id)
    db.flush()
    return {"decision": decision, "review": db.get(models.ResultReview, assessment_id),
            "official_confirmed_level": official.confirmed_level if official else None}


def resubmit_result(db, actor, assessment_id, payload):
    require(actor, "employee")
    assessment = db.get(models.Assessment, assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    employee_access(db, actor, assessment.employee_id, write=True)
    if db.execute(update(models.ResultReview).where(models.ResultReview.assessment_id == assessment_id,
        models.ResultReview.status == "sent_back", models.ResultReview.revision == payload.expected_revision)
        .values(status="pending_review", revision=models.ResultReview.revision + 1)).rowcount != 1:
        raise HTTPException(409, "Only a current sent-back result can be resubmitted")
    audit(db, actor.id, "assessment.review_resubmitted", "assessment", assessment_id,
          subject_id=actor.id, details={"comment": payload.comment})
    details = db.get(models.UserProfile, actor.id)
    if details and details.manager_id:
        notify(db, details.manager_id, "Result resubmitted", payload.comment,
               "result.resubmitted", assessment_id, actor.id)
    return db.get(models.ResultReview, assessment_id)


def quest_progress(db, actor, quest):
    details = db.get(models.UserProfile, actor.id)
    if quest.business_function and (not details or details.business_function != quest.business_function):
        raise HTTPException(403, "Quest is outside your function")
    count = db.query(models.AuditEvent.entity_id).filter(models.AuditEvent.subject_id == actor.id,
        models.AuditEvent.action == quest.event_type, models.AuditEvent.created_at >= quest.created_at).distinct().count()
    claimed = db.query(models.XpAward).filter_by(employee_id=actor.id, source_key=f"quest:{quest.id}").first()
    return {"quest": quest, "progress": min(count, quest.required_count), "completed": count >= quest.required_count,
            "claimed": bool(claimed)}


def claim_quest(db, actor, quest_id):
    require(actor, "employee")
    quest = db.get(models.Quest, quest_id)
    if quest is None or not quest.active:
        raise HTTPException(404, "Active quest not found")
    progress = quest_progress(db, actor, quest)
    if not progress["completed"]:
        raise HTTPException(409, "Quest requirements have not been completed")
    if not progress["claimed"]:
        award_xp(db, actor.id, quest.xp_reward, f"quest:{quest.id}", actor.id)
        audit(db, actor.id, "quest.claimed", "quest", quest.id, subject_id=actor.id)
        notify(db, actor.id, "Quest complete", "Engagement XP awarded; proficiency is unchanged.",
               "quest.claimed", quest.id, actor.id)
    return {**progress, "claimed": True, "xp_reward": quest.xp_reward}
