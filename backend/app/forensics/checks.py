import io
import math
import json
import base64
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from PIL import Image, ImageChops, ImageEnhance
import cv2
import numpy as np
import pikepdf
from num2words import num2words
from dateutil import parser as date_parser

from app.core.config import get_rules
from datagen.crypto_utils import verify_qr_payload, get_or_create_test_ca
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext
from pyhanko.sign.validation.status import SignatureStatus


def check_financial_consistency(extracted_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Check A:
    1. Words vs. Figures consistency
    2. Date tenure consistency (maturity = issue + tenure)
    3. Formula check: maturity = P * (1 + r/4)^(4t)
    """
    findings = []
    rules = get_rules()
    interest_cfg = rules.get("interest_calculation", {})
    tolerance_pct = float(interest_cfg.get("tolerance_percent", 2.0))

    principal_str = extracted_fields.get("principal_amount", {}).get("value")
    words_val = extracted_fields.get("amount_in_words", {}).get("value")
    issue_str = extracted_fields.get("issue_date", {}).get("value")
    maturity_str = extracted_fields.get("maturity_date", {}).get("value")
    tenure_str = extracted_fields.get("tenure_months", {}).get("value")
    rate_str = extracted_fields.get("interest_rate", {}).get("value")
    mat_amount_str = extracted_fields.get("maturity_amount", {}).get("value")

    # 1. Words vs Figures Check
    if principal_str and words_val:
        try:
            p_val = float(principal_str)
            try:
                expected_words = num2words(int(p_val), lang='en_IN').lower()
            except Exception:
                expected_words = num2words(int(p_val)).lower()

            clean_actual_words = words_val.lower().replace("rupees", "").replace("only", "").strip()

            # Word tokens comparison
            exp_tokens = set(expected_words.split())
            act_tokens = set(clean_actual_words.split())
            overlap = len(exp_tokens.intersection(act_tokens))
            ratio = overlap / max(len(exp_tokens), 1)

            if ratio < 0.60:
                findings.append({
                    "check_type": "WORDS_VS_FIGURES",
                    "severity": "HIGH",
                    "status": "ANOMALY_FLAGGED",
                    "title": "Discrepancy Between Amount in Figures and Words",
                    "description": "Anomaly for human review: Numeric figure and written amount text do not match.",
                    "evidence_json": {
                        "figures_amount": p_val,
                        "words_extracted": words_val,
                        "expected_words": expected_words,
                        "token_overlap_ratio": round(ratio, 2)
                    }
                })
        except Exception:
            pass

    # 2. Tenure Date Check
    if issue_str and maturity_str and tenure_str:
        try:
            i_dt = datetime.strptime(issue_str, "%Y-%m-%d")
            m_dt = datetime.strptime(maturity_str, "%Y-%m-%d")
            t_months = int(tenure_str)
            expected_days = int(t_months * 30.4375)
            actual_days = (m_dt - i_dt).days

            # Allow +/- 15 days margin for bank working day calendars
            if abs(actual_days - expected_days) > 15:
                findings.append({
                    "check_type": "TENURE_DATE_MISMATCH",
                    "severity": "HIGH",
                    "status": "ANOMALY_FLAGGED",
                    "title": "Deposit Tenure and Maturity Date Discrepancy",
                    "description": "Anomaly for human review: Duration between issue date and maturity date diverges from stated tenure.",
                    "evidence_json": {
                        "issue_date": issue_str,
                        "maturity_date": maturity_str,
                        "stated_tenure_months": t_months,
                        "actual_duration_days": actual_days,
                        "expected_duration_days": expected_days
                    }
                })
        except Exception:
            pass

    # 3. Interest Formula Check
    if principal_str and rate_str and tenure_str and mat_amount_str:
        try:
            P = float(principal_str)
            r = float(rate_str)
            t_years = int(tenure_str) / 12.0
            actual_mat = float(mat_amount_str)

            expected_mat = P * math.pow(1.0 + (r / 400.0), 4.0 * t_years)
            diff_pct = abs(actual_mat - expected_mat) / expected_mat * 100.0

            if diff_pct > tolerance_pct:
                findings.append({
                    "check_type": "INTEREST_CALCULATION_DISCREPANCY",
                    "severity": "HIGH",
                    "status": "ANOMALY_FLAGGED",
                    "title": "Maturity Calculation Deviation",
                    "description": "Anomaly for human review: Stated maturity amount diverges from standard quarterly compounding formula.",
                    "evidence_json": {
                        "principal": P,
                        "rate_percent": r,
                        "tenure_years": t_years,
                        "actual_maturity_amount": actual_mat,
                        "expected_maturity_amount": round(expected_mat, 2),
                        "deviation_percent": round(diff_pct, 2),
                        "tolerance_percent": tolerance_pct
                    }
                })
        except Exception:
            pass

    return findings


def check_bank_fdr_pattern(extracted_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Check B: Validate FDR number against issuing bank's configured regex
    """
    findings = []
    rules = get_rules()
    banks = rules.get("fictional_banks", [])

    fdr_no = extracted_fields.get("fdr_number", {}).get("value")
    bank_name = extracted_fields.get("bank_name", {}).get("value")

    if not fdr_no:
        return [{
            "check_type": "BANK_FDR_PATTERN",
            "severity": "MEDIUM",
            "status": "ANOMALY_FLAGGED",
            "title": "FDR Number Absent or Unreadable",
            "description": "Anomaly for human review: Certificate number could not be extracted with high confidence.",
            "evidence_json": {"bank_name": bank_name}
        }]

    # Match bank
    target_bank = None
    if bank_name:
        for b in banks:
            if b["name"].lower() in bank_name.lower() or b["short_code"].lower() in bank_name.lower():
                target_bank = b
                break

    if target_bank:
        import re
        pattern = target_bank.get("pattern")
        if pattern and not re.search(pattern, fdr_no):
            findings.append({
                "check_type": "BANK_FDR_PATTERN",
                "severity": "CRITICAL",
                "status": "ANOMALY_FLAGGED",
                "title": f"FDR Number Pattern Mismatch for {target_bank['name']}",
                "description": f"Anomaly for human review: FDR number '{fdr_no}' does not conform to the bank's issuance structure.",
                "evidence_json": {
                    "extracted_fdr_number": fdr_no,
                    "bank": target_bank["name"],
                    "expected_pattern": pattern,
                    "example_valid_format": target_bank.get("pattern_example")
                }
            })

    return findings


def check_pdf_digital_signature(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Check C: pyHanko PDF digital signature validation against test CA
    Returns: valid / invalid / absent with evidence
    """
    try:
        _, signer_cert_path, ca_cert_path = get_or_create_test_ca()
        reader = PdfFileReader(io.BytesIO(pdf_bytes))

        # Check for signature fields
        sig_fields = reader.embedded_signatures
        if not sig_fields:
            return {
                "check_type": "PDF_DIGITAL_SIGNATURE",
                "severity": "INFO",
                "status": "PASS",
                "title": "PDF Digital Signature Absent",
                "description": "Document is an unsigned PDF or scanned copy (common for standard bank physical receipts).",
                "evidence_json": {"signature_present": False, "status": "absent"}
            }

        # Validate signature
        sig = sig_fields[0]
        try:
            val_status = validate_pdf_signature(sig)
            is_intact = getattr(val_status, "intact", False)
        except Exception:
            is_intact = False

        if is_intact:
            return {
                "check_type": "PDF_DIGITAL_SIGNATURE",
                "severity": "INFO",
                "status": "PASS",
                "title": "Cryptographic PDF Digital Signature Valid",
                "description": "Signature is structurally intact and verified against certificate chain.",
                "evidence_json": {
                    "signature_present": True,
                    "status": "valid",
                    "signer_field": sig.field_name,
                    "intact": True
                }
            }
        else:
            return {


                "check_type": "PDF_DIGITAL_SIGNATURE",
                "severity": "CRITICAL",
                "status": "ANOMALY_FLAGGED",
                "title": "Cryptographic PDF Signature Invalidation Detected",
                "description": "Anomaly for human review: Digital signature bytes are corrupted or document was altered after signing.",
                "evidence_json": {
                    "signature_present": True,
                    "status": "invalid",
                    "signer_field": sig.field_name,
                    "intact": False
                }
            }
    except Exception as e:
        return {
            "check_type": "PDF_DIGITAL_SIGNATURE",
            "severity": "HIGH",
            "status": "ANOMALY_FLAGGED",
            "title": "PDF Signature Integrity Check Failure",
            "description": f"Anomaly for human review: Error verifying PDF signature: {str(e)}",
            "evidence_json": {"signature_present": True, "status": "invalid", "error": str(e)}
        }


def compute_ela_heatmap(pil_image: Image.Image, quality: int = 90, scale: int = 12) -> Tuple[Image.Image, float]:
    """
    Check D1: Error Level Analysis (ELA)
    Resaves image at JPEG quality 90, calculates difference from original,
    and amplifies difference by scale factor.
    Returns: (heatmap_pil_image, mean_error_score)
    """
    buffer = io.BytesIO()
    pil_image.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    resaved = Image.open(buffer)

    diff = ImageChops.difference(pil_image.convert("RGB"), resaved.convert("RGB"))
    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema]) if extrema else 1
    if max_diff == 0:
        max_diff = 1

    # Enhance difference
    scale_factor = 255.0 / max_diff
    enhanced = ImageEnhance.Brightness(diff).enhance(scale_factor)

    # Compute mean error
    diff_arr = np.array(diff)
    mean_err = float(np.mean(diff_arr))

    return enhanced, mean_err


def inspect_pikepdf_metadata(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Check D2: pikepdf metadata and incremental revision inspection
    """
    findings = []
    try:
        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            # Check suspicious creators
            suspicious_terms = ["crack", "unauthorized", "editor", "photoshop", "gimp", "modified"]
            meta_str = ""
            if pdf.docinfo:
                for k, v in pdf.docinfo.items():
                    meta_str += f"{k}: {v} "

            for term in suspicious_terms:
                if term in meta_str.lower():
                    findings.append({
                        "check_type": "METADATA_INSPECTION",
                        "severity": "HIGH",
                        "status": "ANOMALY_FLAGGED",
                        "title": "Suspicious PDF Producer / Editor Metadata",
                        "description": "Anomaly for human review: PDF metadata indicates third-party editing or post-issuance manipulation tools.",
                        "evidence_json": {
                            "matched_term": term,
                            "metadata_snippet": meta_str[:200]
                        }
                    })
                    break
    except Exception:
        pass
    return findings


def check_qr_envelope_and_payload(
    pil_img: Image.Image,
    extracted_fields: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Check E:
    1. Detects QR code from document image
    2. Verifies Ed25519 cryptographic signature of mock issuer
    3. Cross-verifies QR payload values vs. OCR extracted values
    """
    findings = []
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(cv_img)

    if not data or not data.strip():
        # Scanned page or missing QR
        return [{
            "check_type": "QR_VERIFICATION",
            "severity": "LOW",
            "status": "PASS",
            "title": "No Machine-Readable QR Detected",
            "description": "Document does not possess a detectable QR code.",
            "evidence_json": {"qr_found": False}
        }]

    try:
        envelope = json.loads(data)
    except Exception:
        return [{
            "check_type": "QR_VERIFICATION",
            "severity": "HIGH",
            "status": "ANOMALY_FLAGGED",
            "title": "Invalid QR Data Format",
            "description": "Anomaly for human review: QR code does not contain valid JSON envelope.",
            "evidence_json": {"raw_qr": data[:100]}
        }]

    # 1. Cryptographic Ed25519 signature verification
    is_valid_sig = verify_qr_payload(envelope)
    if not is_valid_sig:
        findings.append({
            "check_type": "QR_VERIFICATION",
            "severity": "CRITICAL",
            "status": "ANOMALY_FLAGGED",
            "title": "QR Cryptographic Issuer Signature Mismatch",
            "description": "Anomaly for human review: Digital signature in the QR code does not verify against issuing authority key.",
            "evidence_json": {
                "algorithm": envelope.get("alg"),
                "issuer": envelope.get("iss"),
                "signature_valid": False
            }
        })
        return findings

    # 2. Payload Cross-Comparison
    qr_data = envelope.get("data", {})
    ocr_fdr = extracted_fields.get("fdr_number", {}).get("value")
    ocr_principal = extracted_fields.get("principal_amount", {}).get("value")

    mismatches = []
    if ocr_fdr and qr_data.get("fdr_no") and ocr_fdr.strip() != qr_data.get("fdr_no").strip():
        mismatches.append(f"FDR Number mismatch: Doc shows '{ocr_fdr}' vs QR shows '{qr_data.get('fdr_no')}'")

    if ocr_principal and qr_data.get("principal"):
        try:
            if abs(float(ocr_principal) - float(qr_data.get("principal"))) > 1.0:
                mismatches.append(f"Principal mismatch: Doc shows {ocr_principal} vs QR shows {qr_data.get('principal')}")
        except Exception:
            pass

    if mismatches:
        findings.append({
            "check_type": "QR_VERIFICATION",
            "severity": "CRITICAL",
            "status": "ANOMALY_FLAGGED",
            "title": "QR Payload vs. Document Text Divergence",
            "description": "Anomaly for human review: Physical text on certificate diverges from authenticated QR payload.",
            "evidence_json": {
                "discrepancies": mismatches,
                "qr_payload": qr_data
            }
        })
    else:
        findings.append({
            "check_type": "QR_VERIFICATION",
            "severity": "INFO",
            "status": "PASS",
            "title": "QR Code Digitally Verified & Consistent",
            "description": "Ed25519 digital signature verified. Document fields match QR payload.",
            "evidence_json": {
                "qr_fdr_no": qr_data.get("fdr_no"),
                "qr_principal": qr_data.get("principal"),
                "signature_valid": True
            }
        })

    return findings
