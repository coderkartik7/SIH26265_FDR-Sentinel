import io
import json
from typing import Dict, Any
from sqlalchemy.orm import Session
from PIL import Image
import cv2
import numpy as np

from app.connectors.base import BaseVerificationConnector
from app.models.entities import FDRCase, FDRVersion, Document
from app.services.storage_service import retrieve_and_decrypt_document
from app.forensics.preprocessor import pdf_bytes_to_images
from datagen.crypto_utils import verify_qr_payload


class QRAdapter(BaseVerificationConnector):
    """
    Adapter 2: Cryptographic QR Adapter
    Real cryptographic Ed25519 signature verification on the signed QR payload envelope.
    is_simulated = False
    """
    @property
    def adapter_name(self) -> str:
        return "QRAdapter"

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
        try:
            doc_bytes = retrieve_and_decrypt_document(document.storage_path, expected_sha256=document.sha256_hash)
        except Exception as e:
            return {
                "is_verified": False,
                "is_simulated": False,
                "notes": f"Unable to retrieve document content: {str(e)}",
                "raw_response": {"error": str(e)}
            }
        if document.mime_type == "application/pdf":
            page_images = pdf_bytes_to_images(doc_bytes, dpi=180)
            pil_img = page_images[0] if page_images else Image.new("RGB", (800, 1100), "white")
        else:
            pil_img = Image.open(io.BytesIO(doc_bytes)).convert("RGB")

        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(cv_img)

        if not data:
            return {
                "is_verified": False,
                "is_simulated": False,
                "notes": "No machine-readable QR code detected on the document.",
                "raw_response": {"qr_found": False}
            }

        try:
            envelope = json.loads(data)
        except Exception:
            return {
                "is_verified": False,
                "is_simulated": False,
                "notes": "QR payload is malformed or not standard signed envelope.",
                "raw_response": {"qr_found": True, "valid_json": False}
            }

        # Real Ed25519 signature check
        valid_sig = verify_qr_payload(envelope)
        if not valid_sig:
            return {
                "is_verified": False,
                "is_simulated": False,
                "notes": "Cryptographic signature in QR envelope failed Ed25519 verification.",
                "raw_response": {"signature_valid": False, "alg": envelope.get("alg")}
            }

        qr_data = envelope.get("data", {})
        qr_fdr = qr_data.get("fdr_no", "").strip().upper()
        doc_fdr = fdr_case.fdr_number.strip().upper()

        if qr_fdr != doc_fdr:
            return {
                "is_verified": False,
                "is_simulated": False,
                "notes": f"QR certificate number ({qr_fdr}) does not match document ({doc_fdr}).",
                "raw_response": {"signature_valid": True, "qr_fdr": qr_fdr, "doc_fdr": doc_fdr}
            }

        return {
            "is_verified": True,
            "is_simulated": False,
            "notes": "Cryptographic Ed25519 signature verified on QR payload. Data matches document.",
            "raw_response": {
                "signature_valid": True,
                "algorithm": envelope.get("alg"),
                "issuer": envelope.get("iss"),
                "payload": qr_data
            }
        }
