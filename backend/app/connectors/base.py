from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import FDRCase, FDRVersion, Document


class BaseVerificationConnector(ABC):
    """
    Abstract interface for bank verification connectors.
    In production, this talks to Open Banking APIs / NPCI / SFMS.
    In Phase 1, we implement three adapters adhering strictly to Honesty Rule 2.
    """
    @property
    @abstractmethod
    def adapter_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_simulated(self) -> bool:
        """True if relying on mock issuer ledger; False if real cryptographic verification"""
        pass

    @abstractmethod
    def verify(
        self,
        fdr_case: FDRCase,
        version: FDRVersion,
        document: Document,
        db: Session
    ) -> Dict[str, Any]:
        """
        Verify FDR validity.
        Returns:
            is_verified: bool
            raw_response: dict
            notes: str
        """
        pass
