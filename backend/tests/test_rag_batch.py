import json

import config
import rag_batch


def setup_registry(monkeypatch, tmp_path):
    registry = [{"source_id":"SRC_A","source_title":"Synthetic registered source","source_type":"Training",
        "source_owner":"Test owner","original_reference":None,"mapped_skill_ids":["RD_A"],"availability_status":"Content not supplied"},
        {"source_id":"SRC_AMBIG","source_title":"Ambiguous test source","source_type":"Training",
        "source_owner":"Test owner","original_reference":None,"mapped_skill_ids":["RD_A","RD_B"],"availability_status":"Content not supplied"}]
    monkeypatch.setattr(rag_batch,"source_registry",lambda:(registry,{"RD_A","RD_B"}))
    monkeypatch.setattr(config,"RAG_INDEX_DIR",tmp_path/"index")
    monkeypatch.setattr(config,"RAG_MAX_BATCH_FILES",10)
    monkeypatch.setattr(config,"RAG_MAX_FILE_BYTES",1000)
    monkeypatch.setattr(config,"RAG_MAX_BATCH_BYTES",5000)


def row(name, source="SRC_A", skills=None, approved=True, client="1"):
    return {"client_id":client,"original_filename":name,"source_id":source,
            "skill_ids":skills if skills is not None else ["RD_A"],"approved_source_confirmed":approved}


def upload(client, specs, mappings):
    return client.post("/rag/batch/upload", files=[("files",(name,data,mime)) for name,data,mime in specs],
                       data={"metadata":json.dumps(mappings)})


def test_successful_multi_file_upload_and_multiple_skills(client, monkeypatch, tmp_path):
    setup_registry(monkeypatch,tmp_path)
    response=upload(client,[("one.txt",b"first approved synthetic text","text/plain"),("two.txt",b"second approved synthetic text","text/plain")],
        [row("one.txt",skills=["RD_A","RD_B"]),row("two.txt",client="2")])
    assert response.status_code == 200, response.text
    data=response.json(); assert data["selected_count"] == 2 and data["successfully_ingested"] == 2
    assert data["files"][0]["skill_ids"] == ["RD_A","RD_B"]
    assert all(item["internal_storage_name"] != item["original_filename"] for item in data["files"])


def test_mixed_failure_does_not_rollback_success(client, monkeypatch, tmp_path):
    setup_registry(monkeypatch,tmp_path)
    response=upload(client,[("good.txt",b"valid retained content","text/plain"),("bad.pdf",b"not a pdf","application/pdf")],
                    [row("good.txt"),row("bad.pdf",client="2")])
    data=response.json(); assert data["successfully_ingested"] == 1 and data["failed"] == 1
    index=json.loads((tmp_path/"index"/"index.json").read_text())
    assert any(source["original_filename"] == "good.txt" for source in index["sources"])


def test_duplicate_content_different_names_skipped(client, monkeypatch, tmp_path):
    setup_registry(monkeypatch,tmp_path); content=b"identical content hash"
    data=upload(client,[("a.txt",content,"text/plain"),("different.txt",content,"text/plain")],
                [row("a.txt"),row("different.txt",client="2")]).json()
    assert data["successfully_ingested"] == 1 and data["duplicates_skipped"] == 1


def test_ambiguous_mapping_and_unregistered_source_are_independent(client, monkeypatch, tmp_path):
    setup_registry(monkeypatch,tmp_path)
    candidates={"files":[{**row("a.txt",source="SRC_AMBIG",skills=[]),"file_size":10},
                         {**row("new.txt",source="NEW_SOURCE",skills=["RD_A"],client="2"),"file_size":10}]}
    data=client.post("/rag/batch/validate",json=candidates).json()
    assert [item["validation_status"] for item in data["files"]] == ["Mapping required","Pending source validation"]


def test_batch_limits(client, monkeypatch, tmp_path):
    setup_registry(monkeypatch,tmp_path); monkeypatch.setattr(config,"RAG_MAX_BATCH_FILES",1)
    payload={"files":[{**row("a.txt"),"file_size":1},{**row("b.txt",client="2"),"file_size":1}]}
    data=client.post("/rag/batch/validate",json=payload).json()
    assert data["batch_error"] and all(item["validation_status"] == "Failed" for item in data["files"])
    monkeypatch.setattr(config,"RAG_MAX_BATCH_FILES",10); monkeypatch.setattr(config,"RAG_MAX_BATCH_BYTES",1)
    data=client.post("/rag/batch/validate",json=payload).json()
    assert "total size" in data["batch_error"]


def test_unregistered_upload_stays_pending_without_chunks(client, monkeypatch, tmp_path):
    setup_registry(monkeypatch,tmp_path)
    data=upload(client,[("new.txt",b"unregistered content","text/plain")],
                [row("new.txt",source="NEW_SOURCE")]).json()
    assert data["pending_validation"] == 1 and data["successfully_ingested"] == 0
    index=json.loads((tmp_path/"index"/"index.json").read_text())
    assert index["chunks"] == [] and index["sources"][0]["ingestion_status"] == "Pending source validation"


def test_unauthorized_bulk_upload(secure_client):
    response=upload(secure_client,[("a.txt",b"content","text/plain")],[row("a.txt")])
    assert response.status_code == 401
