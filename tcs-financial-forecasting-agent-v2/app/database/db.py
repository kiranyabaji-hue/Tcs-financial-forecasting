from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={"charset": "utf8mb4"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def init_db():
    from app.database import models  # register models
    Base.metadata.create_all(bind=engine)

def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
