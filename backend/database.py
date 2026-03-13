"""SQLite database setup for PurNi Menu."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Use writable path: /tmp on Render (ephemeral), else current dir
DATA_DIR = os.environ.get("DATA_DIR", "/tmp" if os.environ.get("RENDER") else ".")
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'purni_menu.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables if they don't exist."""
    from backend.models import MenuItem, Week  # noqa: F401
    Base.metadata.create_all(bind=engine)
