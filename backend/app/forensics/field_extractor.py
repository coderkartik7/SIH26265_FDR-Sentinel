import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from dateutil import parser as date_parser
from app.core.config import get_rules


def parse_clean_amount(text: str) -> Optional[float]:
    """Extract numeric amount from strings like 'INR 35,00,000.00' or 'Rs 500000'"""
    # Remove currency prefixes and commas
    cleaned = re.sub(r'[^\d.]', '', text)
    try:
        val = float(cleaned)
        return val
    except Exception:
        return None


def extract_structured_fields(raw_text: str, base_confidence: float = 0.95) -> Dict[str, Any]:
    """
    Parse raw OCR or stream text into structured FDR fields using regex and rules from config.
    Returns dictionary with extracted field values, confidences, and manual review flags.
    """
    rules = get_rules()
    banks = rules.get("fictional_banks", [])
    institutions = rules.get("fictional_institutions", [])

    fields: Dict[str, Dict[str, Any]] = {}

    # 1. Bank Extraction
    detected_bank = None
    for b in banks:
        if b["name"].lower() in raw_text.lower() or b["short_code"].lower() in raw_text.lower():
            detected_bank = b["name"]
            break
    fields["bank_name"] = {
        "value": detected_bank,
        "confidence": 0.98 if detected_bank else 0.40,
        "flagged": detected_bank is None
    }

    # 2. FDR Number Extraction
    detected_fdr_no = None
    for b in banks:
        pattern = b.get("pattern")
        if pattern:
            # Strip ^ and $ for searching within multi-line document text
            clean_pat = pattern.lstrip("^").rstrip("$")
            match = re.search(clean_pat, raw_text)
            if match:
                detected_fdr_no = match.group(0).strip()
                break

    if not detected_fdr_no:
        # Fallback pattern targeting explicit FDR / Certificate label
        match = re.search(r'(?:FDR Certificate No|Certificate No|FDR No)\s*[:.]?\s*([A-Z0-9\-_]{8,25})', raw_text, re.IGNORECASE)
        if match:
            detected_fdr_no = match.group(1).strip()

    fields["fdr_number"] = {
        "value": detected_fdr_no,
        "confidence": 0.95 if detected_fdr_no else 0.30,
        "flagged": detected_fdr_no is None
    }

    # 3. Institution Extraction
    detected_inst = None
    for inst in institutions:
        if inst["name"].lower() in raw_text.lower() or inst["code"].lower() in raw_text.lower():
            detected_inst = inst["name"]
            break
    fields["institution_name"] = {
        "value": detected_inst,
        "confidence": 0.95 if detected_inst else 0.40,
        "flagged": detected_inst is None
    }

    # 4. Principal Amount Extraction (figures)
    principal_amt = None
    amt_match = re.search(r'(?:Principal Deposit Amount|Principal Amount|Deposit Amount|INR|Rs\.?)\s*[:.]?\s*(?:INR|Rs\.?)?\s*([\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if amt_match:
        principal_amt = parse_clean_amount(amt_match.group(1))

    fields["principal_amount"] = {
        "value": str(principal_amt) if principal_amt is not None else None,
        "confidence": 0.92 if principal_amt else 0.35,
        "flagged": principal_amt is None
    }

    # 5. Amount in Words Extraction
    words_match = re.search(r'Amount in Words\s*[:.]?\s*([A-Za-z\s]+Only)', raw_text, re.IGNORECASE)
    words_val = words_match.group(1).strip() if words_match else None
    fields["amount_in_words"] = {
        "value": words_val,
        "confidence": 0.90 if words_val else 0.40,
        "flagged": words_val is None
    }

    # 6. Dates Extraction (Issue Date & Maturity Date)
    issue_dt = None
    issue_match = re.search(r'Issue Date\s*[:.]?\s*([0-9]{1,2}-[A-Za-z]{3,9}-[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', raw_text, re.IGNORECASE)
    if issue_match:
        try:
            issue_dt = date_parser.parse(issue_match.group(1), dayfirst=True)
        except Exception:
            pass

    fields["issue_date"] = {
        "value": issue_dt.strftime("%Y-%m-%d") if issue_dt else None,
        "confidence": 0.92 if issue_dt else 0.30,
        "flagged": issue_dt is None
    }

    maturity_dt = None
    mat_match = re.search(r'Maturity Date\s*[:.]?\s*([0-9]{1,2}-[A-Za-z]{3,9}-[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', raw_text, re.IGNORECASE)
    if mat_match:
        try:
            maturity_dt = date_parser.parse(mat_match.group(1), dayfirst=True)
        except Exception:
            pass

    fields["maturity_date"] = {
        "value": maturity_dt.strftime("%Y-%m-%d") if maturity_dt else None,
        "confidence": 0.92 if maturity_dt else 0.30,
        "flagged": maturity_dt is None
    }

    # 7. Tenure (Months)
    tenure_months = None
    tenure_match = re.search(r'(?:Tenure|Deposit Tenure)\s*[:.]?\s*(\d{1,3})\s*Months?', raw_text, re.IGNORECASE)
    if tenure_match:
        try:
            tenure_months = int(tenure_match.group(1))
        except Exception:
            pass
    elif issue_dt and maturity_dt:
        days = (maturity_dt - issue_dt).days
        tenure_months = round(days / 30.4375)

    fields["tenure_months"] = {
        "value": str(tenure_months) if tenure_months else None,
        "confidence": 0.88 if tenure_months else 0.35,
        "flagged": tenure_months is None
    }

    # 8. Interest Rate
    interest_rate = None
    rate_match = re.search(r'Interest Rate[^\d]*(\d{1,2}(?:\.\d{1,2})?)\s*%', raw_text, re.IGNORECASE)
    if rate_match:
        try:
            interest_rate = float(rate_match.group(1))
        except Exception:
            pass

    fields["interest_rate"] = {
        "value": str(interest_rate) if interest_rate else None,
        "confidence": 0.90 if interest_rate else 0.40,
        "flagged": interest_rate is None
    }

    # 9. Maturity Value
    maturity_val = None
    mat_val_match = re.search(r'Maturity Value\s*[:.]?\s*(?:INR|Rs\.?)?\s*([\d,]+(?:\.\d{2})?)', raw_text, re.IGNORECASE)
    if mat_val_match:
        maturity_val = parse_clean_amount(mat_val_match.group(1))

    fields["maturity_amount"] = {
        "value": str(maturity_val) if maturity_val is not None else None,
        "confidence": 0.90 if maturity_val else 0.35,
        "flagged": maturity_val is None
    }

    return fields
