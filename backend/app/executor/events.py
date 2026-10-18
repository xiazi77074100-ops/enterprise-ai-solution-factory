"""Append-only run trace with a hash chain (run_execution.md §7, contracts/events.schema.json).

Events carry hashes, counts, codes and versions only: never document text, extracted values, corrected values
or secrets (T09). Every event is validated against the frozen event contract before it is stored.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog.validation import content_sha256, schema_issues
from app.executor.models import Run, RunEvent

Scalar = str | int | float | bool | None


class EventContractError(RuntimeError):
    """An event that does not match contracts/events.schema.json (a programming error, never user input)."""


def append_event(
    db: Session,
    run: Run,
    event_type: str,
    status: str,
    *,
    actor: tuple[str, str] = ("system", "executor"),
    node_id: str | None = None,
    capability_version_id: uuid.UUID | None = None,
    metadata: dict[str, Scalar] | None = None,
) -> RunEvent:
    """Adds the next event of the run's stream to the session (the caller commits)."""
    last = db.execute(
        select(RunEvent).where(RunEvent.run_id == run.id).order_by(RunEvent.seq.desc()).limit(1)
    ).scalar_one_or_none()
    event: dict[str, Any] = {
        "schema_version": "1",
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "trace_id": run.trace_id,
        "run_id": str(run.id),
        "node_id": node_id,
        "project_id": str(run.project_id),
        "capability_version_id": str(capability_version_id) if capability_version_id else None,
        "actor": {"type": actor[0], "id": actor[1]},
        "status": status,
        "execution_mode": run.execution_mode,
        "redacted_metadata": metadata or {},
        "prev_event_hash": last.event_hash if last else None,
    }
    issues = schema_issues("events", event)
    if issues:
        raise EventContractError(f"{event_type}: {issues[0].code} at {issues[0].location}")
    row = RunEvent(run_id=run.id, seq=(last.seq + 1) if last else 1, event=event, event_hash=content_sha256(event))
    db.add(row)
    db.flush()
    return row


def verify_chain(db: Session, run_id: uuid.UUID) -> bool:
    """True if every stored event hashes to its event_hash and links to the previous one."""
    previous: str | None = None
    for row in db.execute(select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.seq)).scalars():
        if row.event.get("prev_event_hash") != previous or content_sha256(row.event) != row.event_hash:
            return False
        previous = row.event_hash
    return True


def count_events(db: Session, run_id: uuid.UUID) -> int:
    return db.execute(select(func.count()).where(RunEvent.run_id == run_id)).scalar_one()
