from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List
import json

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from git import InvalidGitRepositoryError, Repo
import typer

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

def get_pending_changes() -> List[Change]:
    """Get all pending changes from the database."""
    with get_db_session() as session:
        return session.query(Change).filter(Change.status == ChangeStatus.PENDING).all()

def update_change_status(commit_hash: str, status: ChangeStatus) -> Optional[Change]:
    with get_db_session() as session:
        change = session.query(Change).filter(Change.commit_hash == commit_hash).first()
        if change:
            change.status = status
            session.commit()
        return change

def update_all_pending_changes(status: ChangeStatus) -> int:
    """Update all pending changes to the specified status. Returns the number of changes updated."""
    with get_db_session() as session:
        result = session.query(Change).filter(Change.status == ChangeStatus.PENDING).update(
            {Change.status: status}
        )
        session.commit()
        return result

def require_git_repo():
    """Verify the user is inside a Git repository."""
    try:
        Repo('.', search_parent_directories=True)
    except InvalidGitRepositoryError:
        typer.secho("❌ Not inside a Git repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

def get_stageflow() -> List[str]:
    """Get the stageflow configuration from .gitstage_config.json."""
    config = Path(".gitstage_config.json")
    if config.exists():
        return json.loads(config.read_text())["stages"]
    return ["dev", "testing", "main"]

def save_stageflow(stages: List[str]):
    """Save the stageflow configuration to .gitstage_config.json."""
    config = Path(".gitstage_config.json")
    config.write_text(json.dumps({"stages": stages}, indent=2))
