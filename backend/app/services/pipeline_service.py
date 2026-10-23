import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from PIL import Image
import io

from app.models.entities import (
    User, FDRCase, FDRVersion, Document, ExtractedField,
    ForensicFinding, DuplicateMatch, TrustEvent,
    TrustLevel, CaseStatus
)
from app.services.storage_service import retrieve_and_decrypt_document
from app.services.audit_service import record_audit_event
from app.forensics.preprocessor import pdf_bytes_to_images, preprocess_document_image
from app.forensics.ocr_engine import extract_document_text
from app.forensics.field_extractor import extract_structured_fields
from app.forensics.checks import (
    check_financial_consistency,
    check_bank_fdr_pattern,
    check_pdf_digital_signature,
    compute_ela_heatmap,
    inspect_pikepdf_metadata,
    check_qr_envelope_and_payload
)
from app.forensics.duplicate_radar import (
    compute_fdr_fingerprint,
    compute_page_phash,
    scan_for_duplicates
)


def process_fdr_document(
    db: Session,
    document: Document,
    institution_id: str,
    user_id: Optional[str] = None,
    existing_case_id: Optional[str] = None,
    change_reason: str = "INITIAL_SUBMISSION"
) -> Dict[str, Any]:
    """
    Intake and Forensics Pipeline:
    Decrypt -> Preprocess -> OCR -> Forensic Analysis -> Duplicate Radar -> Trust Ladder L2 Evaluation
    """
    # 1. Retrieve and decrypt raw document bytes
    doc_bytes = retrieve_and_decrypt_document(document.storage_path, expected_sha256=document.sha256_hash)

    # 2. Rasterize to PIL image for visual inspection and OCR
    if document.mime_type == "application/pdf":
        page_images = pdf_bytes_to_images(doc_bytes, dpi=180)
        first_page = page_images[0] if page_images else Image.new("RGB", (800, 1100), "white")
    else:
        first_page = Image.open(io.BytesIO(doc_bytes)).convert("RGB")

    # 3. Preprocess: deskew and denoise
    processed_page, skew_angle = preprocess_document_image(first_page)

    # 4. Perceptual Hash
    phash_val = compute_page_phash(processed_page)
    document.perceptual_hash = phash_val
    db.commit()

    # 5. Extract text and parse structured fields
    ocr_res = extract_document_text(doc_bytes, document.mime_type, preprocessed_image=processed_page)
    raw_text = ocr_res.get("text", "")
    extracted_fields = extract_structured_fields(raw_text, base_confidence=ocr_res.get("confidence", 0.90))

    # 6. Resolve Case and Version
    principal = float(extracted_fields.get("principal_amount", {}).get("value") or 500000.0)
    maturity_amt = float(extracted_fields.get("maturity_amount", {}).get("value") or principal * 1.15)
    rate = float(extracted_fields.get("interest_rate", {}).get("value") or 7.0)
    tenure = int(extracted_fields.get("tenure_months", {}).get("value") or 36)
    fdr_no = extracted_fields.get("fdr_number", {}).get("value") or f"UNKNOWN-{document.id[:8]}"
    bank_name = extracted_fields.get("bank_name", {}).get("value") or "Commercial Bank"

    try:
        issue_date = datetime.strptime(extracted_fields.get("issue_date", {}).get("value"), "%Y-%m-%d")
    except Exception:
        issue_date = datetime.now(timezone.utc)

    try:
        maturity_date = datetime.strptime(extracted_fields.get("maturity_date", {}).get("value"), "%Y-%m-%d")
    except Exception:
        maturity_date = datetime.now(timezone.utc)

    if existing_case_id:
        # Renewal creates a new version, never overwrites
        fdr_case = db.query(FDRCase).filter(FDRCase.id == existing_case_id).first()
        version_num = len(fdr_case.versions) + 1
    else:
        # Create new FDR Case
        import uuid
        case_num = f"CASE-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:8].upper()}"
        fdr_case = FDRCase(
            case_number=case_num,
            institution_id=institution_id,
            bank_name=bank_name,
            fdr_number=fdr_no,
            currency="INR",
            principal_amount=principal,
            maturity_amount=maturity_amt,
            interest_rate=rate,
            issue_date=issue_date,
            maturity_date=maturity_date,
            tenure_months=tenure,
            trust_level=TrustLevel.L1_DECLARED,
            status=CaseStatus.SUBMITTED
        )
        db.add(fdr_case)
        db.commit()
        db.refresh(fdr_case)
        version_num = 1

    # Check user existence for foreign key safety
    valid_user_id = None
    if user_id:
        user_record = db.query(User).filter(User.id == user_id).first()
        if user_record:
            valid_user_id = user_id

    # Create Version
    fdr_version = FDRVersion(
        case_id=fdr_case.id,
        version_number=version_num,
        change_reason=change_reason,
        created_by_user_id=valid_user_id,
        document_id=document.id
    )
    db.add(fdr_version)
    db.commit()
    db.refresh(fdr_version)

    fdr_case.current_version_id = fdr_version.id

    # 7. Store Extracted Fields in DB
    for f_name, f_data in extracted_fields.items():
        ex_field = ExtractedField(
            version_id=fdr_version.id,
            document_id=document.id,
            field_name=f_name,
            field_value=str(f_data.get("value")) if f_data.get("value") is not None else None,
            confidence=float(f_data.get("confidence", 0.9)),
            raw_ocr_text=raw_text[:200],
            is_flagged_for_manual_review=bool(f_data.get("flagged", False))
        )
        db.add(ex_field)

    # 8. Run All Forensic Checks
    all_findings: List[Dict[str, Any]] = []

    # Check A: Financial consistency (Words vs Figures, Tenure Dates, Interest formula)
    all_findings.extend(check_financial_consistency(extracted_fields))

    # Check B: Bank FDR pattern
    all_findings.extend(check_bank_fdr_pattern(extracted_fields))

    # Check C: PDF pyHanko digital signature check
    if document.mime_type == "application/pdf":
        all_findings.append(check_pdf_digital_signature(doc_bytes))

    # Check D1: ELA heatmap & mean error
    _, ela_err = compute_ela_heatmap(processed_page)
    if ela_err > 18.0:
        all_findings.append({
            "check_type": "ELA_ANOMALY",
            "severity": "MEDIUM",
            "status": "ANOMALY_FLAGGED",
            "title": "High Error Level Analysis (ELA) Divergence",
            "description": "Anomaly for human review: Disproportionate compression error level detected in page raster.",
            "evidence_json": {"mean_error": round(ela_err, 2), "threshold": 18.0}
        })

    # Check D2: pikepdf metadata inspection
    if document.mime_type == "application/pdf":
        all_findings.extend(inspect_pikepdf_metadata(doc_bytes))

    # Check E: QR code cryptographic signature and field cross-comparison
    all_findings.extend(check_qr_envelope_and_payload(processed_page, extracted_fields))

    # Store findings in DB
    blocking_flags = 0
    for finding in all_findings:
        is_anomaly = (finding.get("status") == "ANOMALY_FLAGGED")
        severity = finding.get("severity", "MEDIUM")
        if is_anomaly and severity in ("HIGH", "CRITICAL"):
            blocking_flags += 1

        db_finding = ForensicFinding(
            version_id=fdr_version.id,
            check_type=finding.get("check_type", "GENERIC_CHECK"),
            severity=severity,
            status=finding.get("status", "PASS"),
            title=finding.get("title", "Forensic Check"),
            description=finding.get("description", ""),
            evidence_json=finding.get("evidence_json", {})
        )
        db.add(db_finding)

    # 9. Duplicate Radar Multi-Vector Scan
    fingerprint = compute_fdr_fingerprint(
        bank_name=bank_name,
        fdr_number=fdr_no,
        principal_amount=principal,
        issue_date_str=issue_date.strftime("%Y-%m-%d")
    )
    dup_matches = scan_for_duplicates(
        db=db,
        primary_case=fdr_case,
        fingerprint=fingerprint,
        phash_str=phash_val,
        extracted_fields=extracted_fields
    )

    for dm in dup_matches:
        db.add(dm)
        blocking_flags += 1

    # 10. Trust Ladder Evaluation
    # L1: Declared (on submission)
    # L2: Machine-checked (advanced if no blocking high/critical forensic anomalies or duplicate flags)
    prev_trust = fdr_case.trust_level
    if blocking_flags == 0:
        fdr_case.trust_level = TrustLevel.L2_MACHINE_CHECKED
        fdr_case.status = CaseStatus.UNDER_REVIEW

        trust_event = TrustEvent(
            case_id=fdr_case.id,
            version_id=fdr_version.id,
            from_level=prev_trust,
            to_level=TrustLevel.L2_MACHINE_CHECKED,
            trigger_type="FORENSIC_SCAN",
            actor_user_id=valid_user_id,
            notes="Automated intake completed with zero blocking forensic anomalies. Promoted to L2 Machine-checked."
        )
        db.add(trust_event)
    else:
        fdr_case.status = CaseStatus.UNDER_REVIEW
        trust_event = TrustEvent(
            case_id=fdr_case.id,
            version_id=fdr_version.id,
            from_level=prev_trust,
            to_level=prev_trust,
            trigger_type="FORENSIC_SCAN",
            actor_user_id=valid_user_id,
            notes=f"Automated intake flagged {blocking_flags} anomalies for human review. Retained at L1 Declared."
        )
        db.add(trust_event)

    db.commit()
    db.refresh(fdr_case)

    # 11. Hash-chained audit event
    record_audit_event(
        db=db,
        actor_id=user_id,
        actor_role="system",
        action="FDR_INGESTION_COMPLETED",
        target_type="FDR_CASE",
        target_id=fdr_case.id,
        details_json={
            "case_number": fdr_case.case_number,
            "fdr_number": fdr_case.fdr_number,
            "blocking_flags": blocking_flags,
            "trust_level": fdr_case.trust_level,
            "duplicate_matches_count": len(dup_matches)
        }
    )

    return {
        "case_id": fdr_case.id,
        "case_number": fdr_case.case_number,
        "version_id": fdr_version.id,
        "fdr_number": fdr_case.fdr_number,
        "trust_level": fdr_case.trust_level,
        "blocking_flags_count": blocking_flags,
        "duplicate_matches_count": len(dup_matches),
        "status": fdr_case.status
    }
