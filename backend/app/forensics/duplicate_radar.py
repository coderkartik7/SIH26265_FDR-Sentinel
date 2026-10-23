import hashlib
import difflib
from typing import Dict, Any, List, Optional
from PIL import Image
import imagehash
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.entities import FDRCase, FDRVersion, Document, DuplicateMatch, IssuerLedger
from app.core.config import get_rules


def compute_fdr_fingerprint(
    bank_name: Optional[str],
    fdr_number: Optional[str],
    principal_amount: Optional[float],
    issue_date_str: Optional[str]
) -> str:
    """
    Deterministic normalized SHA-256 fingerprint:
    SHA256(norm(bank) : norm(fdr_number) : norm(amount) : norm(issue_date))
    """
    b = (bank_name or "").strip().upper()
    f = (fdr_number or "").strip().upper()
    a = f"{float(principal_amount):.2f}" if principal_amount is not None else "0.00"
    d = (issue_date_str or "").strip()
    raw = f"{b}:{f}:{a}:{d}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compute_page_phash(pil_image: Image.Image) -> str:
    """Compute perceptual hash (pHash) of first document page"""
    hash_obj = imagehash.phash(pil_image)
    return str(hash_obj)


def calculate_phash_distance(hash1_str: str, hash2_str: str) -> int:
    """Compute Hamming distance between two hex pHash strings"""
    try:
        h1 = imagehash.hex_to_hash(hash1_str)
        h2 = imagehash.hex_to_hash(hash2_str)
        return h1 - h2
    except Exception:
        return 999


def scan_for_duplicates(
    db: Session,
    primary_case: FDRCase,
    fingerprint: str,
    phash_str: Optional[str],
    extracted_fields: Dict[str, Any]
) -> List[DuplicateMatch]:
    """
    Duplicate Radar multi-vector scan:
    1. Exact Fingerprint
    2. Cross-Institution Reuse
    3. Post-Release Resubmission (check mock IssuerLedger for RELEASED status)
    4. Perceptual Visual Duplicate (pHash Hamming distance <= threshold)
    5. Fuzzy FDR Number Match
    """
    matches: List[DuplicateMatch] = []
    rules = get_rules()
    dup_rules = rules.get("duplicate_radar", {})
    phash_threshold = int(dup_rules.get("phash_max_distance", 10))

    fdr_num = primary_case.fdr_number.strip().upper()
    inst_id = primary_case.institution_id

    # 1. Post-Release Resubmission Check against Issuer Ledger
    ledger_entry = db.query(IssuerLedger).filter(
        IssuerLedger.fdr_number.ilike(fdr_num)
    ).first()

    if ledger_entry and ledger_entry.status == "RELEASED":
        matches.append(DuplicateMatch(
            primary_case_id=primary_case.id,
            matching_case_id=primary_case.id, # Self or origin
            match_type="POST_RELEASE_REPRESENT",
            similarity_score=1.0,
            evidence_json={
                "fdr_number": fdr_num,
                "ledger_status": "RELEASED",
                "issuer_bank": ledger_entry.bank_name,
                "notes": "Anomaly for human review: This FDR was previously recorded as released/closed in the issuer ledger."
            },
            status="DETECTED"
        ))

    # Query other cases in the system (excluding current case)
    other_cases = db.query(FDRCase).filter(FDRCase.id != primary_case.id).all()

    for candidate in other_cases:
        cand_fdr = candidate.fdr_number.strip().upper()
        evidence = {
            "primary": {
                "case_id": primary_case.id,
                "fdr_number": primary_case.fdr_number,
                "institution_id": primary_case.institution_id,
                "bank": primary_case.bank_name,
                "principal": primary_case.principal_amount,
                "issue_date": primary_case.issue_date.strftime("%Y-%m-%d")
            },
            "candidate": {
                "case_id": candidate.id,
                "fdr_number": candidate.fdr_number,
                "institution_id": candidate.institution_id,
                "bank": candidate.bank_name,
                "principal": candidate.principal_amount,
                "issue_date": candidate.issue_date.strftime("%Y-%m-%d")
            }
        }

        # Check: Cross-Institution Reuse (Exact or identical FDR claimed by different college)
        if cand_fdr == fdr_num and candidate.institution_id != inst_id:
            matches.append(DuplicateMatch(
                primary_case_id=primary_case.id,
                matching_case_id=candidate.id,
                match_type="CROSS_INSTITUTION_REUSE",
                similarity_score=1.0,
                evidence_json=evidence,
                status="DETECTED"
            ))
            continue

        # Check: Exact Number Match within same institution
        if cand_fdr == fdr_num:
            matches.append(DuplicateMatch(
                primary_case_id=primary_case.id,
                matching_case_id=candidate.id,
                match_type="EXACT_FINGERPRINT",
                similarity_score=1.0,
                evidence_json=evidence,
                status="DETECTED"
            ))
            continue

        # Check: Fuzzy String Match on FDR Number
        sim_ratio = difflib.SequenceMatcher(None, fdr_num, cand_fdr).ratio()
        if sim_ratio >= 0.85:
            fuzzy_ev = evidence.copy()
            fuzzy_ev["similarity_ratio"] = round(sim_ratio, 3)
            matches.append(DuplicateMatch(
                primary_case_id=primary_case.id,
                matching_case_id=candidate.id,
                match_type="FUZZY_FDR_NUMBER",
                similarity_score=round(sim_ratio, 3),
                evidence_json=fuzzy_ev,
                status="DETECTED"
            ))

    return matches
