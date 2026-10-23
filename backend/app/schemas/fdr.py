from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class ExtractedFieldResponse(BaseModel):
    id: str
    field_name: str
    field_value: Optional[str] = None
    confidence: float = 1.0
    confidence_score: Optional[float] = None
    raw_ocr_text: Optional[str] = None
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    bounding_box_json: Optional[Dict[str, Any]] = None
    is_flagged_for_manual_review: bool
    manual_corrected_value: Optional[str] = None

    @model_validator(mode="before")
    def add_field_aliases(cls, v):
        if hasattr(v, "__dict__"):
            data = dict(v.__dict__)
            data["confidence_score"] = getattr(v, "confidence", 1.0)
            data["raw_value"] = getattr(v, "raw_ocr_text", None) or getattr(v, "field_value", None)
            data["normalized_value"] = getattr(v, "field_value", None)
            return data
        elif isinstance(v, dict):
            v.setdefault("confidence_score", v.get("confidence", 1.0))
            v.setdefault("raw_value", v.get("raw_ocr_text", v.get("field_value")))
            v.setdefault("normalized_value", v.get("field_value"))
            return v
        return v

    class Config:
        from_attributes = True


class ExtractedFieldUpdateRequest(BaseModel):
    manual_corrected_value: str


class ForensicFindingResponse(BaseModel):
    id: str
    check_type: str
    check_name: Optional[str] = None
    category: Optional[str] = None
    severity: str
    status: str
    title: str
    description: str
    details: Optional[Dict[str, Any]] = None
    evidence_json: Dict[str, Any] = {}
    is_resolved: bool
    resolved_by_user_id: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime

    @model_validator(mode="before")
    def add_finding_aliases(cls, v):
        if hasattr(v, "__dict__"):
            data = dict(v.__dict__)
            data["check_name"] = getattr(v, "check_type", "FORENSIC_CHECK")
            data["category"] = getattr(v, "severity", "INSPECTION")
            data["details"] = getattr(v, "evidence_json", {})
            return data
        elif isinstance(v, dict):
            v.setdefault("check_name", v.get("check_type", "FORENSIC_CHECK"))
            v.setdefault("category", v.get("severity", "INSPECTION"))
            v.setdefault("details", v.get("evidence_json", {}))
            return v
        return v

    class Config:
        from_attributes = True


class DuplicateMatchResponse(BaseModel):
    id: str
    primary_case_id: str
    matching_case_id: str
    match_type: str
    similarity_score: float
    evidence_json: Dict[str, Any]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class VerificationResultResponse(BaseModel):
    id: str
    adapter_name: str
    connector_type: Optional[str] = None
    is_simulated: bool
    is_verified: bool
    status: Optional[str] = None
    raw_response_json: Dict[str, Any] = {}
    raw_response: Optional[Dict[str, Any]] = None
    verified_at: datetime

    @model_validator(mode="before")
    def add_result_aliases(cls, v):
        if hasattr(v, "__dict__"):
            data = dict(v.__dict__)
            data["connector_type"] = getattr(v, "adapter_name", "CONNECTOR")
            data["status"] = "CONFIRMED" if getattr(v, "is_verified", False) else "DISCREPANCY"
            data["raw_response"] = getattr(v, "raw_response_json", {})
            return data
        elif isinstance(v, dict):
            v.setdefault("connector_type", v.get("adapter_name", "CONNECTOR"))
            v.setdefault("status", "CONFIRMED" if v.get("is_verified") else "DISCREPANCY")
            v.setdefault("raw_response", v.get("raw_response_json", {}))
            return v
        return v

    class Config:
        from_attributes = True


class RiskScoreResponse(BaseModel):
    id: str
    score: float
    overall_score: Optional[float] = None
    risk_level: str
    risk_band: Optional[str] = None
    anomaly_score: float = 0.0
    top_reasons_json: List[Dict[str, Any]] = []
    shap_reasons: Optional[List[Dict[str, Any]]] = None
    model_version: str
    computed_at: datetime

    @model_validator(mode="before")
    def add_risk_aliases(cls, v):
        if hasattr(v, "__dict__"):
            data = dict(v.__dict__)
            data["overall_score"] = getattr(v, "score", 0.0)
            data["risk_band"] = getattr(v, "risk_level", "LOW")
            data["shap_reasons"] = getattr(v, "top_reasons_json", [])
            return data
        elif isinstance(v, dict):
            v.setdefault("overall_score", v.get("score", 0.0))
            v.setdefault("risk_band", v.get("risk_level", "LOW"))
            v.setdefault("shap_reasons", v.get("top_reasons_json", []))
            return v
        return v

    class Config:
        from_attributes = True


class TrustEventResponse(BaseModel):
    id: str
    case_id: str
    from_level: str
    to_level: str
    trigger_type: str
    actor_user_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FDRVersionResponse(BaseModel):
    id: str
    version_number: int
    change_reason: str
    document_id: Optional[str] = None
    created_at: datetime
    extracted_fields: List[ExtractedFieldResponse] = []
    forensic_findings: List[ForensicFindingResponse] = []
    verification_results: List[VerificationResultResponse] = []
    risk_scores: List[RiskScoreResponse] = []

    class Config:
        from_attributes = True


class FDRCaseResponse(BaseModel):
    id: str
    case_number: str
    institution_id: str
    bank_name: str
    fdr_number: str
    currency: str
    principal_amount: float
    maturity_amount: float
    interest_rate: float
    issue_date: datetime
    maturity_date: datetime
    tenure_months: int
    trust_level: str
    status: str
    current_version_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    versions: List[FDRVersionResponse] = []
    trust_events: List[TrustEventResponse] = []

    class Config:
        from_attributes = True


class FDRCaseListItem(BaseModel):
    id: str
    case_number: str
    institution_id: str
    institution_name: Optional[str] = None
    bank_name: str
    fdr_number: str
    principal_amount: float
    maturity_amount: float
    interest_rate: float
    issue_date: datetime
    maturity_date: datetime
    trust_level: str
    status: str
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    unresolved_flags_count: int = 0
    created_at: datetime


class AlertResponse(BaseModel):
    id: str
    case_id: str
    alert_type: str
    severity: str
    message: str
    is_acknowledged: bool
    acknowledged_by_user_id: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReleaseRequestCreate(BaseModel):
    case_id: str
    notes: Optional[str] = None


class ReleaseRequestResponse(BaseModel):
    id: str
    case_id: str
    institution_id: str
    requested_by_user_id: str
    status: str
    checklist_json: Dict[str, Any]
    closure_report_path: Optional[str] = None
    approved_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SealDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(SEAL_APPROVE|REJECT)$")
    notes: str
