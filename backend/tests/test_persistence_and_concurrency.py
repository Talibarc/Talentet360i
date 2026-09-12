import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, SessionLocal, get_db
from main import app
import models
from test_phase2 import demo, scored, decide


def test_additive_upgrade_and_restart_preserve_existing_data(tmp_path):
    database_file = tmp_path / "upgrade.sqlite"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("LUNA_", "CIS_"))}
    env.update(LLM_PROVIDER="mock", PYTHON_DOTENV_DISABLED="1", DATABASE_URL=f"sqlite:///{database_file.as_posix()}")
    backend = Path(__file__).resolve().parents[1]
    # Freeze the original user table shape independently of the current Git HEAD.
    # Other tables are absent, exercising additive creation on a legacy DB.
    script = (
        "import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); "
        "db.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, employee_id VARCHAR(50) UNIQUE NOT NULL, "
        "full_name VARCHAR(100) NOT NULL, email VARCHAR(150) UNIQUE NOT NULL, role VARCHAR(30) NOT NULL, "
        "department VARCHAR(100), xp_points INTEGER NOT NULL, created_at DATETIME)'); "
        "db.execute(\"INSERT INTO users VALUES (1,'LEGACY-SYNTHETIC','Synthetic Legacy',"
        "'legacy@example.invalid','employee',NULL,17,NULL)\"); db.commit(); db.close()"
    )
    subprocess.run([sys.executable, "-B", "-c", script, str(database_file)], text=True,
                   cwd=backend, env=env, capture_output=True, check=True)
    verify = (
        "from seed_demo import seed_demo; first=seed_demo(); second=seed_demo(); assert first==second; "
        "from database import SessionLocal; import models; db=SessionLocal(); "
        "legacy=db.query(models.User).filter_by(employee_id='LEGACY-SYNTHETIC').one(); "
        "assert legacy.xp_points==17; assert db.query(models.User).count()==11; "
        "print(db.query(models.AuditEvent).count())"
    )
    first = subprocess.run([sys.executable, "-B", "-c", verify], cwd=backend, env=env,
                           capture_output=True, text=True, check=True)
    restarted = subprocess.run([sys.executable, "-B", "-c", verify], cwd=backend, env=env,
                               capture_output=True, text=True, check=True)
    assert first.stdout == restarted.stdout
    assert int(first.stdout.strip()) > 0


def test_concurrent_submission_is_exactly_once(demo, tmp_path):
    # Copy synthetic test data to a file DB so each request gets its own connection.
    file_engine = create_engine(f"sqlite:///{(tmp_path / 'concurrency.sqlite').as_posix()}",
                                connect_args={"check_same_thread": False, "timeout": 20})
    Base.metadata.create_all(file_engine)
    with SessionLocal() as db, file_engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            rows = db.execute(table.select()).mappings().all()
            if rows:
                connection.execute(table.insert(), [dict(row) for row in rows])
    factory = sessionmaker(bind=file_engine)
    def isolated_db():
        with factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
    app.dependency_overrides[get_db] = isolated_db
    try:
        g = demo.Finance
        q = demo.call("POST", "/questions/generate", g["reviewer"], {"role_skill_map_id": g["mapping"], "question_count": 1}, 201)[0]
        demo.call("PATCH", f"/questions/{q['id']}/review", g["reviewer"], {"status": "approved"})
        a = demo.call("POST", "/assessments", g["manager"], {"employee_id": g["employee"],
            "role_skill_map_id": g["mapping"], "question_count": 1}, 201)
        def submit():
            return demo.client.post(f"/assessments/{a['id']}/submit", headers={"X-Demo-User-Id": str(g["employee"])},
                json={"answers": [{"question_id": q["id"], "selected_answer": q["correct_answer"]}]}).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            codes = list(executor.map(lambda _: submit(), range(2)))
        assert codes.count(200) == 1 and all(c in {200, 400, 409} for c in codes)
        with factory() as db:
            assert db.query(models.XpAward).filter_by(employee_id=g["employee"], source_key=f"assessment:{a['id']}").count() == 1
            assert db.query(models.AuditEvent).filter_by(action="assessment.submitted", entity_id=a["id"]).count() == 1
            assert db.get(models.User, g["employee"]).xp_points == 10
    finally:
        app.dependency_overrides.pop(get_db, None)
        file_engine.dispose()
