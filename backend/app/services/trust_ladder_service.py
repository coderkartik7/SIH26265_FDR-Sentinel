import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.entities import (
    FDRCase, FDRVersion, Document, VerificationResult,
    TrustEvent, TrustLevel, CaseStatus, User, UserRole
)
from app.connectors.mock_issuer_adapter import MockIssuerAdapter
from app.connectors.qr_adapter import QRAdapter
from app.connectors.signature_adapter import SignatureAdapter
from app.services.audit_service import record_audit_event

CONNECTORS = [
    QRAdapter(),
    SignatureAdapter(),
    MockIssuerAdapter()
]


def run_all_verification_connectors(
    db: Session,
    fdr_case: FDRCase,
    user_id: Optional[str] = None
) -> List[VerificationResult]:
    """
    Executes the three verification connector adapters:
    1. QRAdapter (Real Ed25519)
    2. SignatureAdapter (Real pyHanko test CA)
    3. MockIssuerAdapter (Simulated ledger table, badged)
    Saves VerificationResult records and evaluates Trust Ladder L3 Source-verified status.
    """
    version = next((v for v in fdr_case.versions if v.id == fdr_case.current_version_id), None)
    if not version or not version.document:
        raise ValueError("No active document version associated with this FDR case.")

    results: List[VerificationResult] = []
    any_verified = False

    for connector in CONNECTORS:
        res = connector.verify(fdr_case, version, version.document, db)
        is_ver = res.get("is_verified", False)
        if is_ver:
            any_verified = True

        v_res = VerificationResult(
            case_id=fdr_case.id,
            version_id=version.id,
            adapter_name=connector.adapter_name,
            is_simulated=connector.is_simulated,
            is_verified=is_ver,
            raw_response_json=res
        )
        db.add(v_res)
        results.append(v_res)

    db.commit()

    # If at least one connector confirms and case is at L2, advance to L3_SOURCE_VERIFIED
    if any_verified and fdr_case.trust_level in (TrustLevel.L1_DECLARED, TrustLevel.L2_MACHINE_CHECKED):
        prev_level = fdr_case.trust_level
        fdr_case.trust_level = TrustLevel.L3_SOURCE_VERIFIED
        fdr_case.status = CaseStatus.VERIFIED

        trust_event = TrustEvent(
            case_id=fdr_case.id,
            version_id=version.id,
            from_level=prev_level,
            to_level=TrustLevel.L3_SOURCE_VERIFIED,
            trigger_type="CONNECTOR_VERIFIED",
            actor_user_id=user_id,
            notes="Source confirmed by verification connector. Promoted to L3 Source-verified."
        )
        db.add(trust_event)
        db.commit()

        # Audit log
        record_audit_event(
            db=db,
            actor_id=user_id,
            actor_role="system",
            action="TRUST_PROMOTED_L3_SOURCE_VERIFIED",
            target_type="FDR_CASE",
            target_id=fdr_case.id,
            details_json={
                "fdr_number": fdr_case.fdr_number,
                "verified_connectors": [r.adapter_name for r in results if r.is_verified]
            }
        )

    return results


def seal_fdr_case(
    db: Session,
    fdr_case: FDRCase,
    official_user: User,
    decision: str, # SEAL_APPROVE or REJECT
    decision_notes: str
) -> Dict[str, Any]:
    """
    Transition to L4 Sealed:
    A human official makes the final decision on every flagged or verified FDR (Honesty Rule 5).
    Locks the record, generates cryptographic sealed QR receipt digest, and writes hash-chained audit log.
    Edits create a new version, never overwrites.
    """
    version = next((v for v in fdr_case.versions if v.id == fdr_case.current_version_id), None)
    prev_level = fdr_case.trust_level

    if decision == "SEAL_APPROVE":
        fdr_case.trust_level = TrustLevel.L4_SEALED
        fdr_case.status = CaseStatus.SEALED

        # Generate cryptographic sealed receipt digest
        receipt_payload = {
            "case_id": fdr_case.id,
            "case_number": fdr_case.case_number,
            "fdr_number": fdr_case.fdr_number,
            "principal": fdr_case.principal_amount,
            "institution_id": fdr_case.institution_id,
            "sealed_by": official_user.email,
            "sealed_at": datetime.now(timezone.utc).isoformat()
        }
        sealed_digest = hashlib.sha256(json.dumps(receipt_payload, sort_keys=True).encode("utf-8")).hexdigest()

        trust_event = TrustEvent(
            case_id=fdr_case.id,
            version_id=version.id if version else None,
            from_level=prev_level,
            to_level=TrustLevel.L4_SEALED,
            trigger_type="OFFICIAL_SEAL",
            actor_user_id=official_user.id,
            notes=f"Official Approval: {decision_notes}. Sealed Receipt Hash: {sealed_digest[:16]}"
        )
        db.add(trust_event)
        db.commit()

        # Hash-chained audit entry
        record_audit_event(
            db=db,
            actor_id=official_user.id,
            actor_role=official_user.role,
            action="OFFICIAL_SEALED_L4",
            target_type="FDR_CASE",
            target_id=fdr_case.id,
            details_json={
                "fdr_number": fdr_case.fdr_number,
                "notes": decision_notes,
                "sealed_receipt_digest": sealed_digest
            }
        )

        return {
            "status": "SEALED",
            "trust_level": TrustLevel.L4_SEALED,
            "sealed_receipt_digest": sealed_digest,
            "message": "FDR successfully sealed at L4. Record is locked against modification."
        }
    else:
        # Rejection
        fdr_case.status = CaseStatus.REJECTED
        trust_event = TrustEvent(
            case_id=fdr_case.id,
            version_id=version.id if version else None,
            from_level=prev_level,
            to_level=prev_level,
            trigger_type="OFFICIAL_OVERRIDE",
            actor_user_id=official_user.id,
            notes=f"Official Rejection: {decision_notes}"
        )
        db.add(trust_event)
        db.commit()

        record_audit_event(
            db=db,
            actor_id=official_user.id,
            actor_role=official_user.role,
            action="OFFICIAL_REJECTED",
            target_type="FDR_CASE",
            target_id=fdr_case.id,
            details_json={"notes": decision_notes}
        )

        return {
            "status": "REJECTED",
            "trust_level": fdr_case.trust_level,
            "message": f"FDR rejected by official: {decision_notes}"
        }
