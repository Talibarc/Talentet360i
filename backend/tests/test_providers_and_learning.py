import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

import config
import learning_service
from llm_provider import get_provider, LunaProvider, MockProvider, ProviderError
from schemas import GeneratedQuestion, RoleSkillMapCreate, TniNarrative


QUESTION_ARGS = dict(system_prompt="Synthetic", user_prompt="Synthetic", skill_name="Synthetic",
                     target_level=2, question_count=1)


def test_invalid_question_options():
    with pytest.raises(ValidationError):
        GeneratedQuestion(question_text="Synthetic", options={"X": "Wrong"}, correct_answer="A", explanation="Synthetic")
    assert RoleSkillMapCreate(role_id=1, skill_id=1).is_expected is False


def test_luna_calls_preserved_adapter(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "luna")
    monkeypatch.setattr(config, "CIS_BASE_URL", "https://example.invalid")
    monkeypatch.setattr(config, "CIS_API_KEY", "synthetic-placeholder")
    import llm_service
    question = MockProvider().questions(**QUESTION_ARGS)[0].model_dump()
    calls = []
    def fake_generate(system, user):
        calls.append((system, user))
        return json.dumps([question])
    monkeypatch.setattr(llm_service, "generate_text", fake_generate)
    assert isinstance(get_provider(), LunaProvider)
    assert get_provider().questions(**QUESTION_ARGS)[0].rag_source == question["rag_source"]
    assert calls == [("Synthetic", "Synthetic")]
    detail = TniNarrative(summary="Synthetic", development_focus="Review", next_steps=["Review"],
                          recommended_resource_ids=[], limitations=["Synthetic fixture"])
    monkeypatch.setattr(llm_service, "generate_text", lambda *args: detail.model_dump_json())
    monkeypatch.setattr(llm_service, "generate_text", lambda *args: pytest.fail("TNI must be local"))
    assert get_provider().tni({"skill_name":"Synthetic", "current_level":1, "target_level":2, "skill_gap":1}, []).recommended_resource_ids == []


@pytest.mark.parametrize("response", ["not json", "[]", '[{"question_text":"Incomplete"}]'])
def test_luna_invalid_output_is_safe(monkeypatch, response):
    monkeypatch.setattr(config, "CIS_BASE_URL", "https://example.invalid")
    monkeypatch.setattr(config, "CIS_API_KEY", "synthetic-placeholder")
    monkeypatch.setattr("llm_service.generate_text", lambda *args: response)
    with pytest.raises(ProviderError, match="invalid question data|non-JSON or unparseable"):
        LunaProvider().questions(**QUESTION_ARGS)


def test_luna_missing_credentials_safe_http_error(client, seeded, monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "luna")
    monkeypatch.setattr(config, "CIS_BASE_URL", "")
    monkeypatch.setattr("question_service.build_finance_rag_context", lambda *args: "Synthetic source")
    response = client.post("/questions/generate", json={"role_skill_map_id": seeded["mapping"]["id"]})
    assert response.status_code == 409
    assert "validated source mapping" in response.json()["detail"]


def test_dotenv_only_provider_switch(tmp_path):
    # Route the existing dotenv loader to a temporary synthetic config file.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("LUNA_", "CIS_")) and k not in {"LLM_PROVIDER", "DEMO_IDENTITIES_ENABLED", "PYTHON_DOTENV_DISABLED"}}
    path = tmp_path / ".env"
    script = (
        "import dotenv,sys; original=dotenv.load_dotenv; "
        "dotenv.load_dotenv=lambda _:original(sys.argv[1]); "
        "import config; from llm_provider import get_provider; "
        "print(get_provider().name); "
        "assert config.CIS_BASE_URL == 'https://example.invalid'; "
        "assert config.CIS_MODEL == 'synthetic-model'; "
        "assert config.CIS_API_KEY == 'synthetic-placeholder'; "
        "assert config.DEMO_IDENTITIES_ENABLED == (config.LLM_PROVIDER == 'mock')"
    )
    for provider in ("mock", "luna"):
        path.write_text(f"LLM_PROVIDER={provider}\nLUNA_BASE_URL=https://example.invalid\n"
                        "LUNA_MODEL=synthetic-model\nLUNA_API_KEY=synthetic-placeholder\n", encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", "-c", script, str(path)],
                                cwd=Path(__file__).resolve().parents[1], env=env,
                                capture_output=True, text=True, check=True)
        assert result.stdout.strip() == provider


