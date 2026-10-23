import pytest
from datetime import datetime
from pathlib import Path

from app.models.entities import (
    User, UserRole, Institution, Document, FDRCase, FDRVersion,
    TrustLevel, CaseStatus, IssuerLedger
)
from app.connectors.mock_issuer_adapter import MockIssuerAdapter
from app.connectors.qr_adapter import QRAdapter
from app.connectors.signature_adapter import SignatureAdapter
from app.services.trust_ladder_service import run_all_verification_connectors, seal_fdr_case
from app.ml.risk_model import compute_risk_score
from app.core.security import create_access_token, hash_password


def test_mock_issuer_adapter_returns_simulated_badge(db):
    inst = Institution(id="INST-CONN-1", name="Test College", code="TC-01", region="Northern", city="Delhi", state="DL", contact_email="tc@tc.edu")
    db.add(inst)

    # Add row in mock issuer ledger
    ledger_entry = IssuerLedger(
        bank_id="ACT",
        bank_name="Apex Commercial Trust",
        fdr_number="ACT-FD-DL-109001",
        institution_name="Test College",
        principal_amount=1000000.0,
        maturity_amount=1200000.0,
        interest_rate=7.0,
        issue_date=datetime(2024, 1, 1),
        maturity_date=datetime(2027, 1, 1),
        status="ACTIVE"
    )
    db.add(ledger_entry)

    doc = Document(
        filename="dummy.pdf", original_name="dummy.pdf", mime_type="application/pdf",
        file_size=1000, storage_path="dummy.pdf", sha256_hash="0"*64, is_encrypted=False
    )
    db.add(doc)

    case = FDRCase(
        case_number="CASE-2026-9001",
        institution_id=inst.id,
        bank_name="Apex Commercial Trust",
        fdr_number="ACT-FD-DL-109001",
        principal_amount=1000000.0,
        maturity_amount=1200000.0,
        interest_rate=7.0,
        issue_date=datetime(2024, 1, 1),
        maturity_date=datetime(2027, 1, 1),
        tenure_months=36,
        trust_level=TrustLevel.L2_MACHINE_CHECKED,
        status=CaseStatus.UNDER_REVIEW
    )
    db.add(case)
    db.commit()

    ver = FDRVersion(case_id=case.id, version_number=1, document_id=doc.id)
    db.add(ver)
    db.commit()

    adapter = MockIssuerAdapter()
    assert adapter.is_simulated is True
    res = adapter.verify(case, ver, doc, db)
    assert res["is_verified"] is True
    assert res["is_simulated"] is True
    assert res["badge"] == "SIMULATED ISSUER"


def test_trust_ladder_l3_and_l4_sealing(db):
    inst = Institution(id="INST-CONN-2", name="Sealing College", code="SC-02", region="Western", city="Pune", state="MH", contact_email="sc@sc.edu")
    db.add(inst)

    official = User(
        email="seal_official@aicte.gov.in",
        hashed_password=hash_password("Pass123!"),
        full_name="Sealing Officer",
        role=UserRole.OFFICIAL,
        is_active=True
    )
    db.add(official)

    ledger_entry = IssuerLedger(
        bank_id="ACT",
        bank_name="Apex Commercial Trust",
        fdr_number="ACT-FD-DL-109002",
        institution_name="Sealing College",
        principal_amount=2000000.0,
        maturity_amount=2400000.0,
        interest_rate=7.2,
        issue_date=datetime(2024, 2, 1),
        maturity_date=datetime(2027, 2, 1),
        status="ACTIVE"
    )
    db.add(ledger_entry)

    doc = Document(
        filename="dummy2.pdf", original_name="dummy2.pdf", mime_type="application/pdf",
        file_size=1000, storage_path="dummy2.pdf", sha256_hash="1"*64, is_encrypted=False
    )
    db.add(doc)

    case = FDRCase(
        case_number="CASE-2026-9002",
        institution_id=inst.id,
        bank_name="Apex Commercial Trust",
        fdr_number="ACT-FD-DL-109002",
        principal_amount=2000000.0,
        maturity_amount=2400000.0,
        interest_rate=7.2,
        issue_date=datetime(2024, 2, 1),
        maturity_date=datetime(2027, 2, 1),
        tenure_months=36,
        trust_level=TrustLevel.L2_MACHINE_CHECKED,
        status=CaseStatus.UNDER_REVIEW
    )
    db.add(case)
    db.commit()

    ver = FDRVersion(case_id=case.id, version_number=1, document_id=doc.id)
    db.add(ver)
    db.commit()
    case.current_version_id = ver.id
    db.commit()

    # 1. Run Connectors -> advances to L3_SOURCE_VERIFIED
    results = run_all_verification_connectors(db, case, user_id=official.id)
    db.refresh(case)
    assert case.trust_level == TrustLevel.L3_SOURCE_VERIFIED
    assert case.status == CaseStatus.VERIFIED

    # 2. Official Seal Decision -> advances to L4_SEALED
    seal_res = seal_fdr_case(
        db=db,
        fdr_case=case,
        official_user=official,
        decision="SEAL_APPROVE",
        decision_notes="Verified against bank ledger and AICTE approval order."
    )
    db.refresh(case)
    assert case.trust_level == TrustLevel.L4_SEALED
    assert case.status == CaseStatus.SEALED
    assert "sealed_receipt_digest" in seal_res
    assert len(seal_res["sealed_receipt_digest"]) == 64


