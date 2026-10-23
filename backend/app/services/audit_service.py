from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.entities import AuditLog
from app.core.security import compute_audit_hash, canonical_json


def _format_time(dt: Any) -> str:
    if isinstance(dt, str):
        return dt
    if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def record_audit_event(
    db: Session,
    actor_id: Optional[str],
    actor_role: Optional[str],
    action: str,
    target_type: str,
    target_id: Optional[str] = None,
    details_json: Optional[Dict[str, Any]] = None,
    event_time: Optional[datetime] = None
) -> AuditLog:
    """
    Append an immutable event to the hash-chained audit log.
    hash = SHA256(prev_hash + canonical_json(event_payload))
    """
    if details_json is None:
        details_json = {}
    if event_time is None:
        event_time = datetime.now(timezone.utc)

    # Get the latest entry to link the hash chain
    latest_entry = db.query(AuditLog).order_by(desc(AuditLog.id)).first()
    prev_hash = latest_entry.hash if latest_entry else None

    # Canonical event payload to be hashed
    event_payload = {
        "event_time": _format_time(event_time),
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "target_type": target_type,
        "target_id": str(target_id) if target_id else None,
        "details_json": details_json
    }

    current_hash = compute_audit_hash(prev_hash, event_payload)

    audit_entry = AuditLog(
        event_time=event_time,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        details_json=details_json,
        prev_hash=prev_hash,
        hash=current_hash,
        is_tampered=False
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry


def verify_audit_chain(db: Session) -> Dict[str, Any]:
    """
    Walk the entire audit log from genesis to tip.
    Validates both:
      1. prev_hash pointer integrity
      2. SHA256 content signature against canonical payload
    Returns verification summary and first broken index if tampered.
    """
    records: List[AuditLog] = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    total = len(records)

    if total == 0:
        return {
            "is_valid": True,
            "total_records": 0,
            "broken_index": None,
            "broken_id": None,
            "message": "Audit chain is empty and intact."
        }

    for idx, row in enumerate(records):
        expected_prev = records[idx - 1].hash if idx > 0 else None

        # Check 1: prev_hash pointer
        if row.prev_hash != expected_prev:
            return {
                "is_valid": False,
                "total_records": total,
                "broken_index": idx,
                "broken_id": row.id,
                "reason": f"Chain link broken at record #{row.id}: prev_hash ({row.prev_hash}) does not match prior record hash ({expected_prev})."
            }

        # Check 2: Payload content re-hash
        event_payload = {
            "event_time": _format_time(row.event_time),
            "actor_id": row.actor_id,
            "actor_role": row.actor_role,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": str(row.target_id) if row.target_id else None,
            "details_json": row.details_json
        }
        recomputed_hash = compute_audit_hash(expected_prev, event_payload)

        if recomputed_hash != row.hash:
            return {
                "is_valid": False,
                "total_records": total,
                "broken_index": idx,
                "broken_id": row.id,
                "reason": f"Payload tamper detected at record #{row.id}: stored hash does not match canonical recomputed hash."
            }

    return {
        "is_valid": True,
        "total_records": total,
        "broken_index": None,
        "broken_id": None,
        "message": f"Cryptographic audit chain fully verified ({total} events intact)."
    }


def tamper_audit_row_for_demo(db: Session, record_id: int, forged_action: Optional[str] = None, forged_details: Optional[Dict[str, Any]] = None) -> AuditLog:
    """
    Intentionally corrupt an audit row in the database WITHOUT updating
    the stored cryptographic hash. This is used by the demo & tests
    to prove that tampering is immediately flagged by the verification walker.
    """
    row = db.query(AuditLog).filter(AuditLog.id == record_id).first()
    if not row:
        raise ValueError(f"Audit record #{record_id} not found")

    if forged_action:
        row.action = forged_action
    if forged_details:
        row.details_json = forged_details
    row.is_tampered = True

    db.commit()
    db.refresh(row)
    return row
