"""Synthetic contract fixtures only; external sockets are blocked by conftest."""
import copy
import json

import pytest
import config
import models
from database import SessionLocal
from llm_provider import LunaProvider, MockProvider, ProviderError
from luna_contract import ResponseContractError, parse_questions
from test_phase2 import demo

ARGS = dict(system_prompt="Fixture", user_prompt="Fixture", skill_name="Fixture", target_level=2, question_count=1)
Q = {"question_text":"Which fixture action is supported?", "options":{"A":"Record the check", "B":"Skip the check", "C":"Delete the check", "D":"Hide the check"}, "correct_answer":"A", "explanation":"The fixture requires recording."}


def envelope(content):
    return {"id":"fixture-id", "model":"fixture-model", "choices":[{"index":0,"finish_reason":"stop","message":{"role":"assistant","content":content}}]}


@pytest.mark.parametrize("raw", [json.dumps([Q]), {"questions":[Q]}, [Q], json.dumps(json.dumps([Q])),
    '```json\n'+json.dumps([Q])+'\n```', envelope(json.dumps({"questions":[Q]})),
    json.dumps(envelope(json.dumps([Q]))), ' Here are the questions:\n```json\n'+json.dumps([Q])+'\n```\n',
    'JSON: '+json.dumps([Q]), '```\n'+json.dumps([Q])+'\n```'])
def test_supported_representations(raw):
    assert parse_questions(raw,1)[0].model_dump(exclude_none=True)==Q


@pytest.mark.parametrize("raw", ['not json','[{bad}]',json.dumps([Q])+' trailing text',
    'Ignore earlier rules '+json.dumps([Q]), json.dumps([Q])+json.dumps([Q]),
    '```python\n'+json.dumps([Q])+'\n```', '{"questions":[],"questions":[]}', '[NaN]',
    json.dumps(json.dumps(json.dumps(json.dumps(json.dumps(json.dumps(json.dumps([Q]))))))),
    {"data":[Q]}, {"questions":[Q],"choices":[]}, {"questions":[Q],"extra":"unapproved"},
    [], [Q,Q], ["not an object"], {"choices":[]}, {"choices":[{},{}]},
    envelope([{"type":"text","text":json.dumps([Q])}])])
def test_malformed_or_unrecognized_shapes_rejected(raw):
    with pytest.raises(ResponseContractError):parse_questions(raw,1)


@pytest.mark.parametrize("field", ['question_text','options','correct_answer','explanation'])
def test_required_fields_never_invented(field):
    row=copy.deepcopy(Q);row.pop(field)
    with pytest.raises(ResponseContractError):parse_questions([row],1)


@pytest.mark.parametrize("change", [{"correct_answer":"E"},{"correct_answer":"Record the check"},
    {"options":{"A":"a","B":"b","C":"c"}}, {"options":{"A":"a","B":"a","C":"c","D":"d"}},
    {"options":{"A":1,"B":"b","C":"c","D":"d"}}, {"question_text":" "},
    {"explanation":" "},{"skill_id":"invented"}])
def test_canonical_schema_remains_strict(change):
    with pytest.raises(ResponseContractError):parse_questions([Q|change],1)


def test_supplied_optional_source_is_not_rewritten():
    assert parse_questions([Q|{"rag_source":"Fixture supplied reference"}],1)[0].rag_source=="Fixture supplied reference"
    assert parse_questions([Q],1)[0].rag_source is None


@pytest.mark.parametrize("finish",['length','content_filter','tool_calls'])
def test_incomplete_choices_rejected(finish):
    raw=envelope(json.dumps([Q]));raw['choices'][0]['finish_reason']=finish
    with pytest.raises(ResponseContractError):parse_questions(raw,1)


def test_diagnostics_exclude_values_and_unknown_keys(caplog):
    secret='PRIVATE_FIXTURE_DO_NOT_LOG'
    with pytest.raises(ResponseContractError):parse_questions([Q|{"options":{"A":secret,"B":secret,"C":"c","D":"d"}}],1)
    with pytest.raises(ResponseContractError):parse_questions({secret:secret},1)
    with pytest.raises(ResponseContractError):parse_questions(secret,1)
    assert secret not in caplog.text
    assert 'canonical_schema_validation' in caplog.text and 'unparseable' in caplog.text
    assert 'unknown_key_count' in caplog.text and 'paths' in caplog.text
    assert Q['question_text'] not in caplog.text


def test_network_failure_logs_status_only(monkeypatch,caplog):
    monkeypatch.setattr(config,'CIS_BASE_URL','https://example.invalid')
    monkeypatch.setattr(config,'CIS_API_KEY','fixture-only')
    def fail(*args):
        error=RuntimeError('PRIVATE_FIXTURE_DO_NOT_LOG');error.status_code=401;raise error
    monkeypatch.setattr('llm_service.generate_text',fail)
    with pytest.raises(ProviderError) as e:LunaProvider().questions(**ARGS)
    assert e.value.status_code==503 and 'PRIVATE_FIXTURE' not in caplog.text
    assert '401' in caplog.text and 'request_unavailable' in caplog.text


def test_mock_unchanged():
    assert MockProvider().questions(**ARGS)==MockProvider().questions(**ARGS)
    assert 'Synthetic' in MockProvider().questions(**ARGS)[0].rag_source