def test_ml_risk_scoring_and_shap_reasons():
    # Evaluate high risk case (tampered features)
    high_risk_features = {
        "days_to_maturity": 200.0,
        "trust_level_num": 1.0,
        "high_flags_count": 2.0,
        "med_flags_count": 1.0,
        "anomaly_score": 0.85,
        "duplicate_flag": 0.0,
        "principal_lakhs": 25.0,
        "rate_deviation": 1.2
    }
    high_res = compute_risk_score(high_risk_features)
    assert high_res["score"] >= 60.0
    assert len(high_res["top_reasons"]) == 3
    for r in high_res["top_reasons"]:
        assert "feature" in r
        assert "contribution" in r
        assert "description" in r

    # Evaluate clean genuine case
    clean_features = {
        "days_to_maturity": 500.0,
        "trust_level_num": 4.0,
        "high_flags_count": 0.0,
        "med_flags_count": 0.0,
        "anomaly_score": 0.02,
        "duplicate_flag": 0.0,
        "principal_lakhs": 10.0,
        "rate_deviation": 0.1
    }
    clean_res = compute_risk_score(clean_features)
    assert clean_res["score"] <= 35.0
    assert clean_res["risk_level"] == "LOW"


def test_risk_score_api_endpoint(client, db):
    inst = Institution(id="INST-API-RISK", name="Risk Inst", code="RI-01", region="Northern", city="Delhi", state="DL", contact_email="r@r.edu")
    db.add(inst)
    user = User(email="risk_user@aicte.gov.in", hashed_password=hash_password("Pass123!"), full_name="Risk User", role=UserRole.OFFICIAL, is_active=True)
    db.add(user)
    case = FDRCase(
        case_number="CASE-2026-RISK",
        institution_id=inst.id,
        bank_name="Apex Commercial Trust",
        fdr_number="ACT-FD-DL-109099",
        principal_amount=1000000.0,
        maturity_amount=1200000.0,
        interest_rate=7.0,
        issue_date=datetime(2024, 1, 1),
        maturity_date=datetime(2027, 1, 1),
        tenure_months=36,
        trust_level=TrustLevel.L2_MACHINE_CHECKED,
        status=CaseStatus.UNDER_REVIEW
    )
    db.add(case)
    db.commit()
    ver = FDRVersion(case_id=case.id, version_number=1)
    db.add(ver)
    db.commit()
    case.current_version_id = ver.id
    db.commit()

    token = create_access_token({"sub": user.id, "role": user.role, "email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(f"/api/v1/trust/cases/{case.id}/risk-score", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data
    assert "risk_level" in data
    assert "top_reasons_json" in data
    assert len(data["top_reasons_json"]) == 3
