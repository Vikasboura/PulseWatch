from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    # pool_size and max_overflow are only valid for non-SQLite/QueuePool
    **({"pool_size": settings.DB_POOL_SIZE, "max_overflow": settings.DB_MAX_OVERFLOW}
       if not settings.DATABASE_URL.startswith("sqlite") else {})
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
