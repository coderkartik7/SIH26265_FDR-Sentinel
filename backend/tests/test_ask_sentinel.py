import pytest
from datetime import datetime, timezone
from app.models.entities import User, UserRole, Institution, FDRCase, TrustLevel, CaseStatus
from app.services.query_service import parse_natural_language_to_filters, execute_ask_sentinel_query
from app.core.security import create_access_token, hash_password


def test_parse_natural_language_to_filters():
    # 1. High risk question
    filters, summary = parse_natural_language_to_filters("Show all high risk flagged FDRs")
    assert any(f.field == "risk_score" and f.operator == "gte" and f.value == 70.0 for f in filters)
    assert "Risk score ≥ 70" in summary

    # 2. Bank and trust level
    filters, summary = parse_natural_language_to_filters("Show L4 sealed deposits from Apex Commercial Trust")
    assert any(f.field == "trust_level" and f.value == TrustLevel.L4_SEALED for f in filters)
    assert any(f.field == "bank_name" and f.value == "apex" for f in filters)

    # 3. Maturity within days
    filters, summary = parse_natural_language_to_filters("Find FDRs maturing in next 30 days")
    assert any(f.field == "days_to_maturity" and f.operator == "lte" and f.value == 30 for f in filters)


def test_ask_sentinel_role_scoping_and_execution(db):
    inst1 = Institution(id="INST-Q-1", name="Query College A", code="QC-01", region="Northern", city="Delhi", state="DL", contact_email="q1@q.edu")
    inst2 = Institution(id="INST-Q-2", name="Query College B", code="QC-02", region="Southern", city="Chennai", state="TN", contact_email="q2@q.edu")
    db.add_all([inst1, inst2])

    user_inst1 = User(email="user1@qc01.edu", hashed_password=hash_password("Pass123!"), full_name="User 1", role=UserRole.INSTITUTION, institution_id=inst1.id, is_active=True)
    user_official = User(email="official@aicte.gov.in", hashed_password=hash_password("Pass123!"), full_name="AICTE Official", role=UserRole.OFFICIAL, is_active=True)
    db.add_all([user_inst1, user_official])

    case1 = FDRCase(
        case_number="CASE-Q-1", institution_id=inst1.id, bank_name="Apex Commercial Trust",
        fdr_number="ACT-FD-DL-109551", principal_amount=1500000.0, maturity_amount=1800000.0,
        interest_rate=7.0, issue_date=datetime.now(timezone.utc), maturity_date=datetime(2027, 1, 1),
        tenure_months=36, trust_level=TrustLevel.L4_SEALED, status=CaseStatus.SEALED
    )
    case2 = FDRCase(
        case_number="CASE-Q-2", institution_id=inst2.id, bank_name="Bharosa National Bank",
        fdr_number="BNB-2024-NDL-59552", principal_amount=2500000.0, maturity_amount=3000000.0,
        interest_rate=7.2, issue_date=datetime.now(timezone.utc), maturity_date=datetime(2027, 1, 1),
        tenure_months=36, trust_level=TrustLevel.L4_SEALED, status=CaseStatus.SEALED
    )
    db.add_all([case1, case2])
    db.commit()

    # Query by Institution 1 user -> Must only return Case 1
    res_inst = execute_ask_sentinel_query(db, user_inst1, "Show all sealed FDRs")
    assert res_inst.results_count == 1
    assert res_inst.results[0]["fdr_number"] == "ACT-FD-DL-109551"

    # Query by Official user -> Can see both
    res_off = execute_ask_sentinel_query(db, user_official, "Show all sealed FDRs")
    assert res_off.results_count >= 2


def test_ask_sentinel_api_endpoint(client, db):
    user = User(email="ask_api_user@aicte.gov.in", hashed_password=hash_password("Pass123!"), full_name="Official", role=UserRole.OFFICIAL, is_active=True)
    db.add(user)
    db.commit()

    token = create_access_token({"sub": user.id, "role": user.role, "email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/v1/ask-sentinel", json={"question": "Show all FDRs from Apex bank"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "interpreted_filters" in data
    assert "summary_text" in data
    assert data["is_rule_fallback"] is True
