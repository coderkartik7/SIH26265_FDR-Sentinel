from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.core.database import get_db
from app.models.entities import User, UserRole, Alert, ReleaseRequest, FDRCase
from app.schemas.fdr import AlertResponse, ReleaseRequestResponse, ReleaseRequestCreate
from app.api.deps import get_current_user, require_roles
from app.services.alert_service import (
    scan_maturity_alerts_and_escalate,
    set_demo_clock_offset,
    get_effective_demo_time,
    acknowledge_alert
)
from app.services.release_service import (
    create_release_request,
    approve_and_finalize_release,
    evaluate_release_eligibility
)
from app.services.analytics_service import compute_liability_forecast

router = APIRouter(prefix="/monitoring", tags=["Monitoring & Release"])


class DemoClockRequest(BaseModel):
    offset_days: int


@router.post("/demo-clock")
def update_demo_clock_offset(
    req: DemoClockRequest,
    current_user: User = Depends(require_roles([UserRole.OFFICIAL, UserRole.ADMIN]))
):
    """
    Simulate jumping the demo clock forward or backward in time (e.g. +90 days)
    to test maturity notifications and auto-escalations.
    """
    new_offset = set_demo_clock_offset(req.offset_days)
    effective = get_effective_demo_time()
    return {
        "status": "UPDATED",
        "offset_days": new_offset,
        "effective_time": effective.isoformat(),
        "notice": f"Demo clock offset set to {new_offset} days from real time."
    }


@router.post("/scan-alerts")
def run_maturity_scan(
    current_user: User = Depends(require_roles([UserRole.OFFICIAL, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Triggers maturity scanner and escalation engine across all active FDRs.
    """
    res = scan_maturity_alerts_and_escalate(db)
    return res


@router.get("/alerts", response_model=List[AlertResponse])
def get_alerts(
    acknowledged: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if acknowledged is not None:
        query = query.filter(Alert.is_acknowledged == acknowledged)

    # Institution users only see alerts on their own cases
    if current_user.role == UserRole.INSTITUTION:
        query = query.join(FDRCase).filter(FDRCase.institution_id == current_user.institution_id)

    alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()
    return alerts


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_case_alert(
    alert_id: str,
    current_user: User = Depends(require_roles([UserRole.OFFICIAL, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    try:
        updated = acknowledge_alert(db=db, alert_id=alert_id, user_id=current_user.id)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/release/request", response_model=ReleaseRequestResponse)
def submit_release_request(
    req: ReleaseRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    case = db.query(FDRCase).filter(FDRCase.id == req.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="FDR Case not found")

    if current_user.role == UserRole.INSTITUTION and case.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        rel_req = create_release_request(
            db=db,
            case_id=req.case_id,
            institution_id=case.institution_id,
            user_id=current_user.id
        )
        return rel_req
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/release/{request_id}/approve")
def approve_release(
    request_id: str,
    current_user: User = Depends(require_roles([UserRole.OFFICIAL, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    try:
        res = approve_and_finalize_release(db=db, release_request_id=request_id, official_user=current_user)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/release/{request_id}/report")
def download_closure_report(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req = db.query(ReleaseRequest).filter(ReleaseRequest.id == request_id).first()
    if not req or not req.closure_report_path:
        raise HTTPException(status_code=404, detail="Closure report not found")

    return FileResponse(
        path=req.closure_report_path,
        media_type="application/pdf",
        filename=f"AICTE_Closure_Report_{req.id[:8]}.pdf"
    )


@router.get("/liability-forecast")
def get_liability_forecast(
    months: int = Query(24, ge=6, le=60),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Maturing deposit volume per month split by Trust Level via Pandas.
    """
    forecast = compute_liability_forecast(db=db, months_ahead=months)
    return forecast
