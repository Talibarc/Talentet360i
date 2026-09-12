import os
import socket

# Apply before importing config/main: never read secrets or touch the application DB.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import config
import learning_service
from database import Base, engine
from main import app


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LLM_PROVIDER", "mock")
    monkeypatch.setattr(learning_service, "FINANCE_FILE", tmp_path / "finance.xlsx")
    monkeypatch.setattr(learning_service, "RD_FILE", tmp_path / "dataops.xlsx")

    original_connect = socket.socket.connect

    def no_network(sock, address):
        # Windows asyncio creates a loopback socket pair for its event loop.
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return original_connect(sock, address)
        raise AssertionError("Tests must not use external network connections")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def seeded(client):
    def create(path, data):
        response = client.post(path, json=data)
        assert response.status_code == 201, response.text
        return response.json()

    role = create("/roles", dict(role_code="SYNTH", role_name="Synthetic Analyst", business_function="Finance"))
    skill = create("/skills", dict(name="Synthetic Reconciliation", description="Synthetic fixture only"))
    mapping = create("/role-skill-maps", dict(role_id=role["id"], skill_id=skill["id"], target_level=3))
    user = create("/users", dict(employee_id="SYNTH-001", full_name="Synthetic Employee", email="synthetic@example.invalid"))
    return dict(role=role, skill=skill, mapping=mapping, user=user)


@pytest.fixture
def learning_workbooks():
    # These fixtures are fictional and are written only in pytest's temporary directory.
    def write(path, sheets, header_row):
        workbook = Workbook()
        workbook.remove(workbook.active)
        for name, rows in sheets.items():
            ws = workbook.create_sheet(name)
            for _ in range(header_row - 1):
                ws.append([])
            for row in rows:
                ws.append(row)
        workbook.save(path)
        workbook.close()

    write(learning_service.FINANCE_FILE, {
        "Skill_Master": [["skill_id", "skill"], ["SYN-S1", "Synthetic Reconciliation"]],
        "Training_Catalogue": [["course_id", "course_title"], ["SYN-C1", "Synthetic Practice Resource"]],
        "Training_Skill_Map": [["skill_id", "course_id", "level_group", "mapping_confidence"],
                               ["SYN-S1", "SYN-C1", "Supplied scope", "Synthetic fixture"],
                               ["MISSING-ID", "SYN-C1", "", ""]],
    }, 3)
    write(learning_service.RD_FILE, {
        "Skill Master": [["Skill_ID", "Skill"], ["SYN-D1", "Synthetic Pipeline"]],
        "SOP & Learning Mapping": [["Skill_ID", "Reference title", "Primary URL", "Review status"],
                                   ["SYN-D1", "Synthetic Pipeline Resource", "https://example.invalid/learning", "Fixture only"]],
    }, 4)
