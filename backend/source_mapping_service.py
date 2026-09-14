"""Source remapping changes retrieval metadata, never document content."""
from fastapi import HTTPException
import models
from offline_rag import load_index
from event_service import audit
from sqlalchemy import update


def remap(db, actor, source_id, payload):
    registered = db.query(models.SourceRecord).filter_by(workbook="overall_rd.xlsx",
        entity_type="source_metadata", source_key=source_id).first()
    if not registered or not registered.fingerprint:
        raise HTTPException(409, "Import and validate this source before changing its mapping")
    known = {r.source_key for r in db.query(models.SourceRecord).filter_by(
        workbook="overall_rd.xlsx", entity_type="skill") if r.fingerprint}
    selected = sorted(set(payload.skill_ids))
    if set(selected) - known:
        raise HTTPException(422, "Unknown Skill_ID. Select skills from the imported workbook")
    sources = [r for r in load_index().get("sources", []) if r.get("source_id") == source_id
               and r.get("ingestion_status") == "Ingested"]
    if not sources:
        raise HTTPException(404, "No ingested document for this source")
    previous = sorted({skill for r in sources for skill in r.get("skill_ids", [])})
    if previous != sorted(set(payload.expected_skill_ids)):
        raise HTTPException(409, "Mapping changed. Reload the source and review the current mapping")
    row = db.get(models.SourceSkillOverride, source_id)
    if row is None:
        db.add(models.SourceSkillOverride(source_id=source_id, skill_ids=selected))
    else:
        changed = db.execute(update(models.SourceSkillOverride).where(
            models.SourceSkillOverride.source_id == source_id,
            models.SourceSkillOverride.skill_ids == row.skill_ids).values(skill_ids=selected))
        if changed.rowcount != 1:
            raise HTTPException(409, "Mapping changed. Reload and review the current mapping")
    audit(db, actor.id, "source.skills_remapped", "source", registered.id,
          details={"source_id": source_id, "old_skill_ids": previous, "new_skill_ids": selected,
                   "comment": payload.comment, "versions": sorted({r["version"] for r in sources}),
                   "content_changed": False, "reindex_required": False})
    return {"source_id": source_id, "old_skill_ids": previous, "skill_ids": selected,
            "content_changed": False, "reindex_required": False}
