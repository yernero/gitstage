from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

class ChangeStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Base(DeclarativeBase):
    pass

class Change(Base):
    __tablename__ = "changes"

    id = Column(Integer, primary_key=True)
    commit_hash = Column(String, unique=True)
    summary = Column(String)
    test_plan = Column(String)
    status = Column(SQLEnum(ChangeStatus), default=ChangeStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def get_db_session() -> Session:
    db_path = Path.home() / ".gitstage" / "changes.db"
    db_path.parent.mkdir(exist_ok=True)
    
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def record_change(
    commit_hash: str,
    summary: str,
    test_plan: str,
    status: ChangeStatus = ChangeStatus.PENDING
) -> Change:
    with get_db_session() as session:
        change = Change(
            commit_hash=commit_hash,
            summary=summary,
            test_plan=test_plan,
            status=status
        )
        session.add(change)
        session.commit()
        return change

def get_change(commit_hash: str) -> Optional[Change]:
    with get_db_session() as session:
        return session.query(Change).filter(Change.commit_hash == commit_hash).first()

def update_change_status(commit_hash: str, status: ChangeStatus) -> Optional[Change]:
    with get_db_session() as session:
        change = session.query(Change).filter(Change.commit_hash == commit_hash).first()
        if change:
            change.status = status
            session.commit()
        return change
