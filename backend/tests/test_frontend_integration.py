import config
import models
from database import SessionLocal
from seed_demo import seed_demo
from fastapi.testclient import TestClient
from main import app

def test_demo_selector_only_explicit_synthetic_seed(secure_client):
    assert secure_client.get('/demo/identities').json() == {'provider': 'mock', 'identities': []}
    with SessionLocal.begin() as db:
        db.add(models.User(employee_id='DEMO-IMPOSTOR', full_name='Synthetic unseeded', email='unseeded@example.invalid', role='admin'))
    seeded = seed_demo()
    response = secure_client.get('/demo/identities')
    assert response.status_code == 200
    rows = response.json()['identities']
    assert {r['id'] for r in rows} == {r['id'] for r in seeded['identities']}
    assert len(rows) == 10
    assert all(set(r) == {'id', 'role', 'label', 'business_function'} for r in rows)
    assert all(r['label'] != 'DEMO-IMPOSTOR' for r in rows)

def test_demo_selector_requires_mock(secure_client, monkeypatch):
    monkeypatch.setattr(config, 'LLM_PROVIDER', 'luna')
    assert secure_client.get('/demo/identities').status_code == 403

def test_demo_selector_rejects_nonlocal():
    with TestClient(app, client=('192.0.2.1', 12345)) as client:
        assert client.get('/demo/identities').status_code == 403
