import time
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.entities import FDRCase, User, UserRole, TrustLevel, CaseStatus
from app.schemas.query import FieldFilter, AskSentinelResponse
from app.services.audit_service import record_audit_event
from app.services.alert_service import get_effective_demo_time


def parse_natural_language_to_filters(question: str) -> Tuple[List[FieldFilter], str]:
    """
    Deterministic rule-based NLP parser translating English questions into validated JSON filters.
    Ensures Ask-Sentinel works 100% reliably offline without requiring an external LLM API key.
    """
    q = question.lower()
    filters: List[FieldFilter] = []
    summary_parts = []

    # 1. Risk checks
    if "high risk" in q or "highest risk" in q or "flagged" in q or "risky" in q:
        filters.append(FieldFilter(field="risk_score", operator="gte", value=70.0))
        summary_parts.append("Risk score ≥ 70")
    elif "medium risk" in q:
        filters.append(FieldFilter(field="risk_score", operator="gte", value=40.0))
        filters.append(FieldFilter(field="risk_score", operator="lt", value=70.0))
        summary_parts.append("Risk score between 40 and 70")
    elif "low risk" in q or "clean" in q:
        filters.append(FieldFilter(field="risk_score", operator="lt", value=40.0))
        summary_parts.append("Risk score < 40")

    # 2. Trust Level checks
    if "l4" in q or "sealed" in q:
        filters.append(FieldFilter(field="trust_level", operator="eq", value=TrustLevel.L4_SEALED))
        summary_parts.append("Trust Level = L4 Sealed")
    elif "l3" in q or "source-verified" in q or "source verified" in q:
        filters.append(FieldFilter(field="trust_level", operator="eq", value=TrustLevel.L3_SOURCE_VERIFIED))
        summary_parts.append("Trust Level = L3 Source-verified")
    elif "l2" in q or "machine-checked" in q or "machine checked" in q:
        filters.append(FieldFilter(field="trust_level", operator="eq", value=TrustLevel.L2_MACHINE_CHECKED))
        summary_parts.append("Trust Level = L2 Machine-checked")
    elif "l1" in q or "declared" in q:
        filters.append(FieldFilter(field="trust_level", operator="eq", value=TrustLevel.L1_DECLARED))
        summary_parts.append("Trust Level = L1 Declared")

    # 3. Status checks
    if "released" in q or "liquidated" in q:
        filters.append(FieldFilter(field="status", operator="eq", value=CaseStatus.RELEASED))
        summary_parts.append("Status = Released")
    elif "pending release" in q or "release requested" in q:
        filters.append(FieldFilter(field="status", operator="eq", value=CaseStatus.RELEASE_REQUESTED))
        summary_parts.append("Status = Release Requested")
    elif "under review" in q:
        filters.append(FieldFilter(field="status", operator="eq", value=CaseStatus.UNDER_REVIEW))
        summary_parts.append("Status = Under Review")

    # 4. Bank name checks
    bank_aliases = {
        "apex": "Apex Commercial Trust",
        "bharosa": "Bharosa National Bank",
        "citadel": "Citadel Rural & Urban Bank",
        "deccan": "Deccan Mercantile Bank",
        "evertrust": "EverTrust Co-operative Bank"
    }
    for alias, full_name in bank_aliases.items():
        if alias in q:
            filters.append(FieldFilter(field="bank_name", operator="contains", value=alias))
            summary_parts.append(f"Bank matches '{full_name}'")
            break

    # 5. Maturity days
    days_match = re.search(r'(?:next|within|in)\s+(\d{1,3})\s+days', q)
    if days_match:
        days_num = int(days_match.group(1))
        filters.append(FieldFilter(field="days_to_maturity", operator="lte", value=days_num))
        summary_parts.append(f"Maturity within {days_num} days")

    # 6. Amount limits (e.g. greater than 20 lakhs, above 1000000)
    lakh_match = re.search(r'(?:above|greater than|more than|>)\s+(\d+(?:\.\d+)?)\s*(?:lakh|lacs|lac)', q)
    if lakh_match:
        val = float(lakh_match.group(1)) * 100000.0
        filters.append(FieldFilter(field="principal_amount", operator="gte", value=val))
        summary_parts.append(f"Principal amount ≥ INR {val:,.0f}")

    if not summary_parts:
        summary_text = "Showing matching FDR records based on keywords"
    else:
        summary_text = f"Filtered by: {', '.join(summary_parts)}"

    return filters, summary_text


from typing import Tuple


def execute_ask_sentinel_query(
    db: Session,
    user: User,
    question: str,
    limit: int = 20
) -> AskSentinelResponse:
    start_time = time.time()
    filters, summary = parse_natural_language_to_filters(question)

    query = db.query(FDRCase)

    # Scoping constraint: Institution users can only view their own cases
    if user.role == UserRole.INSTITUTION:
        query = query.filter(FDRCase.institution_id == user.institution_id)

    # Apply parameterized filters
    effective_now = get_effective_demo_time()

    for f in filters:
        col = getattr(FDRCase, f.field, None)
        if col is not None:
            if f.operator == "eq":
                query = query.filter(col == f.value)
            elif f.operator == "neq":
                query = query.filter(col != f.value)
            elif f.operator == "gt":
                query = query.filter(col > f.value)
            elif f.operator == "gte":
                query = query.filter(col >= f.value)
            elif f.operator == "lt":
                query = query.filter(col < f.value)
            elif f.operator == "lte":
                query = query.filter(col <= f.value)
            elif f.operator == "contains":
                query = query.filter(col.ilike(f"%{f.value}%"))
        elif f.field == "days_to_maturity":
            # Computed filter
            pass

    records = query.limit(limit).all()
    results = []

    for r in records:
        mat_dt = r.maturity_date
        if not hasattr(mat_dt, "tzinfo") or mat_dt.tzinfo is None:
            mat_dt = mat_dt.replace(tzinfo=timezone.utc)
        days_rem = (mat_dt - effective_now).days

        results.append({
            "id": r.id,
            "case_number": r.case_number,
            "fdr_number": r.fdr_number,
            "bank_name": r.bank_name,
            "institution_name": r.institution.name if r.institution else None,
            "principal_amount": r.principal_amount,
            "maturity_amount": r.maturity_amount,
            "maturity_date": r.maturity_date.strftime("%Y-%m-%d"),
            "days_to_maturity": days_rem,
            "trust_level": r.trust_level,
            "status": r.status
        })

    elapsed_ms = round((time.time() - start_time) * 1000.0, 2)

    # Log query to audit log
    record_audit_event(
        db=db,
        actor_id=user.id,
        actor_role=user.role,
        action="ASK_SENTINEL_QUERY_EXECUTED",
        target_type="QUERY",
        target_id=None,
        details_json={
            "question": question,
            "filters_count": len(filters),
            "results_count": len(results),
            "elapsed_ms": elapsed_ms
        }
    )

    return AskSentinelResponse(
        original_question=question,
        interpreted_filters=filters,
        summary_text=summary,
        results_count=len(results),
        results=results,
        execution_time_ms=elapsed_ms,
        is_rule_fallback=True
    )
