from pathlib import Path

from sqlalchemy import create_engine
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
    finally:
        db.close()
