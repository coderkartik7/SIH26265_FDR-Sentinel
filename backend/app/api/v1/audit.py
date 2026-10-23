from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.entities import AuditLog, User, UserRole
from app.schemas.audit import AuditLogResponse, AuditVerifyResponse, TamperDemoRequest
from app.services.audit_service import verify_audit_chain, tamper_audit_row_for_demo
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/audit", tags=["Cryptographic Audit Chain"])


@router.get("/verify", response_model=AuditVerifyResponse)
def verify_audit_log_chain(db: Session = Depends(get_db)):
    """
    Cryptographic verification endpoint:
    Walks the entire hash chain from index 0 to latest.
    Recalculates SHA256(prev_hash + canonical_json(event_payload)) for every record.
    Returns:
      is_valid: true if uncompromised
      broken_index: index of first detected modification if tampered
    """
    result = verify_audit_chain(db)
    return result


@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    target_type: Optional[str] = None,
    action: Optional[str] = None,
    current_user: User = Depends(require_roles([UserRole.OFFICIAL, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Retrieve audit log entries with optional filters.
    Restricted to AICTE Officials and Administrators.
    """
    query = db.query(AuditLog)
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    if action:
        query = query.filter(AuditLog.action == action)

    logs = query.order_by(desc(AuditLog.id)).offset(offset).limit(limit).all()
    return logs


@router.post("/tamper-demo", response_model=AuditLogResponse)
def simulate_database_tamper(
    req: TamperDemoRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Demonstration and testing endpoint:
    Intentionally mutates a record directly in the DB WITHOUT updating the cryptographic hash.
    This simulates an attacker or unauthorized DB admin modifying history.
    Subsequent calls to /audit/verify will pinpoint this exact row as tampered.
    """
    try:
        tampered_row = tamper_audit_row_for_demo(
            db=db,
            record_id=req.record_id,
            forged_action=req.forged_action,
            forged_details=req.forged_details
        )
        return tampered_row
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
