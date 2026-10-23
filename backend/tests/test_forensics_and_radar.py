import io
import csv
from pathlib import Path
from datetime import datetime, timezone
import pytest
from PIL import Image

from app.models.entities import (
    User, UserRole, Institution, Document, FDRCase,
    ExtractedField, ForensicFinding, DuplicateMatch,
    TrustLevel, CaseStatus, IssuerLedger
)
from app.services.storage_service import store_encrypted_document
from app.services.pipeline_service import process_fdr_document
from app.forensics.checks import (
    check_financial_consistency,
    check_bank_fdr_pattern,
    check_pdf_digital_signature,
    compute_ela_heatmap,
    inspect_pikepdf_metadata
)
from app.forensics.duplicate_radar import scan_for_duplicates, compute_fdr_fingerprint

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCUMENTS_DIR = BASE_DIR / "datagen" / "out" / "documents"


def test_words_vs_figures_consistency_check():
    # Matching words vs figures
    valid_fields = {
        "principal_amount": {"value": "1000000.0"},
        "amount_in_words": {"value": "Rupees Ten Lakh Only"}
    }
    findings = check_financial_consistency(valid_fields)
    words_findings = [f for f in findings if f["check_type"] == "WORDS_VS_FIGURES"]
    assert len(words_findings) == 0

    # Mismatched words vs figures (e.g. Tamper test)
    tampered_fields = {
        "principal_amount": {"value": "1000000.0"},
        "amount_in_words": {"value": "Rupees Eighty Five Lakh Only"}
    }
    tampered_findings = check_financial_consistency(tampered_fields)
    flagged = [f for f in tampered_findings if f["check_type"] == "WORDS_VS_FIGURES"]
    assert len(flagged) == 1
    assert flagged[0]["status"] == "ANOMALY_FLAGGED"
    assert "token_overlap_ratio" in flagged[0]["evidence_json"]


def test_bank_fdr_pattern_check():
    # Valid ACT pattern
    valid_act = {
        "bank_name": {"value": "Apex Commercial Trust"},
        "fdr_number": {"value": "ACT-FD-DL-101001"}
    }
    assert len(check_bank_fdr_pattern(valid_act)) == 0

    # Invalid pattern for ACT
    invalid_act = {
        "bank_name": {"value": "Apex Commercial Trust"},
        "fdr_number": {"value": "INVALID-12345-FORMAT"}
    }
    act_findings = check_bank_fdr_pattern(invalid_act)
    assert len(act_findings) == 1
    assert act_findings[0]["severity"] == "CRITICAL"


def test_pyhanko_digital_signature_check():
    # Find a genuine signed PDF from datagen
    signed_files = list(DOCUMENTS_DIR.glob("fdr_001_ACT_*.pdf"))
    if signed_files:
        with open(signed_files[0], "rb") as f:
            pdf_bytes = f.read()
        res = check_pdf_digital_signature(pdf_bytes)
        assert res["evidence_json"]["status"] == "valid"

    # Find a signature-tampered PDF
    tampered_sig_files = list(DOCUMENTS_DIR.glob("*signature_breaking_edit*.pdf"))
    if tampered_sig_files:
        with open(tampered_sig_files[0], "rb") as f:
            pdf_bytes = f.read()
        res_tampered = check_pdf_digital_signature(pdf_bytes)
        assert res_tampered["status"] == "ANOMALY_FLAGGED"
        assert res_tampered["severity"] in ("CRITICAL", "HIGH")


def test_duplicate_radar_cross_institution(db):
    inst1 = Institution(id="INST-TEST-1", name="College A", code="COL-A", region="Northern", city="Delhi", state="Delhi", contact_email="a@col.edu")
    inst2 = Institution(id="INST-TEST-2", name="College B", code="COL-B", region="Southern", city="Chennai", state="TN", contact_email="b@col.edu")
    db.add_all([inst1, inst2])
    db.commit()

    case_existing = FDRCase(
        case_number="CASE-2026-0001",
        institution_id=inst1.id,
        bank_name="Apex Commercial Trust",
        fdr_number="ACT-FD-DL-109999",
        principal_amount=1000000.0,
        maturity_amount=1200000.0,
        interest_rate=7.0,
        issue_date=datetime(2024, 1, 1),
        maturity_date=datetime(2027, 1, 1),
        tenure_months=36,
        trust_level=TrustLevel.L2_MACHINE_CHECKED,
        status=CaseStatus.VERIFIED
    )
    db.add(case_existing)
    db.commit()

    # Now a second institution submits the exact same FDR number
    case_new = FDRCase(
        case_number="CASE-2026-0002",
        institution_id=inst2.id,
        bank_name="Apex Commercial Trust",
        fdr_number="ACT-FD-DL-109999",
        principal_amount=1000000.0,
        maturity_amount=1200000.0,
        interest_rate=7.0,
        issue_date=datetime(2024, 1, 1),
        maturity_date=datetime(2027, 1, 1),
        tenure_months=36,
        trust_level=TrustLevel.L1_DECLARED,
        status=CaseStatus.SUBMITTED
    )
    db.add(case_new)
    db.commit()

    fingerprint = compute_fdr_fingerprint(case_new.bank_name, case_new.fdr_number, case_new.principal_amount, "2024-01-01")
    matches = scan_for_duplicates(db, case_new, fingerprint, None, {})

    assert len(matches) > 0
    cross_matches = [m for m in matches if m.match_type == "CROSS_INSTITUTION_REUSE"]
    assert len(cross_matches) == 1
    assert cross_matches[0].matching_case_id == case_existing.id


def test_end_to_end_fdr_ingestion_stores_fields_and_promotes_trust(db):
    inst = Institution(id="INST-E2E", name="E2E Institute", code="E2E-01", region="Western", city="Pune", state="MH", contact_email="e2e@inst.edu")
    db.add(inst)
    db.commit()

    # Ingest a clean genuine PDF from datagen
    genuine_files = list(DOCUMENTS_DIR.glob("fdr_002_ACT_*.pdf"))
    assert len(genuine_files) > 0, "Generated documents should exist"
    test_pdf_path = genuine_files[0]

    with open(test_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Store encrypted document
    storage_path, sha256_hash, file_size, mime_type = store_encrypted_document(
        filename=test_pdf_path.name,
        raw_data=pdf_bytes
    )

    doc = Document(
        filename=test_pdf_path.name,
        original_name=test_pdf_path.name,
        mime_type=mime_type,
        file_size=file_size,
        storage_path=storage_path,
        sha256_hash=sha256_hash,
        is_encrypted=True
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process document through intake pipeline
    res = process_fdr_document(
        db=db,
        document=doc,
        institution_id=inst.id,
        user_id="test_user"
    )

    assert res["status"] in (CaseStatus.UNDER_REVIEW, CaseStatus.SUBMITTED)
    assert res["trust_level"] == TrustLevel.L2_MACHINE_CHECKED
    assert res["blocking_flags_count"] == 0

    # Verify extracted fields were stored in DB
    stored_fields = db.query(ExtractedField).filter(ExtractedField.version_id == res["version_id"]).all()
    assert len(stored_fields) >= 5
    field_names = [f.field_name for f in stored_fields]
    assert "principal_amount" in field_names
    assert "fdr_number" in field_names

    # Verify findings were stored in DB
    stored_findings = db.query(ForensicFinding).filter(ForensicFinding.version_id == res["version_id"]).all()
    assert len(stored_findings) >= 1
