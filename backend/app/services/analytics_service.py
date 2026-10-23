from datetime import datetime, timezone
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy.orm import Session

from app.models.entities import FDRCase, TrustLevel, CaseStatus


def compute_liability_forecast(db: Session, months_ahead: int = 24) -> Dict[str, Any]:
    """
    Computes monthly liability forecast using Pandas:
    Aggregates maturing deposit amounts per month, split by Trust Ladder level (L1, L2, L3, L4).
    """
    cases = db.query(FDRCase).filter(
        FDRCase.status.in_([CaseStatus.SUBMITTED, CaseStatus.UNDER_REVIEW, CaseStatus.VERIFIED, CaseStatus.SEALED, CaseStatus.RELEASE_REQUESTED])
    ).all()

    if not cases:
        return {
            "total_active_liability": 0.0,
            "total_cases": 0,
            "monthly_forecast": [],
            "trust_split": {}
        }

    data = []
    for c in cases:
        data.append({
            "id": c.id,
            "fdr_number": c.fdr_number,
            "principal": float(c.principal_amount),
            "maturity_amount": float(c.maturity_amount),
            "trust_level": c.trust_level,
            "maturity_date": c.maturity_date
        })

    df = pd.DataFrame(data)
    df["maturity_date"] = pd.to_datetime(df["maturity_date"])
    df["year_month"] = df["maturity_date"].dt.strftime("%Y-%m")

    # Group by month and trust level
    monthly_pivot = df.pivot_table(
        index="year_month",
        columns="trust_level",
        values="maturity_amount",
        aggfunc="sum",
        fill_value=0.0
    ).reset_index()

    # Ensure all trust level columns exist
    for lvl in [TrustLevel.L1_DECLARED, TrustLevel.L2_MACHINE_CHECKED, TrustLevel.L3_SOURCE_VERIFIED, TrustLevel.L4_SEALED]:
        if lvl not in monthly_pivot.columns:
            monthly_pivot[lvl] = 0.0

    monthly_pivot["total_maturing"] = (
        monthly_pivot[TrustLevel.L1_DECLARED] +
        monthly_pivot[TrustLevel.L2_MACHINE_CHECKED] +
        monthly_pivot[TrustLevel.L3_SOURCE_VERIFIED] +
        monthly_pivot[TrustLevel.L4_SEALED]
    )

    monthly_forecast = []
    for _, row in monthly_pivot.sort_values("year_month").iterrows():
        monthly_forecast.append({
            "month": row["year_month"],
            "L1_DECLARED": round(float(row[TrustLevel.L1_DECLARED]), 2),
            "L2_MACHINE_CHECKED": round(float(row[TrustLevel.L2_MACHINE_CHECKED]), 2),
            "L3_SOURCE_VERIFIED": round(float(row[TrustLevel.L3_SOURCE_VERIFIED]), 2),
            "L4_SEALED": round(float(row[TrustLevel.L4_SEALED]), 2),
            "total": round(float(row["total_maturing"]), 2)
        })

    trust_split = df.groupby("trust_level")["maturity_amount"].sum().to_dict()

    return {
        "total_active_liability": round(float(df["maturity_amount"].sum()), 2),
        "total_cases": len(df),
        "monthly_forecast": monthly_forecast,
        "trust_split": {k: round(float(v), 2) for k, v in trust_split.items()}
    }
