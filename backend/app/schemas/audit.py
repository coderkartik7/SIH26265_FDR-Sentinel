from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: int
    event_time: datetime
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[str] = None
    details_json: Dict[str, Any]
    prev_hash: Optional[str] = None
    hash: str
    is_tampered: bool

    class Config:
        from_attributes = True


class AuditVerifyResponse(BaseModel):
    is_valid: bool
    total_records: int
    broken_index: Optional[int] = None
    broken_id: Optional[int] = None
    reason: Optional[str] = None
    message: Optional[str] = None


class TamperDemoRequest(BaseModel):
    record_id: int
    forged_action: Optional[str] = "FORGED_OFFICIAL_APPROVAL"
    forged_details: Optional[Dict[str, Any]] = None