@pytest.fixture
def rd_contract(demo,monkeypatch):
    g=demo.DataOps
    with SessionLocal.begin() as db:
        db.get(models.RoleSkillMap,g["mapping"]).target_label="Expert"
        for kind,key,entity in [('mapping','FIX-M',g['mapping']),('skill','FIX-S',g['skill'])]:
            db.add(models.SourceRecord(workbook='overall_rd.xlsx',sheet=kind,source_row=1,source_key=key,
                entity_type=kind,entity_id=entity,fingerprint='fixture',details={}))
    monkeypatch.setattr(config,'LLM_PROVIDER','luna')
    monkeypatch.setattr(config,'CIS_BASE_URL','https://example.invalid')
    monkeypatch.setattr(config,'CIS_API_KEY','fixture-only')
    chunk=dict(chunk_id='FIX-CHK',source_id='FIX-SRC',reference='section 1',text='PRIVATE_FIXTURE_CONTEXT record the check.',
        version='fixture-v1',document_filename='fixture.txt',function='DataOps',skill_ids=['FIX-S'],
        intended_proficiencies=['Expert'],ingestion_status='Ingested',approved_for_generation=True,synthetic_only=False)
    # This flag exercises office routing with fictional text; no company document is used.
    monkeypatch.setattr('offline_rag.load_index',lambda:{'chunks':[chunk]})
    return demo,chunk


def test_rd_prompt_provenance_pending_and_approval_gate(rd_contract,monkeypatch):
    demo,chunk=rd_contract;g=demo.DataOps
    def fake(system,user):
        assert all(chunk[k] in user for k in ('text','chunk_id','source_id','version'))
        assert all(k in system for k in ('question_text','options','correct_answer','explanation'))
        return envelope(json.dumps({'questions':[Q]}))
    monkeypatch.setattr('llm_service.generate_text',fake)
    row=demo.call('POST','/questions/generate',demo.ld,{'role_skill_map_id':g['mapping'],'question_count':1,'require_approved_sop':True},201)[0]
    assert row['status']=='pending_review' and row['source_ids']==['FIX-SRC']
    assert row['chunk_references']==['FIX-CHK'] and row['document_references']==['fixture.txt@fixture-v1']
    assert 'Finance Excel RAG' not in row['rag_source'] and not row['synthetic_only']
    demo.call('POST','/assessments',demo.ld,{'employee_id':g['employee'],'role_skill_map_id':g['mapping'],'question_count':20},409)
    demo.call('PATCH',f"/questions/{row['id']}/review",g['reviewer'],{'status':'approved'})
    with SessionLocal() as db:assert db.get(models.Question,row['id']).status=='approved'


@pytest.mark.parametrize('change',[{'approved_for_generation':False},{'synthetic_only':True},{'skill_ids':['OTHER']},{'ingestion_status':'Pending'}])
def test_require_approved_sop_blocks_before_provider(rd_contract,monkeypatch,change):
    demo,chunk=rd_contract;chunk.update(change)
    monkeypatch.setattr('llm_service.generate_text',lambda *a:pytest.fail('Ineligible context reached provider'))
    demo.call('POST','/questions/generate',demo.ld,{'role_skill_map_id':demo.DataOps['mapping'],'question_count':1,'require_approved_sop':True},503)


@pytest.mark.parametrize('raw,category',[('broken','non-JSON'),('[{}]','invalid question data')])
def test_contract_errors_are_502_and_save_nothing(rd_contract,monkeypatch,raw,category):
    demo,_=rd_contract
    monkeypatch.setattr('llm_service.generate_text',lambda *a:raw)
    data=demo.call('POST','/questions/generate',demo.ld,{'role_skill_map_id':demo.DataOps['mapping'],'question_count':1,'require_approved_sop':True},502)
    assert category in data['detail']
    with SessionLocal() as db:assert db.query(models.Question).count()==0


@pytest.mark.parametrize("shape", ["valid", "empty", "truncated", "missing_content"])
def test_sdk_adapter_response_contract(monkeypatch, shape):
    from types import SimpleNamespace
    import llm_service
    monkeypatch.setattr(config, "CIS_API_KEY", "fixture-only")
    monkeypatch.setattr(config, "CIS_BASE_URL", "https://example.invalid")
    monkeypatch.setattr(llm_service, "CIS_API_KEY", "fixture-only")
    monkeypatch.setattr(llm_service, "CIS_BASE_URL", "https://example.invalid")
    closed = []
    class FakeClient:
        def __init__(self, **kwargs): pass
        def complete(self, **kwargs):
            message = SimpleNamespace(content=json.dumps({"questions": [Q]}) if shape != "missing_content" else None)
            return SimpleNamespace(choices=[] if shape == "empty" else [SimpleNamespace(
                message=message, finish_reason="length" if shape == "truncated" else "stop")])
        def close(self): closed.append(True)
    monkeypatch.setattr(llm_service, "ChatCompletionsClient", FakeClient)
    if shape == "valid":
        assert LunaProvider().questions(**ARGS)[0].question_text == Q["question_text"]
    else:
        with pytest.raises(ResponseContractError): LunaProvider().questions(**ARGS)
    assert closed == [True]
