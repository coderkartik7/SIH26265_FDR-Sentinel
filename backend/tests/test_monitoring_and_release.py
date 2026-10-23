import os
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.models.entities import (
    User, UserRole, Institution, FDRCase, FDRVersion,
    Alert, ReleaseRequest, TrustLevel, CaseStatus, IssuerLedger
)
from app.services.alert_service import (
    scan_maturity_alerts_and_escalate,
    set_demo_clock_offset,
    get_effective_demo_time
)
from app.services.release_service import (
    evaluate_release_eligibility,
    create_release_request,
    approve_and_finalize_release
)
from app.services.analytics_service import compute_liability_forecast
from app.core.security import hash_password


def test_demo_clock_and_maturity_alerts_triggering(db):
    inst = Institution(id="INST-MON-1", name="Maturity College", code="MC-01", region="Northern", city="Delhi", state="DL", contact_email="mc@mc.edu")
    db.add(inst)

    # Base date: today + 35 days
    future_date = datetime.now(timezone.utc) + timedelta(days=35)

    case = FDRCase(
        case_number="CASE-2026-MAT-1",
        institution_id=inst.id,
        bank_name="Bharosa National Bank",
        fdr_number="BNB-2024-NDL-59999",
        principal_amount=1000000.0,
        maturity_amount=1250000.0,
        interest_rate=7.5,
        issue_date=datetime.now(timezone.utc) - timedelta(days=330),
        maturity_date=future_date,
        tenure_months=12,
        trust_level=TrustLevel.L2_MACHINE_CHECKED,
        status=CaseStatus.VERIFIED
    )
    db.add(case)
    db.commit()

    # Initial scan at offset 0 (35 days to maturity -> falls in 60-day interval)
    set_demo_clock_offset(0)
    res_0 = scan_maturity_alerts_and_escalate(db)

    # Now simulate jumping clock forward by 10 days (now 25 days to maturity -> MATURITY_30 triggers)
    set_demo_clock_offset(10)
    res_10 = scan_maturity_alerts_and_escalate(db)
    assert res_10["new_alerts_created"] >= 1

    alerts = db.query(Alert).filter(Alert.case_id == case.id).all()
    alert_types = [a.alert_type for a in alerts]
    assert "MATURITY_30" in alert_types

    # Reset offset
    set_demo_clock_offset(0)


def test_escalation_engine_for_unacknowledged_alerts(db):
    inst = Institution(id="INST-ESC-1", name="Escalation College", code="EC-01", region="Southern", city="Mysuru", state="KA", contact_email="ec@ec.edu")
    db.add(inst)

    case = FDRCase(
        case_number="CASE-2026-ESC-1",
        institution_id=inst.id,
        bank_name="Citadel Rural & Urban Bank",
        fdr_number="CRUB100999999X",
        principal_amount=500000.0,
        maturity_amount=600000.0,
        interest_rate=7.0,
        issue_date=datetime.now(timezone.utc) - timedelta(days=350),
        maturity_date=datetime.now(timezone.utc) + timedelta(days=15),
        tenure_months=12,
        trust_level=TrustLevel.L2_MACHINE_CHECKED,
        status=CaseStatus.VERIFIED
    )
    db.add(case)
    db.commit()

    # Manually seed an unacknowledged alert created 8 days ago
    stale_alert = Alert(
        case_id=case.id,
        alert_type="MATURITY_15",
        severity="MEDIUM",
        message="Stale alert pending review",
        is_acknowledged=False,
        created_at=datetime.now(timezone.utc) - timedelta(days=8)
    )
    db.add(stale_alert)
    db.commit()

    # Run escalation engine
    set_demo_clock_offset(0)
    res = scan_maturity_alerts_and_escalate(db)
    assert res["escalations_created"] >= 1

    esc_alerts = db.query(Alert).filter(
        Alert.case_id == case.id,
        Alert.alert_type == "SENIOR_OFFICIAL_ESCALATION"
    ).all()
    assert len(esc_alerts) == 1
    assert esc_alerts[0].severity == "CRITICAL"


