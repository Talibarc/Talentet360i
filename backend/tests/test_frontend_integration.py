import config
import models
from database import SessionLocal
from seed_demo import seed_demo
from fastapi.testclient import TestClient
from main import app
from llm_provider import get_provider, LunaProvider

def test_demo_selector_only_explicit_synthetic_seed(secure_client):
    assert secure_client.get('/demo/identities').json() == {'provider': 'mock', 'identities': []}
    with SessionLocal.begin() as db:
        db.add(models.User(employee_id='DEMO-IMPOSTOR', full_name='Synthetic unseeded', email='unseeded@example.invalid', role='admin'))
    seeded = seed_demo()
    response = secure_client.get('/demo/identities')
    assert response.status_code == 200
    rows = response.json()['identities']
    # The normal selector intentionally hides the internal global Admin/L&D
    # identities and adds a scoped L&D identity for each function.
    assert len(rows) == 10
    assert {(r['role'], r['business_function']) for r in rows} == {
        (role, function)
        for function in ('Finance', 'DataOps')
        for role in ('ld', 'reviewer', 'manager', 'employee', 'leader')
    }
    assert len(rows) == 10
    assert all(set(r) == {'id', 'role', 'label', 'business_function'} for r in rows)
    assert all(r['label'] != 'DEMO-IMPOSTOR' for r in rows)

def test_luna_with_demo_identities_disabled_rejects_selector(secure_client, monkeypatch):
    monkeypatch.setattr(config, 'LLM_PROVIDER', 'luna')
    monkeypatch.setattr(config, 'DEMO_IDENTITIES_ENABLED', False)
    response = secure_client.get('/demo/identities')
    assert response.status_code == 403
    assert response.json()['detail'] == 'Demo identities are disabled in this environment.'
    assert secure_client.get('/me', headers={'X-Demo-User-Id': '1'}).status_code == 403

def test_luna_with_explicit_demo_access_keeps_roles_and_provider(secure_client, monkeypatch):
    seed_demo()
    monkeypatch.setattr(config, 'LLM_PROVIDER', 'luna')
    monkeypatch.setattr(config, 'DEMO_IDENTITIES_ENABLED', True)
    response = secure_client.get('/demo/identities')
    assert response.status_code == 200
    assert response.json()['provider'] == 'luna'
    assert isinstance(get_provider(), LunaProvider)
    identities = response.json()['identities']
    assert {row['role'] for row in identities} == {'ld', 'reviewer', 'manager', 'employee', 'leader'}
    assert {row['business_function'] for row in identities} == {'Finance', 'DataOps'}
    employee = next(row for row in identities if row['role'] == 'employee')
    assert secure_client.get('/data/inventory', headers={'X-Demo-User-Id': str(employee['id'])}).status_code == 403

def test_demo_selector_rejects_nonlocal():
    with TestClient(app, client=('192.0.2.1', 12345)) as client:
        assert client.get('/demo/identities').status_code == 403
