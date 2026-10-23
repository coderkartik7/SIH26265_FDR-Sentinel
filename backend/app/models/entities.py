import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, String, Boolean, DateTime, Float, Integer, ForeignKey, Text, JSON, Enum
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str):
    INSTITUTION = "institution"
    OFFICIAL = "official"
    ADMIN = "admin"


class TrustLevel(str):
    L1_DECLARED = "L1_DECLARED"
    L2_MACHINE_CHECKED = "L2_MACHINE_CHECKED"
    L3_SOURCE_VERIFIED = "L3_SOURCE_VERIFIED"
    L4_SEALED = "L4_SEALED"


class CaseStatus(str):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    SEALED = "SEALED"
    MATURED = "MATURED"
    RELEASE_REQUESTED = "RELEASE_REQUESTED"
    RELEASED = "RELEASED"
    REJECTED = "REJECTED"


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    region = Column(String(50), nullable=False) # Northern, Southern, Western
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    contact_email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    users = relationship("User", back_populates="institution")
    cases = relationship("FDRCase", back_populates="institution")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.INSTITUTION, nullable=False)
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    institution = relationship("Institution", back_populates="users")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    sha256_hash = Column(String(64), index=True, nullable=False)
    perceptual_hash = Column(String(64), index=True, nullable=True)
    is_encrypted = Column(Boolean, default=True, nullable=False)
    encrypted_dek = Column(Text, nullable=True)
    is_scanned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    versions = relationship("FDRVersion", back_populates="document")