def test_dotenv_can_enable_demo_without_changing_luna_provider(tmp_path):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("LUNA_", "CIS_")) and k not in {"LLM_PROVIDER", "DEMO_IDENTITIES_ENABLED", "PYTHON_DOTENV_DISABLED"}}
    path = tmp_path / ".env"
    path.write_text("LLM_PROVIDER=luna\nDEMO_IDENTITIES_ENABLED=true\n", encoding="utf-8")
    script = ("import dotenv,sys; original=dotenv.load_dotenv; "
              "dotenv.load_dotenv=lambda _:original(sys.argv[1]); import config; "
              "from llm_provider import get_provider,LunaProvider; "
              "assert config.DEMO_IDENTITIES_ENABLED is True; "
              "assert config.LLM_PROVIDER == 'luna'; assert isinstance(get_provider(),LunaProvider)")
    subprocess.run([sys.executable, "-B", "-c", script, str(path)],
                   cwd=Path(__file__).resolve().parents[1], env=env,
                   capture_output=True, text=True, check=True)


def test_mock_without_azure_imports():
    script = (
        "import builtins; original=builtins.__import__; "
        "exec('def guarded(name, *args, **kwargs):\\n"
        " if name.startswith(\"azure\") or name == \"llm_service\": raise AssertionError(\"Azure import in mock\")\\n"
        " return original(name, *args, **kwargs)'); "
        "builtins.__import__=guarded; from question_service import generate_question_drafts; "
        "assert len(generate_question_drafts('Synthetic','Synthetic',2,'Level 2','Synthetic',2)) == 2"
    )
    subprocess.run([sys.executable, "-B", "-c", script],
                   cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True, text=True)


@pytest.mark.parametrize("fail", [False, True])
def test_preserved_luna_transport_contract(monkeypatch, fail):
    import llm_service
    from types import SimpleNamespace
    monkeypatch.setattr(llm_service, "CIS_API_KEY", "synthetic-placeholder")
    monkeypatch.setattr(llm_service, "CIS_BASE_URL", "https://example.invalid")
    monkeypatch.setattr(llm_service, "CIS_MODEL", "synthetic-model")
    observed = {}
    class FakeClient:
        def __init__(self, **kwargs):
            observed["endpoint"] = kwargs["endpoint"]
        def complete(self, **kwargs):
            assert kwargs["headers"]["Authorization"] == "Bearer synthetic-placeholder"
            assert kwargs["model"] == "synthetic-model"
            if fail:
                raise RuntimeError("Synthetic failure")
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Synthetic result"))])
        def close(self):
            observed["closed"] = True
    monkeypatch.setattr(llm_service, "ChatCompletionsClient", FakeClient)
    if fail:
        with pytest.raises(RuntimeError, match="Synthetic failure"):
            llm_service.generate_text("Synthetic", "Synthetic")
    else:
        assert llm_service.generate_text("Synthetic", "Synthetic") == "Synthetic result"
    assert observed == {"endpoint": "https://example.invalid", "closed": True}


def test_learning_exact_joins(learning_workbooks):
    resources, _ = learning_service.get_learning_resources("Synthetic Reconciliation", "Finance")
    assert len(resources) == 1 and resources[0].source_skill_id == "SYN-S1"
    resources, _ = learning_service.get_learning_resources("Synthetic Pipeline", "DataOps")
    assert len(resources) == 1 and resources[0].url == "https://example.invalid/learning"
    assert resources[0].mapping_row == 5
    for name, function in [("Synthetic", "Finance"), ("MISSING-ID", "Finance"),
                           ("Synthetic Pipeline", "Finance"), ("Synthetic Pipeline", "Unknown")]:
        assert learning_service.get_learning_resources(name, function)[0] == []


def test_broken_or_ambiguous_course_mapping(monkeypatch):
    rows = {
        "Skill_Master": [(4, {"skill_id": "SYN-S1", "skill": "Synthetic"})],
        "Training_Catalogue": [],
        "Training_Skill_Map": [(4, {"skill_id": "SYN-S1", "course_id": "SYN-C1"})],
    }
    monkeypatch.setattr(learning_service, "_rows", lambda path, sheet, header: rows[sheet])
    assert learning_service.get_learning_resources("Synthetic", "Finance")[0] == []
    rows["Training_Catalogue"] = [(4, {"course_id": "SYN-C1", "course_title": "Synthetic A"}),
                                  (5, {"course_id": "SYN-C1", "course_title": "Synthetic B"})]
    assert learning_service.get_learning_resources("Synthetic", "Finance")[0] == []


def test_provider_cannot_invent_tni_resource(client, seeded, monkeypatch):
    from test_workflows import generate, approve, assign, submit
    questions = generate(client, seeded, 1)
    approve(client, questions)
    submit(client, assign(client, seeded, 1), questions, 1)
    def invented(self, facts, resources):
        return TniNarrative(summary="Synthetic", development_focus="Review", next_steps=["Review"],
                            recommended_resource_ids=["invented"], limitations=[])
    monkeypatch.setattr(MockProvider, "tni", invented)
    response = client.get(f"/users/{seeded['user']['id']}/tni")
    assert response.status_code == 200
    assert response.json()["skill_gaps"][0]["detail"]["recommended_resource_ids"] == []
