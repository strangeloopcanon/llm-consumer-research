"""Database layer for persisting simulation runs.

Uses SQLAlchemy with aiosqlite for async SQLite access.
Schema is designed to be easily migratable to PostgreSQL.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, String, Text, create_engine, desc
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

Base = declarative_base()


class RunRecord(Base):
    """A single simulation run."""

    __tablename__ = "runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    label = Column(Text, nullable=True)
    status = Column(String(20), default="completed")
    request_json = Column(Text, nullable=False)
    response_json = Column(Text, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "label": self.label,
            "status": self.status,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["request"] = json.loads(self.request_json) if self.request_json else None
        result["response"] = json.loads(self.response_json) if self.response_json else None
        return result


_engine = None
_Session = None


def get_db_path() -> Path:
    """Get the path to the SQLite database file."""
    settings = get_settings()
    db_dir = Path(getattr(settings, "data_dir", ".")) / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "runs.db"


def init_db() -> None:
    """Initialize the database, creating tables if they don't exist."""
    global _engine, _Session
    db_path = get_db_path()
    _engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(_engine)
    _Session = sessionmaker(bind=_engine)


def get_session():
    """Get a database session."""
    global _Session
    if _Session is None:
        init_db()
    return _Session()


def save_run(
    request_data: Dict[str, Any],
    response_data: Dict[str, Any],
    label: Optional[str] = None,
    status: str = "completed",
) -> str:
    """Save a simulation run to the database.

    Returns the run ID.
    """
    session = get_session()
    try:
        run_id = str(uuid.uuid4())
        record = RunRecord(
            id=run_id,
            label=label,
            status=status,
            request_json=json.dumps(request_data),
            response_json=json.dumps(response_data),
        )
        session.add(record)
        session.commit()
        return run_id
    finally:
        session.close()


def list_runs(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """List simulation runs, most recent first."""
    session = get_session()
    try:
        records = (
            session.query(RunRecord)
            .order_by(desc(RunRecord.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [r.to_dict() for r in records]
    finally:
        session.close()


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific run by ID, including full request/response."""
    session = get_session()
    try:
        record = session.query(RunRecord).filter_by(id=run_id).first()
        if record is None:
            return None
        return record.to_full_dict()
    finally:
        session.close()


def delete_run(run_id: str) -> bool:
    """Delete a run by ID. Returns True if deleted, False if not found."""
    session = get_session()
    try:
        record = session.query(RunRecord).filter_by(id=run_id).first()
        if record is None:
            return False
        session.delete(record)
        session.commit()
        return True
    finally:
        session.close()


__all__ = ["init_db", "save_run", "list_runs", "get_run", "delete_run", "RunRecord"]
