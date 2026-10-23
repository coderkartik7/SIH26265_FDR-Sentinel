from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import get_settings, get_rules
from app.models.entities import FDRCase, Alert, RiskScore, TrustLevel, CaseStatus, User, UserRole
from app.services.audit_service import record_audit_event

settings = get_settings()


def get_effective_demo_time() -> datetime:
    """
    Returns current system time offset by DEMO_CLOCK_OFFSET_DAYS.
    Enables simulation of time jumps (e.g. forward 90 days) during hackathon evaluations.
    """
    offset = int(os.getenv("DEMO_CLOCK_OFFSET_DAYS", settings.DEMO_CLOCK_OFFSET_DAYS))
    return datetime.now(timezone.utc) + timedelta(days=offset)


import os


def set_demo_clock_offset(days: int) -> int:
    """Update global demo clock offset in days"""
    settings.DEMO_CLOCK_OFFSET_DAYS = days
    os.environ["DEMO_CLOCK_OFFSET_DAYS"] = str(days)
    return days


def scan_maturity_alerts_and_escalate(db: Session) -> Dict[str, Any]:
    """
    Daily scan (run by Celery Beat or on-demand):
    1. Scans FDRs at 90, 60, 30, 15, and 7 days to maturity relative to effective demo clock.
    2. Escalation engine: unacknowledged alerts > N days escalate to senior officials.
    3. High-risk FDRs (score >= 70) jump to CRITICAL priority.
    """
    rules = get_rules()
    alert_intervals = rules.get("alert_intervals_days", [90, 60, 30, 15, 7])
    escalation_cfg = rules.get("escalation", {})
    unack_days = int(escalation_cfg.get("unacknowledged_days_senior", 7))
    high_risk_priority = bool(escalation_cfg.get("high_risk_priority_escalation", True))

    current_time = get_effective_demo_time()
    active_cases = db.query(FDRCase).filter(
        FDRCase.status.in_([CaseStatus.SUBMITTED, CaseStatus.UNDER_REVIEW, CaseStatus.VERIFIED, CaseStatus.SEALED])
    ).all()

    new_alerts_count = 0
    escalations_count = 0

    for case in active_cases:
        # Calculate days to maturity relative to effective demo time
        mat_dt = case.maturity_date
        if not hasattr(mat_dt, "tzinfo") or mat_dt.tzinfo is None:
            mat_dt = mat_dt.replace(tzinfo=timezone.utc)
        days_remaining = (mat_dt - current_time).days

        # Check latest risk score if available
        is_high_risk = False
        current_version = next((v for v in case.versions if v.id == case.current_version_id), None)
        if current_version and current_version.risk_scores:
            latest_risk = sorted(current_version.risk_scores, key=lambda r: r.computed_at, reverse=True)[0]
            if latest_risk.score >= 70.0:
                is_high_risk = True

        # 1. Maturity intervals
        for interval in alert_intervals:
            if days_remaining <= interval and days_remaining > (interval - 15):
                alert_type = f"MATURITY_{interval}"
                # Check if this alert was already raised
                existing_alert = db.query(Alert).filter(
                    Alert.case_id == case.id,
                    Alert.alert_type == alert_type
                ).first()

                if not existing_alert:
                    sev = "HIGH" if (interval <= 15 or (is_high_risk and high_risk_priority)) else "MEDIUM"
                    msg = (
                        f"FDR #{case.fdr_number} ({case.bank_name}) is {days_remaining} days from maturity "
                        f"on {mat_dt.strftime('%d-%b-%Y')}. Principal: INR {case.principal_amount:,.2f}."
                    )
                    if is_high_risk:
                        msg += " [HIGH-RISK ESCALATION: Case has flagged anomalies]"

                    new_alert = Alert(
                        case_id=case.id,
                        alert_type=alert_type,
                        severity=sev,
                        message=msg,
                        is_acknowledged=False
                    )
                    db.add(new_alert)
                    new_alerts_count += 1

        # 2. Escalation Engine for Unacknowledged Alerts
        pending_alerts = db.query(Alert).filter(
            Alert.case_id == case.id,
            Alert.is_acknowledged == False,
            Alert.alert_type != "SENIOR_OFFICIAL_ESCALATION"
        ).all()

        for alert in pending_alerts:
            alert_created = alert.created_at
            if not hasattr(alert_created, "tzinfo") or alert_created.tzinfo is None:
                alert_created = alert_created.replace(tzinfo=timezone.utc)

            age_days = (current_time - alert_created).days
            if age_days >= unack_days:
                # Check if escalation already created
                esc_existing = db.query(Alert).filter(
                    Alert.case_id == case.id,
                    Alert.alert_type == "SENIOR_OFFICIAL_ESCALATION"
                ).first()

                if not esc_existing:
                    esc_alert = Alert(
                        case_id=case.id,
                        alert_type="SENIOR_OFFICIAL_ESCALATION",
                        severity="CRITICAL",
                        message=(
                            f"ESCALATION TO SENIOR OFFICIAL: Alert on FDR #{case.fdr_number} "
                            f"remained unacknowledged for {age_days} days. Immediate AICTE intervention required."
                        ),
                        is_acknowledged=False
                    )
                    db.add(esc_alert)
                    escalations_count += 1

    db.commit()

    return {
        "effective_demo_time": current_time.isoformat(),
        "offset_days": int(os.getenv("DEMO_CLOCK_OFFSET_DAYS", settings.DEMO_CLOCK_OFFSET_DAYS)),
        "active_cases_scanned": len(active_cases),
        "new_alerts_created": new_alerts_count,
        "escalations_created": escalations_count
    }


def acknowledge_alert(db: Session, alert_id: str, user_id: str) -> Alert:
    """Acknowledge an alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise ValueError(f"Alert #{alert_id} not found")

    alert.is_acknowledged = True
    alert.acknowledged_by_user_id = user_id
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert
