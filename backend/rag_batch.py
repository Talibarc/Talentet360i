"""Validated multi-file upload service for the local offline RAG index."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field, model_validator

import config
from offline_rag import (INDEX_FILENAME, SUPPORTED_EXTENSIONS, RagError, chunk_segments,
                         extract_document, load_index)


class BatchMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    client_id: str = Field(min_length=1, max_length=100)
    original_filename: str = Field(min_length=1, max_length=500)
    source_id: str | None = Field(default=None, max_length=200)
    skill_ids: list[str] = Field(default_factory=list)
    approved_source_confirmed: bool = False

    @model_validator(mode="after")
    def unique_skills(self):
        self.skill_ids = sorted(set(self.skill_ids))
        return self


class BatchCandidate(BatchMapping):
    file_size: int = Field(ge=0)


class BatchValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    files: list[BatchCandidate] = Field(min_length=1)


def source_registry() -> tuple[list[dict[str, Any]], set[str]]:
    """Expose workbook metadata without reading any URL or document content."""
    from source_import import RD_FILE, source_plan

    records, _ = source_plan()
    skills = {row["source_key"] for row in records
              if row["workbook"] == RD_FILE.name and row["entity_type"] == "skill"}
    rows = []
    for row in records:
        if row["workbook"] != RD_FILE.name:
            continue
        details = row["details"]
        if row["entity_type"] == "source_metadata":
            rows.append({
                "source_id": row["source_key"], "source_title": details.get("title"),
                "source_type": details.get("source_type"), "source_owner": details.get("owner"),
                "original_reference": details.get("original_reference"), "mapped_skill_ids": [],
                "availability_status": details.get("availability_status", "Content not supplied"),
            })
        elif row["entity_type"] == "learning":
            rows.append({
                "source_id": details["resource_id"], "source_title": details.get("title"),
                "source_type": details.get("source_type"), "source_owner": details.get("owner"),
                "original_reference": details.get("original_reference"),
                "mapped_skill_ids": [details["source_skill_id"]],
                "availability_status": "Content not supplied",
            })
        elif row["entity_type"] == "question_source":
            rows.append({
                "source_id": row["source_key"], "source_title": details.get("title"),
                "source_type": "Question bank", "source_owner": "Faiza Shaikh",
                "original_reference": details.get("url"), "mapped_skill_ids": [],
                "availability_status": "Unavailable — excluded from MVP",
            })
    return sorted(rows, key=lambda item: item["source_id"]), skills


def sanitize_filename(value: str) -> str:
    name = Path(value.replace("\\", "/")).name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem).strip("._") or "document"
    extension = Path(name).suffix.casefold()
    return (stem[:120] + extension)


def _validation(candidate: BatchCandidate, registry: dict[str, dict], skills: set[str]) -> dict[str, Any]:
    sanitized = sanitize_filename(candidate.original_filename)
    extension = Path(sanitized).suffix.casefold()
    result = {**candidate.model_dump(), "sanitized_filename": sanitized, "validation_status": "Ready", "message": None}
    if extension not in SUPPORTED_EXTENSIONS:
        result.update(validation_status="Failed", message=f"Unsupported file extension: {extension or '(none)'}")
    elif candidate.file_size > config.RAG_MAX_FILE_BYTES:
        result.update(validation_status="Failed", message="File exceeds configured size limit")
    elif candidate.source_id not in registry:
        result.update(validation_status="Pending source validation", message="Source_ID is not registered; content cannot support generation")
    elif registry[candidate.source_id]["availability_status"] == "Unavailable — excluded from MVP":
        result.update(validation_status="Failed", message="Source is excluded from the MVP")
    elif not candidate.skill_ids or not set(candidate.skill_ids).issubset(skills):
        result.update(validation_status="Mapping required", message="Select one or more existing Skill_ID values")
    elif not candidate.approved_source_confirmed:
        result.update(validation_status="Pending source validation", message="Admin/L&D approval confirmation is required")
    return result


def validate_batch(candidates: list[BatchCandidate]) -> dict[str, Any]:
    rows, skills = source_registry()
    registry = {row["source_id"]: row for row in rows}
    total = sum(candidate.file_size for candidate in candidates)
    batch_error = None
    if len(candidates) > config.RAG_MAX_BATCH_FILES:
        batch_error = f"Batch exceeds maximum of {config.RAG_MAX_BATCH_FILES} files"
    elif total > config.RAG_MAX_BATCH_BYTES:
        batch_error = f"Batch exceeds maximum total size of {config.RAG_MAX_BATCH_BYTES} bytes"
    results = [_validation(candidate, registry, skills) for candidate in candidates]
    if batch_error:
        for result in results:
            result.update(validation_status="Failed", message=batch_error)
    return {"selected_count": len(candidates), "total_bytes": total, "batch_error": batch_error, "files": results}


def _save_index(index: dict[str, Any]) -> None:
    config.RAG_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    temporary = config.RAG_INDEX_DIR / (INDEX_FILENAME + ".tmp")
    temporary.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(config.RAG_INDEX_DIR / INDEX_FILENAME)


async def upload_and_ingest(files: list[UploadFile], mappings: list[BatchMapping]) -> dict[str, Any]:
    if len(files) != len(mappings):
        raise RagError("Every uploaded file requires one mapping row")
    candidates = []
    contents = []
    for upload, mapping in zip(files, mappings):
        if upload.filename != mapping.original_filename:
            raise RagError("Uploaded filename does not match its mapping row")
        content = await upload.read()
        contents.append(content)
        candidates.append(BatchCandidate(**mapping.model_dump(), file_size=len(content)))
    validation = validate_batch(candidates)
    index = load_index()
    index.setdefault("sources", []); index.setdefault("chunks", [])
    indexed_hashes = {source.get("content_hash") for source in index["sources"]
                      if source.get("content_hash") and source.get("ingestion_status") == "Ingested"}
    seen_hashes: set[str] = set()
    upload_dir = config.RAG_INDEX_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    registry_rows, _ = source_registry(); registry = {row["source_id"]: row for row in registry_rows}
    outcomes = []

    for validated, content in zip(validation["files"], contents):
        status = validated["validation_status"]
        outcome = {**validated, "content_hash": None, "internal_storage_name": None, "chunk_count": 0}
        if status in {"Failed", "Mapping required"}:
            outcomes.append(outcome); continue
        digest = hashlib.sha256(content).hexdigest()
        extension = Path(validated["sanitized_filename"]).suffix.casefold()
        internal_name = f"{digest[:32]}{extension}"
        outcome.update(content_hash=digest, version=digest[:12], internal_storage_name=internal_name)
        if digest in indexed_hashes or digest in seen_hashes:
            outcome.update(validation_status="Duplicate skipped", message="Identical content hash already indexed")
            outcomes.append(outcome); continue
        seen_hashes.add(digest)
        stored = upload_dir / internal_name
        stored.write_bytes(content)
        if status == "Pending source validation":
            index["sources"].append({
                "source_id": validated.get("source_id") or "UNREGISTERED", "title": None,
                "source_type": None, "owner": None, "original_reference": None,
                "skill_ids": validated["skill_ids"], "original_filename": validated["original_filename"],
                "internal_storage_name": internal_name, "content_hash": digest, "version": digest[:12],
                "availability_status": "Available locally", "ingestion_status": "Pending source validation",
                "chunk_count": 0, "synthetic_only": False, "limitation": validated["message"],
            })
            outcomes.append(outcome); continue
        try:
            segments = extract_document(stored)
            chunks = chunk_segments(segments, validated["source_id"], digest)
            meta = registry[validated["source_id"]]
            timestamp = datetime.now(timezone.utc).isoformat()
            for chunk in chunks:
                chunk.update(source_id=validated["source_id"], source_title=meta["source_title"],
                    skill_ids=validated["skill_ids"], document_filename=validated["original_filename"],
                    internal_storage_name=internal_name, file_content_hash=digest, version=digest[:12], synthetic_only=False,
                    function="DataOps", role_bands=[], intended_proficiencies=[],
                    approved_for_generation=True, ingestion_status="Ingested", ingested_at=timestamp)
            index["chunks"].extend(chunks)
            index["sources"].append({
                "source_id": validated["source_id"], "title": meta["source_title"],
                "source_type": meta["source_type"], "owner": meta["source_owner"],
                "original_reference": meta["original_reference"], "skill_ids": validated["skill_ids"],
                "original_filename": validated["original_filename"], "internal_storage_name": internal_name,
                "content_hash": digest, "version": digest[:12],
                "availability_status": "Ingested", "ingestion_status": "Ingested",
                "chunk_count": len(chunks), "synthetic_only": False, "limitation": None,
            })
            indexed_hashes.add(digest)
            outcome.update(validation_status="Ingested", message=None, chunk_count=len(chunks))
        except RagError as error:
            stored.unlink(missing_ok=True)
            outcome.update(validation_status="Failed", message=str(error))
        outcomes.append(outcome)
    index["created_at"] = datetime.now(timezone.utc).isoformat()
    _save_index(index)
    counts = {status: sum(row["validation_status"] == status for row in outcomes) for status in
              ("Ingested", "Duplicate skipped", "Pending source validation", "Failed", "Mapping required")}
    return {"selected_count": len(outcomes), "successfully_ingested": counts["Ingested"],
            "duplicates_skipped": counts["Duplicate skipped"],
            "pending_validation": counts["Pending source validation"] + counts["Mapping required"],
            "failed": counts["Failed"], "files": outcomes}
