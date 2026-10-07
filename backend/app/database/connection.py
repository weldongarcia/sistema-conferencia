from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import configuracao

# Lida do ambiente (DATABASE_URL). Ver app/core/config.py.
engine = create_engine(configuracao.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 🔥 BASE (ESSENCIAL)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()