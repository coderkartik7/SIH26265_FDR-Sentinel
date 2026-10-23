import os
import sys
import csv
import json
import random
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Ensure workspace and backend on path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "backend"))

import yaml
from datagen.crypto_utils import (
    get_or_create_ed25519_issuer_key,
    get_or_create_test_ca
)
from datagen.pdf_generator import (
    create_fdr_pdf,
    calculate_quarterly_maturity,
    format_inr_words
)
from datagen.tamper_engine import (
    apply_metadata_tamper,
    apply_signature_breaking_edit
)
from datagen.noise_engine import (
    convert_pdf_to_scanned_image
)

RULES_FILE = BASE_DIR / "config" / "rules.yaml"


def load_rules():
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def format_bank_fdr_number(bank_id: str, seq: int) -> str:
    """Generate valid FDR numbers strictly matching bank patterns in rules.yaml"""
    if bank_id == "ACT":
        return f"ACT-FD-DL-{100000 + seq}"
    elif bank_id == "BNB":
        return f"BNB-2024-NDL-{50000 + seq}"
    elif bank_id == "CRUB":
        return f"CRUB{100000000 + seq}X"
    elif bank_id == "DMB":
        return f"DMB-401-MH-{800000 + seq}"
    elif bank_id == "ETCB":
        return f"ETCB-DEP-{40000000 + seq}"
    return f"GEN-{bank_id}-{seq:06d}"