class FDRCase(Base):
    __tablename__ = "fdr_cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_number = Column(String(50), unique=True, index=True, nullable=False)
    institution_id = Column(String(36), ForeignKey("institutions.id"), nullable=False)
    bank_name = Column(String(255), nullable=False)
    fdr_number = Column(String(100), index=True, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    principal_amount = Column(Float, nullable=False)
    maturity_amount = Column(Float, nullable=False)
    interest_rate = Column(Float, nullable=False)
    issue_date = Column(DateTime, nullable=False)
    maturity_date = Column(DateTime, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    trust_level = Column(String(50), default=TrustLevel.L1_DECLARED, nullable=False)
    current_version_id = Column(String(36), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default=CaseStatus.SUBMITTED, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    institution = relationship("Institution", back_populates="cases")
    versions = relationship("FDRVersion", back_populates="case", cascade="all, delete-orphan")
    trust_events = relationship("TrustEvent", back_populates="case", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="case", cascade="all, delete-orphan")


class FDRVersion(Base):
    __tablename__ = "fdr_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("fdr_cases.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, default=1, nullable=False)
    change_reason = Column(String(100), default="INITIAL_SUBMISSION", nullable=False)
    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    case = relationship("FDRCase", back_populates="versions")
    document = relationship("Document", back_populates="versions")
    extracted_fields = relationship("ExtractedField", back_populates="version", cascade="all, delete-orphan")
    forensic_findings = relationship("ForensicFinding", back_populates="version", cascade="all, delete-orphan")
    verification_results = relationship("VerificationResult", back_populates="version", cascade="all, delete-orphan")
    risk_scores = relationship("RiskScore", back_populates="version", cascade="all, delete-orphan")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    version_id = Column(String(36), ForeignKey("fdr_versions.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    field_name = Column(String(100), nullable=False) # bank, fdr_number, principal_amount, etc.
    field_value = Column(String(500), nullable=True)
    confidence = Column(Float, default=1.0, nullable=False) # 0.0 - 1.0
    raw_ocr_text = Column(Text, nullable=True)
    bounding_box_json = Column(JSON, nullable=True)
    is_flagged_for_manual_review = Column(Boolean, default=False, nullable=False)
    manual_corrected_value = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    version = relationship("FDRVersion", back_populates="extracted_fields")


class ForensicFinding(Base):
    __tablename__ = "forensic_findings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    version_id = Column(String(36), ForeignKey("fdr_versions.id", ondelete="CASCADE"), nullable=False)
    check_type = Column(String(100), nullable=False) # WORDS_VS_FIGURES, BANK_PATTERN, PYHANKO_SIG, ELA_TAMPER, PIKEPDF_METADATA, QR_PAYLOAD, ANOMALY_FOREST
    severity = Column(String(20), default="MEDIUM", nullable=False) # INFO, LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(50), default="PASS", nullable=False) # PASS, ANOMALY_FLAGGED
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    evidence_json = Column(JSON, nullable=False, default=dict)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    version = relationship("FDRVersion", back_populates="forensic_findings")


class DuplicateMatch(Base):
    __tablename__ = "duplicate_matches"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    primary_case_id = Column(String(36), ForeignKey("fdr_cases.id", ondelete="CASCADE"), nullable=False)
    matching_case_id = Column(String(36), ForeignKey("fdr_cases.id", ondelete="CASCADE"), nullable=False)
    match_type = Column(String(50), nullable=False) # EXACT_FINGERPRINT, CROSS_INSTITUTION_REUSE, POST_RELEASE_REPRESENT, VISUAL_PERCEPTUAL_PHASH
    similarity_score = Column(Float, default=1.0, nullable=False)
    evidence_json = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), default="DETECTED", nullable=False) # DETECTED, REVIEWED, CONFIRMED, DISMISSED
    created_at = Column(DateTime, default=utc_now)


class TrustEvent(Base):
    __tablename__ = "trust_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("fdr_cases.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String(36), ForeignKey("fdr_versions.id"), nullable=True)
    from_level = Column(String(50), nullable=False)
    to_level = Column(String(50), nullable=False)
    trigger_type = Column(String(50), nullable=False) # SYSTEM_OCR, FORENSIC_SCAN, CONNECTOR_VERIFIED, OFFICIAL_SEAL, MANUAL_OVERRIDE
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    case = relationship("FDRCase", back_populates="trust_events")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("fdr_cases.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String(36), ForeignKey("fdr_versions.id", ondelete="CASCADE"), nullable=False)
    adapter_name = Column(String(50), nullable=False) # MockIssuerAdapter, QRAdapter, SignatureAdapter
    is_simulated = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    raw_response_json = Column(JSON, nullable=False, default=dict)
    verified_at = Column(DateTime, default=utc_now)

    version = relationship("FDRVersion", back_populates="verification_results")


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("fdr_cases.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String(36), ForeignKey("fdr_versions.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False) # 0 to 100
    risk_level = Column(String(20), nullable=False) # LOW, MEDIUM, HIGH
    anomaly_score = Column(Float, default=0.0)
    top_reasons_json = Column(JSON, nullable=False, default=list) # SHAP reasons
    model_version = Column(String(50), default="GBDT-v1.0")
    computed_at = Column(DateTime, default=utc_now)

    version = relationship("FDRVersion", back_populates="risk_scores")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("fdr_cases.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String(50), nullable=False) # MATURITY_90, MATURITY_60, MATURITY_30, MATURITY_15, MATURITY_7, HIGH_RISK_ESCALATION, UNRESOLVED_FLAG
    severity = Column(String(20), default="MEDIUM", nullable=False)
    message = Column(Text, nullable=False)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    case = relationship("FDRCase", back_populates="alerts")


class ReleaseRequest(Base):
    __tablename__ = "release_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("fdr_cases.id", ondelete="CASCADE"), nullable=False)
    institution_id = Column(String(36), ForeignKey("institutions.id"), nullable=False)
    requested_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="PENDING_CHECKLIST", nullable=False) # PENDING_CHECKLIST, SUBMITTED, APPROVED, REJECTED, COMPLETED
    checklist_json = Column(JSON, nullable=False, default=dict)
    closure_report_path = Column(String(500), nullable=True)
    approved_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class IssuerLedger(Base):
    __tablename__ = "issuer_ledger"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    bank_id = Column(String(50), nullable=False)
    bank_name = Column(String(255), nullable=False)
    fdr_number = Column(String(100), unique=True, index=True, nullable=False)
    institution_name = Column(String(255), nullable=False)
    principal_amount = Column(Float, nullable=False)
    maturity_amount = Column(Float, nullable=False)
    interest_rate = Column(Float, nullable=False)
    issue_date = Column(DateTime, nullable=False)
    maturity_date = Column(DateTime, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False) # ACTIVE, RENEWED, LIQUIDATED, RELEASED
    qr_public_key = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_time = Column(DateTime, default=utc_now, nullable=False)
    actor_id = Column(String(36), nullable=True)
    actor_role = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False) # e.g. AUTH_LOGIN, FDR_UPLOAD, TRUST_TRANSITION, OFFICIAL_DECISION
    target_type = Column(String(100), nullable=False) # FDR_CASE, USER, DOCUMENT, RELEASE_REQUEST
    target_id = Column(String(100), nullable=True)
    details_json = Column(JSON, nullable=False, default=dict)
    prev_hash = Column(String(64), nullable=True)
    hash = Column(String(64), nullable=False)
    is_tampered = Column(Boolean, default=False, nullable=False)
