from typing import Dict, Any
from sqlalchemy.orm import Session
from app.connectors.base import BaseVerificationConnector
from app.models.entities import FDRCase, FDRVersion, Document, IssuerLedger


class MockIssuerAdapter(BaseVerificationConnector):
    """
    Adapter 1: Mock Issuer Ledger Table
    Simulates core banking ledger integration (SFMS/CBS).
    NOTE (Honesty Rule 2): This adapter is SIMULATED and badged as such in the UI.
    """
    @property
    def adapter_name(self) -> str:
        return "MockIssuerAdapter"

    @property
    def is_simulated(self) -> bool:
        return True

    def verify(
        self,
        fdr_case: FDRCase,
        version: FDRVersion,
        document: Document,
        db: Session
    ) -> Dict[str, Any]:
        clean_num = fdr_case.fdr_number.strip().upper()
        ledger_row = db.query(IssuerLedger).filter(
            IssuerLedger.fdr_number.ilike(clean_num)
        ).first()

        if not ledger_row:
            return {
                "is_verified": False,
                "is_simulated": True,
                "badge": "SIMULATED ISSUER",
                "notes": f"Certificate #{fdr_case.fdr_number} not found in issuing bank central ledger.",
                "raw_response": {"found": False, "fdr_number": clean_num}
            }

        # Check status and matching amounts
        if ledger_row.status == "RELEASED":
            return {
                "is_verified": False,
                "is_simulated": True,
                "badge": "SIMULATED ISSUER",
                "notes": "Bank ledger confirms this FDR was previously released/liquidated.",
                "raw_response": {
                    "found": True,
                    "ledger_status": ledger_row.status,
                    "fdr_number": clean_num
                }
            }

        amt_diff = abs(ledger_row.principal_amount - fdr_case.principal_amount)
        if amt_diff > 1.0:
            return {
                "is_verified": False,
                "is_simulated": True,
                "badge": "SIMULATED ISSUER",
                "notes": f"Principal amount mismatch with issuing bank ledger: doc has {fdr_case.principal_amount} vs ledger {ledger_row.principal_amount}",
                "raw_response": {
                    "found": True,
                    "ledger_principal": ledger_row.principal_amount,
                    "submitted_principal": fdr_case.principal_amount
                }
            }

        return {
            "is_verified": True,
            "is_simulated": True,
            "badge": "SIMULATED ISSUER",
            "notes": "Bank core ledger confirms active fixed deposit under AICTE lien.",
            "raw_response": {
                "found": True,
                "ledger_status": ledger_row.status,
                "bank_name": ledger_row.bank_name,
                "principal": ledger_row.principal_amount,
                "maturity_date": ledger_row.maturity_date.strftime("%Y-%m-%d")
            }
        }