def generate_dataset(seed: int = 42, count: int = 150, output_dir: str = "datagen/out"):
    random.seed(seed)
    out_path = Path(output_dir)
    pdf_dir = out_path / "documents"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    rules = load_rules()
    banks = rules.get("fictional_banks", [])
    institutions = rules.get("fictional_institutions", [])

    print(f"[*] Initializing cryptographic test CA and Ed25519 issuer keys...")
    get_or_create_ed25519_issuer_key()
    get_or_create_test_ca()

    print(f"[*] Generating {count} synthetic FDRs with seed={seed}...")

    # Composition: 100 genuine, 25 tampered, 15 duplicates, 10 noisy-but-genuine
    num_genuine = 100
    num_tampered = 25
    num_duplicates = 15
    num_noisy = 10

    records = []
    issuer_ledger = []

    # Tenure options: 12, 24, 36, 60 months
    tenures = [12, 24, 36, 60]
    principals = [500000.0, 1000000.0, 1500000.0, 2000000.0, 2500000.0, 3500000.0, 5000000.0]

    fdr_seq = 1000
    base_date = datetime(2023, 1, 15)

    # -------------------------------------------------------------
    # 1. Genuine FDRs (100)
    # -------------------------------------------------------------
    print(f"[*] Generating {num_genuine} Genuine FDRs...")
    for i in range(num_genuine):
        fdr_seq += 1
        bank = random.choice(banks)
        inst = random.choice(institutions)
        fdr_num = format_bank_fdr_number(bank["id"], fdr_seq)

        principal = random.choice(principals)
        tenure = random.choice(tenures)
        rate_min, rate_max = bank.get("base_interest_rate_range", [6.5, 7.5])
        rate = round(random.uniform(rate_min, rate_max), 2)

        days_offset = random.randint(0, 500)
        issue_dt = base_date + timedelta(days=days_offset)
        # Approximate tenure in days (tenure_months * 30.4)
        maturity_dt = issue_dt + timedelta(days=int(tenure * 30.4375))
        mat_amount = calculate_quarterly_maturity(principal, rate, tenure)

        sign_pdf = (i % 3 == 0) # 1 in 3 genuine PDFs gets pyHanko digital signature
        filename = f"fdr_{i+1:03d}_{bank['id']}_{fdr_num}.pdf"
        filepath = pdf_dir / filename

        create_fdr_pdf(
            output_path=str(filepath),
            bank_info=bank,
            institution_info=inst,
            fdr_number=fdr_num,
            principal_amount=principal,
            tenure_months=tenure,
            interest_rate=rate,
            issue_date=issue_dt,
            maturity_date=maturity_dt,
            maturity_amount=mat_amount,
            sign_pdf=sign_pdf
        )

        records.append({
            "id": f"GEN-{i+1:03d}",
            "fdr_number": fdr_num,
            "bank_id": bank["id"],
            "institution_id": inst["id"],
            "label": "genuine",
            "tamper_type": "none",
            "is_duplicate": False,
            "duplicate_type": "none",
            "principal_amount": principal,
            "maturity_amount": mat_amount,
            "interest_rate": rate,
            "issue_date": issue_dt.strftime("%Y-%m-%d"),
            "maturity_date": maturity_dt.strftime("%Y-%m-%d"),
            "tenure_months": tenure,
            "file_path": filepath.resolve().relative_to(BASE_DIR.resolve()).as_posix(),
            "qr_signed": True,
            "pdf_signed": sign_pdf
        })

        issuer_ledger.append({
            "bank_id": bank["id"],
            "bank_name": bank["name"],
            "fdr_number": fdr_num,
            "institution_name": inst["name"],
            "principal_amount": principal,
            "maturity_amount": mat_amount,
            "interest_rate": rate,
            "issue_date": issue_dt.strftime("%Y-%m-%d"),
            "maturity_date": maturity_dt.strftime("%Y-%m-%d"),
            "status": "ACTIVE"
        })

    # -------------------------------------------------------------
    # 2. Tampered FDRs (25)
    # -------------------------------------------------------------
    print(f"[*] Generating {num_tampered} Tampered FDRs across 6 forensic anomaly categories...")
    tamper_types = [
        "edited_amount",
        "edited_date",
        "amount_words_mismatch",
        "pasted_region",
        "metadata_edited_after_signing",
        "signature_breaking_edit"
    ]

    for i in range(num_tampered):
        fdr_seq += 1
        t_type = tamper_types[i % len(tamper_types)]
        bank = random.choice(banks)
        inst = random.choice(institutions)
        fdr_num = format_bank_fdr_number(bank["id"], fdr_seq)

        principal = random.choice(principals)
        tenure = random.choice(tenures)
        rate = round(random.uniform(6.5, 8.0), 2)
        issue_dt = base_date + timedelta(days=random.randint(100, 400))
        maturity_dt = issue_dt + timedelta(days=int(tenure * 30.4375))
        mat_amount = calculate_quarterly_maturity(principal, rate, tenure)

        override_fig = None
        override_words = None
        override_issue = None
        override_mat = None
        pasted = False
        sign_pdf = False

        if t_type == "edited_amount":
            # Forged figure amount: e.g. inflated by 2x-3x
            forged_amt = principal * 2.5
            override_fig = f"INR {forged_amt:,.2f}"
        elif t_type == "edited_date":
            # Maturity date changed without changing tenure/rate
            override_mat = (issue_dt + timedelta(days=120)).strftime("%d-%b-%Y")
        elif t_type == "amount_words_mismatch":
            # Figures says principal, words says mismatched 85 Lakh
            override_words = "Rupees Eighty Five Lakh Only"
        elif t_type == "pasted_region":
            pasted = True
        elif t_type == "metadata_edited_after_signing":
            sign_pdf = True
        elif t_type == "signature_breaking_edit":
            sign_pdf = True

        filename = f"fdr_{num_genuine + i + 1:03d}_TAMPERED_{t_type}_{fdr_num}.pdf"
        filepath = pdf_dir / filename

        create_fdr_pdf(
            output_path=str(filepath),
            bank_info=bank,
            institution_info=inst,
            fdr_number=fdr_num,
            principal_amount=principal,
            tenure_months=tenure,
            interest_rate=rate,
            issue_date=issue_dt,
            maturity_date=maturity_dt,
            maturity_amount=mat_amount,
            sign_pdf=sign_pdf,
            override_figure_amount=override_fig,
            override_words_amount=override_words,
            override_issue_date_str=override_issue,
            override_maturity_date_str=override_mat,
            pasted_box=pasted
        )

        if t_type == "metadata_edited_after_signing":
            apply_metadata_tamper(str(filepath))
        elif t_type == "signature_breaking_edit":
            apply_signature_breaking_edit(str(filepath))

        records.append({
            "id": f"TAMP-{i+1:03d}",
            "fdr_number": fdr_num,
            "bank_id": bank["id"],
            "institution_id": inst["id"],
            "label": "tampered",
            "tamper_type": t_type,
            "is_duplicate": False,
            "duplicate_type": "none",
            "principal_amount": principal,
            "maturity_amount": mat_amount,
            "interest_rate": rate,
            "issue_date": issue_dt.strftime("%Y-%m-%d"),
            "maturity_date": maturity_dt.strftime("%Y-%m-%d"),
            "tenure_months": tenure,
            "file_path": filepath.resolve().relative_to(BASE_DIR.resolve()).as_posix(),
            "qr_signed": True,
            "pdf_signed": sign_pdf
        })

    # -------------------------------------------------------------
    # 3. Duplicates (15)
    # -------------------------------------------------------------
    print(f"[*] Generating {num_duplicates} Duplicates (Cross-institution & Post-release)...")
    # 7 cross-institution duplicates (same FDR submitted by two different institutions)
    for i in range(7):
        # Pick one genuine record to duplicate
        original = records[i * 5]
        bank = next(b for b in banks if b["id"] == original["bank_id"])
        # Pick a different institution
        diff_insts = [inst for inst in institutions if inst["id"] != original["institution_id"]]
        new_inst = diff_insts[i % len(diff_insts)]

        filename = f"fdr_{num_genuine + num_tampered + i + 1:03d}_DUP_CROSS_INST_{original['fdr_number']}.pdf"
        filepath = pdf_dir / filename

        create_fdr_pdf(
            output_path=str(filepath),
            bank_info=bank,
            institution_info=new_inst,
            fdr_number=original["fdr_number"],
            principal_amount=original["principal_amount"],
            tenure_months=original["tenure_months"],
            interest_rate=original["interest_rate"],
            issue_date=datetime.strptime(original["issue_date"], "%Y-%m-%d"),
            maturity_date=datetime.strptime(original["maturity_date"], "%Y-%m-%d"),
            maturity_amount=original["maturity_amount"],
            sign_pdf=False
        )

        records.append({
            "id": f"DUP-{i+1:03d}",
            "fdr_number": original["fdr_number"],
            "bank_id": original["bank_id"],
            "institution_id": new_inst["id"],
            "label": "duplicate",
            "tamper_type": "none",
            "is_duplicate": True,
            "duplicate_type": "cross_institution_reuse",
            "principal_amount": original["principal_amount"],
            "maturity_amount": original["maturity_amount"],
            "interest_rate": original["interest_rate"],
            "issue_date": original["issue_date"],
            "maturity_date": original["maturity_date"],
            "tenure_months": original["tenure_months"],
            "file_path": filepath.resolve().relative_to(BASE_DIR.resolve()).as_posix(),
            "qr_signed": True,
            "pdf_signed": False
        })

    # 8 post-release duplicates (FDR resubmitted after release approval)
    for i in range(8):
        original = records[(i + 10) * 4]
        bank = next(b for b in banks if b["id"] == original["bank_id"])
        inst = next(ins for ins in institutions if ins["id"] == original["institution_id"])

        # Mark in issuer_ledger as RELEASED
        for ledger_row in issuer_ledger:
            if ledger_row["fdr_number"] == original["fdr_number"]:
                ledger_row["status"] = "RELEASED"

        filename = f"fdr_{num_genuine + num_tampered + 7 + i + 1:03d}_DUP_POST_RELEASE_{original['fdr_number']}.pdf"
        filepath = pdf_dir / filename

        create_fdr_pdf(
            output_path=str(filepath),
            bank_info=bank,
            institution_info=inst,
            fdr_number=original["fdr_number"],
            principal_amount=original["principal_amount"],
            tenure_months=original["tenure_months"],
            interest_rate=original["interest_rate"],
            issue_date=datetime.strptime(original["issue_date"], "%Y-%m-%d"),
            maturity_date=datetime.strptime(original["maturity_date"], "%Y-%m-%d"),
            maturity_amount=original["maturity_amount"],
            sign_pdf=False
        )

        records.append({
            "id": f"DUP-{7 + i + 1:03d}",
            "fdr_number": original["fdr_number"],
            "bank_id": original["bank_id"],
            "institution_id": inst["id"],
            "label": "duplicate",
            "tamper_type": "none",
            "is_duplicate": True,
            "duplicate_type": "post_release_resubmission",
            "principal_amount": original["principal_amount"],
            "maturity_amount": original["maturity_amount"],
            "interest_rate": original["interest_rate"],
            "issue_date": original["issue_date"],
            "maturity_date": original["maturity_date"],
            "tenure_months": original["tenure_months"],
            "file_path": filepath.resolve().relative_to(BASE_DIR.resolve()).as_posix(),
            "qr_signed": True,
            "pdf_signed": False
        })

    # -------------------------------------------------------------
    # 4. Noisy-but-genuine FDRs (10)
    # -------------------------------------------------------------
    print(f"[*] Generating {num_noisy} Noisy Scanned FDRs (Rotation, Blur, JPEG Compression)...")
    for i in range(num_noisy):
        fdr_seq += 1
        bank = random.choice(banks)
        inst = random.choice(institutions)
        fdr_num = format_bank_fdr_number(bank["id"], fdr_seq)

        principal = random.choice(principals)
        tenure = random.choice(tenures)
        rate = round(random.uniform(6.5, 7.8), 2)
        issue_dt = base_date + timedelta(days=random.randint(50, 350))
        maturity_dt = issue_dt + timedelta(days=int(tenure * 30.4375))
        mat_amount = calculate_quarterly_maturity(principal, rate, tenure)

        temp_pdf = pdf_dir / f"temp_clean_fdr_{140 + i + 1:03d}.pdf"
        create_fdr_pdf(
            output_path=str(temp_pdf),
            bank_info=bank,
            institution_info=inst,
            fdr_number=fdr_num,
            principal_amount=principal,
            tenure_months=tenure,
            interest_rate=rate,
            issue_date=issue_dt,
            maturity_date=maturity_dt,
            maturity_amount=mat_amount,
            sign_pdf=False
        )

        # Convert to scanned JPG with rotation, blur, and JPEG compression artifacts
        img_filename = f"fdr_{140 + i + 1:03d}_NOISY_SCAN_{bank['id']}_{fdr_num}.jpg"
        img_filepath = pdf_dir / img_filename
        convert_pdf_to_scanned_image(
            pdf_path=str(temp_pdf),
            output_image_path=str(img_filepath),
            rotate_deg=random.uniform(-2.5, 2.5),
            blur_radius=random.uniform(0.4, 0.9),
            jpeg_quality=random.randint(35, 50)
        )
        if temp_pdf.exists():
            temp_pdf.unlink()

        records.append({
            "id": f"NOISY-{i+1:03d}",
            "fdr_number": fdr_num,
            "bank_id": bank["id"],
            "institution_id": inst["id"],
            "label": "noisy_genuine",
            "tamper_type": "scanner_noise",
            "is_duplicate": False,
            "duplicate_type": "none",
            "principal_amount": principal,
            "maturity_amount": mat_amount,
            "interest_rate": rate,
            "issue_date": issue_dt.strftime("%Y-%m-%d"),
            "maturity_date": maturity_dt.strftime("%Y-%m-%d"),
            "tenure_months": tenure,
            "file_path": img_filepath.resolve().relative_to(BASE_DIR.resolve()).as_posix(),
            "qr_signed": True,
            "pdf_signed": False
        })

        issuer_ledger.append({
            "bank_id": bank["id"],
            "bank_name": bank["name"],
            "fdr_number": fdr_num,
            "institution_name": inst["name"],
            "principal_amount": principal,
            "maturity_amount": mat_amount,
            "interest_rate": rate,
            "issue_date": issue_dt.strftime("%Y-%m-%d"),
            "maturity_date": maturity_dt.strftime("%Y-%m-%d"),
            "status": "ACTIVE"
        })

    # -------------------------------------------------------------
    # 5. Output ground_truth.csv and issuer_ledger.json
    # -------------------------------------------------------------
    csv_file = out_path / "ground_truth.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "fdr_number", "bank_id", "institution_id", "label", "tamper_type",
            "is_duplicate", "duplicate_type", "principal_amount", "maturity_amount",
            "interest_rate", "issue_date", "maturity_date", "tenure_months",
            "file_path", "qr_signed", "pdf_signed"
        ])
        writer.writeheader()
        writer.writerows(records)

    ledger_file = out_path / "issuer_ledger.json"
    with open(ledger_file, "w", encoding="utf-8") as f:
        json.dump(issuer_ledger, f, indent=2)

    print(f"\n[SUCCESS] Generated total {len(records)} FDRs:")
    print(f"  - Genuine:  {len([r for r in records if r['label'] == 'genuine'])}")
    print(f"  - Tampered: {len([r for r in records if r['label'] == 'tampered'])}")
    print(f"  - Duplicate:{len([r for r in records if r['label'] == 'duplicate'])}")
    print(f"  - Noisy:    {len([r for r in records if r['label'] == 'noisy_genuine'])}")
    print(f"  - Ground Truth: {csv_file}")
    print(f"  - Issuer Ledger:{ledger_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic FDR dataset for FDR-Sentinel")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic generation")
    parser.add_argument("--count", type=int, default=150, help="Total number of FDRs to generate")
    parser.add_argument("--out", type=str, default="datagen/out", help="Output directory")
    args = parser.parse_args()

    generate_dataset(seed=args.seed, count=args.count, output_dir=args.out)
