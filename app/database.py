from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.paths import APP_ROOT

DATABASE_URL = f"sqlite:///{(APP_ROOT / 'time_tracker.db').as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