def test_release_eligibility_and_closure_report(db):
    inst = Institution(id="INST-REL-1", name="Release College", code="RC-01", region="Western", city="Panaji", state="GA", contact_email="rc@rc.edu")
    db.add(inst)

    official = User(
        email="release_officer@aicte.gov.in",
        hashed_password=hash_password("Pass123!"),
        full_name="Release Officer",
        role=UserRole.OFFICIAL,
        is_active=True
    )
    db.add(official)

    past_date = datetime.now(timezone.utc) - timedelta(days=5)

    case = FDRCase(
        case_number="CASE-2026-REL-1",
        institution_id=inst.id,
        bank_name="Apex Commercial Trust",
        fdr_number="ACT-FD-DL-109888",
        principal_amount=3000000.0,
        maturity_amount=3600000.0,
        interest_rate=7.1,
        issue_date=datetime.now(timezone.utc) - timedelta(days=735),
        maturity_date=past_date,
        tenure_months=24,
        trust_level=TrustLevel.L4_SEALED, # Eligible: Sealed at L4
        status=CaseStatus.SEALED
    )
    db.add(case)

    # Mock issuer ledger entry
    ledger = IssuerLedger(
        bank_id="ACT",
        bank_name="Apex Commercial Trust",
        fdr_number="ACT-FD-DL-109888",
        institution_name="Release College",
        principal_amount=3000000.0,
        maturity_amount=3600000.0,
        interest_rate=7.1,
        issue_date=datetime.now(timezone.utc) - timedelta(days=735),
        maturity_date=past_date,
        status="ACTIVE"
    )
    db.add(ledger)
    db.commit()

    ver = FDRVersion(case_id=case.id, version_number=1)
    db.add(ver)
    db.commit()
    case.current_version_id = ver.id
    db.commit()

    # 1. Check eligibility
    elig = evaluate_release_eligibility(db, case)
    assert elig["all_eligible"] is True
    assert elig["checklist"]["CHECK_TRUST_L4"]["passed"] is True
    assert elig["checklist"]["CHECK_MATURITY"]["passed"] is True

    # 2. Initiate release request
    rel_req = create_release_request(db, case.id, inst.id, user_id=official.id)
    assert rel_req.status == "SUBMITTED"

    # 3. Official approves release -> Generates Closure Report PDF & closes case
    fin_res = approve_and_finalize_release(db, rel_req.id, official)
    assert fin_res["status"] == "RELEASED"
    assert Path(fin_res["closure_report_path"]).exists()

    db.refresh(case)
    assert case.status == CaseStatus.RELEASED

    db.refresh(ledger)
    assert ledger.status == "RELEASED"


def test_pandas_liability_forecast(db):
    inst = Institution(id="INST-FC-1", name="Forecast College", code="FC-01", region="Northern", city="Jaipur", state="RJ", contact_email="fc@fc.edu")
    db.add(inst)

    c1 = FDRCase(
        case_number="CASE-FC-1", institution_id=inst.id, bank_name="ACT",
        fdr_number="ACT-FD-DL-109771", principal_amount=1000000.0, maturity_amount=1200000.0,
        interest_rate=7.0, issue_date=datetime.now(timezone.utc),
        maturity_date=datetime(2027, 3, 15, tzinfo=timezone.utc), tenure_months=12,
        trust_level=TrustLevel.L2_MACHINE_CHECKED, status=CaseStatus.VERIFIED
    )
    c2 = FDRCase(
        case_number="CASE-FC-2", institution_id=inst.id, bank_name="BNB",
        fdr_number="BNB-2024-NDL-59772", principal_amount=2000000.0, maturity_amount=2400000.0,
        interest_rate=7.2, issue_date=datetime.now(timezone.utc),
        maturity_date=datetime(2027, 3, 20, tzinfo=timezone.utc), tenure_months=12,
        trust_level=TrustLevel.L4_SEALED, status=CaseStatus.SEALED
    )
    db.add_all([c1, c2])
    db.commit()

    forecast = compute_liability_forecast(db, months_ahead=24)
    assert forecast["total_active_liability"] >= 3600000.0
    assert len(forecast["monthly_forecast"]) > 0

    march_2027 = next((m for m in forecast["monthly_forecast"] if m["month"] == "2027-03"), None)
    assert march_2027 is not None
    assert march_2027["L2_MACHINE_CHECKED"] == 1200000.0
    assert march_2027["L4_SEALED"] == 2400000.0
    assert march_2027["total"] == 3600000.0
