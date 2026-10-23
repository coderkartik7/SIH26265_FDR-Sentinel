import io
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.connectors.base import BaseVerificationConnector
from app.models.entities import FDRCase, FDRVersion, Document
from app.services.storage_service import retrieve_and_decrypt_document
from app.forensics.checks import check_pdf_digital_signature


class SignatureAdapter(BaseVerificationConnector):
    """
    Adapter 3: PDF Digital Signature Adapter
    Real pyHanko CMS digital signature verification against our synthetic test CA.
    is_simulated = False
    """
    @property
    def adapter_name(self) -> str:
        return "SignatureAdapter"

    @property
    def is_simulated(self) -> bool:
        return False

    def verify(
        self,
        fdr_case: FDRCase,
        version: FDRVersion,
        document: Document,
        db: Session
    ) -> Dict[str, Any]:
        if document.mime_type != "application/pdf":
            return {
                "is_verified": False,
                "is_simulated": False,
                "notes": "Non-PDF documents cannot contain embedded pyHanko CMS digital signatures.",
                "raw_response": {"is_pdf": False}
            }

        try:
            doc_bytes = retrieve_and_decrypt_document(document.storage_path, expected_sha256=document.sha256_hash)
        except Exception as e:
            return {
                "is_verified": False,
                "is_simulated": False,
                "notes": f"Unable to retrieve document content: {str(e)}",
                "raw_response": {"error": str(e)}
            }
        res = check_pdf_digital_signature(doc_bytes)

        ev = res.get("evidence_json", {})
        sig_status = ev.get("status")

        if sig_status == "valid":
            return {
                "is_verified": True,
                "is_simulated": False,
                "notes": "Document holds a cryptographically valid CMS digital signature verified against synthetic test CA.",
                "raw_response": ev
            }
        elif sig_status == "invalid":
            return {
                "is_verified": False,
                "is_simulated": False,
                "notes": "PDF digital signature failed cryptographic verification: byte tampering detected.",
                "raw_response": ev
            }
        else:
            return {
                "is_verified": False,
                "is_simulated": False,
                "notes": "Document does not possess an embedded digital signature.",
                "raw_response": ev
            }
