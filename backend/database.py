from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool
from config import DATABASE_URL

BACKEND_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BACKEND_DIR / "talent360i.db"
 
 
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    **({"poolclass": StaticPool} if DATABASE_URL == "sqlite:///:memory:" else {}),
)


@event.listens_for(engine, "connect")
def sqlite_integrity(connection, record):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.close()
 
 
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)
 
 
class Base(DeclarativeBase):
    pass
 
 
def get_db():
    db = SessionLocal()
 
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
