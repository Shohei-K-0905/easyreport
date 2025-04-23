import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database URL from environment or default to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")

# SQLAlchemy engine and session
engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    # Import all models to ensure they are registered with Base
    import models  # noqa
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()
    print("Database tables created")
