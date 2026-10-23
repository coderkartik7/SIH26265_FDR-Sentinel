import io
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import qrcode
from num2words import num2words
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from datagen.crypto_utils import (
    sign_qr_payload, get_or_create_test_ca
)
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.signers import SimpleSigner, PdfSigner
from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata
from pyhanko.sign.fields import SigFieldSpec


def calculate_quarterly_maturity(principal: float, rate_percent: float, tenure_months: int) -> float:
    """
    Default quarterly compounding formula:
    maturity = P * (1 + r / 400) ** (4 * t_years)
    """
    t_years = tenure_months / 12.0
    maturity = principal * math.pow(1.0 + (rate_percent / 400.0), 4.0 * t_years)
    return round(maturity, 2)


def format_inr_words(amount: float) -> str:
    """Convert number to Indian currency words format"""
    int_amt = int(amount)
    try:
        words = num2words(int_amt, lang='en_IN').title()
    except Exception:
        words = num2words(int_amt).title()
    return f"Rupees {words} Only"


# Color palettes per fictional bank
BANK_PALETTES = {
    "ACT": {"primary": colors.HexColor("#0D233A"), "accent": colors.HexColor("#D4AF37"), "bg": colors.HexColor("#F8F9FA")},
    "BNB": {"primary": colors.HexColor("#6B1D2F"), "accent": colors.HexColor("#2E6F40"), "bg": colors.HexColor("#FAF8F5")},
    "CRUB": {"primary": colors.HexColor("#2C3E50"), "accent": colors.HexColor("#E67E22"), "bg": colors.HexColor("#FDFEFE")},
    "DMB": {"primary": colors.HexColor("#4A154B"), "accent": colors.HexColor("#C29D38"), "bg": colors.HexColor("#F9F7F6")},
    "ETCB": {"primary": colors.HexColor("#005F73"), "accent": colors.HexColor("#0A9396"), "bg": colors.HexColor("#F4F9F9")}
}


def create_fdr_pdf(
    output_path: str,
    bank_info: Dict[str, Any],
    institution_info: Dict[str, Any],
    fdr_number: str,
    principal_amount: float,
    tenure_months: int,
    interest_rate: float,
    issue_date: datetime,
    maturity_date: datetime,
    maturity_amount: float,
    sign_pdf: bool = False,
    override_figure_amount: Optional[str] = None,
    override_words_amount: Optional[str] = None,
    override_issue_date_str: Optional[str] = None,
    override_maturity_date_str: Optional[str] = None,
    pasted_box: bool = False
) -> str:
    """
    Generate an authentic-looking fixed deposit receipt PDF with ReportLab.
    Optionally applies pyHanko digital signature using our synthetic test CA.
    """
    bank_id = bank_info.get("id", "ACT")
    palette = BANK_PALETTES.get(bank_id, BANK_PALETTES["ACT"])

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4

    # 1. Background tint and ornate dual-line border
    c.setFillColor(palette["bg"])
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setStrokeColor(palette["primary"])
    c.setLineWidth(3)
    c.rect(20, 20, width - 40, height - 40)

    c.setStrokeColor(palette["accent"])
    c.setLineWidth(1)
    c.rect(25, 25, width - 50, height - 50)

    # 2. Header banner
    c.setFillColor(palette["primary"])
    c.rect(26, height - 120, width - 52, 94, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 60, bank_info.get("name", "Commercial Bank").upper())

    c.setFont("Helvetica", 10)
    c.setFillColor(palette["accent"])
    branch = bank_info.get("branch_locations", ["Central Branch"])[0]
    ifsc = f"{bank_info.get('ifsc_prefix', 'TEST0')}001928"
    c.drawCentredString(width / 2, height - 80, f"Branch: {branch}  |  IFSC: {ifsc}  |  RTGS/NEFT Enabled")

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.white)
    c.drawCentredString(width / 2, height - 105, "FIXED DEPOSIT RECEIPT (SECURITY DEPOSIT)")

    # 3. Security deposit watermark
    c.saveState()
    c.setFont("Helvetica-Bold", 42)
    c.setFillColor(colors.HexColor("#E0E0E0"), alpha=0.35)
    c.translate(width / 2, height / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, "AICTE SECURITY DEPOSIT")
    c.drawCentredString(0, -60, "NON-TRANSFERABLE")
    c.restoreState()

    # 4. Key metadata banner
    c.setFillColor(palette["primary"])
    c.setFont("Helvetica-Bold", 11)
    c.drawString(45, height - 150, f"FDR Certificate No: {fdr_number}")

    issue_str = override_issue_date_str or issue_date.strftime("%d-%b-%Y")
    c.drawRightString(width - 45, height - 150, f"Issue Date: {issue_str}")

    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.8)
    c.line(45, height - 160, width - 45, height - 160)

    # 5. Holder Details Box
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(palette["primary"])
    c.drawString(45, height - 180, "DEPOSITOR / BENEFICIARY DETAILS:")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(45, height - 200, f"Institution Name:   {institution_info.get('name')}")
    c.drawString(45, height - 218, f"AICTE Permanent ID: {institution_info.get('code')}")
    c.drawString(45, height - 236, f"Lien Marked To:     MEMBER SECRETARY, AICTE, NEW DELHI (Joint Holder)")
    c.drawString(45, height - 254, f"Campus Location:    {institution_info.get('city')}, {institution_info.get('state')} ({institution_info.get('region')} Region)")

    # 6. Financial Details Table
    fig_amount_str = override_figure_amount or f"INR {principal_amount:,.2f}"
    words_amount_str = override_words_amount or format_inr_words(principal_amount)
    mat_date_str = override_maturity_date_str or maturity_date.strftime("%d-%b-%Y")
    mat_amount_str = f"INR {maturity_amount:,.2f}"

    table_data = [
        ["Principal Deposit Amount", fig_amount_str],
        ["Amount in Words", words_amount_str],
        ["Deposit Tenure", f"{tenure_months} Months ({tenure_months / 12:.1f} Years)"],
        ["Interest Rate (p.a.)", f"{interest_rate:.2f}% (Quarterly Compounding)"],
        ["Maturity Date", mat_date_str],
        ["Maturity Value", mat_amount_str]
    ]

    t = Table(table_data, colWidths=[180, width - 270])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#F0F4F8")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D7DE")),
    ]))
    t.wrapOn(c, width, height)
    t.drawOn(c, 45, height - 420)

    # 7. Pasted box tamper simulation if requested
    if pasted_box:
        c.saveState()
        c.setFillColor(colors.HexColor("#FFF8E7"))
        c.setStrokeColor(colors.HexColor("#E0C080"))
        c.setLineWidth(1)
        c.rect(225, height - 285, 180, 24, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#A00000"))
        c.setFont("Courier-Bold", 10)
        c.drawString(235, height - 275, "INR 9,50,000.00 (FORGED)")
        c.restoreState()

    # 8. Terms & Conditions
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(palette["primary"])
    c.drawString(45, height - 445, "TERMS AND REGULATORY CONDITIONS:")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor("#444444"))
    c.drawString(45, height - 460, "1. This Fixed Deposit is under irrevocable lien to AICTE under regulation SIH26265.")
    c.drawString(45, height - 472, "2. Premature liquidation or encashment requires written tripartite consent from AICTE.")
    c.drawString(45, height - 484, "3. Auto-renewal shall apply upon maturity unless instructions are received prior to 15 days.")
    c.drawString(45, height - 496, "4. Verification QR is digitally signed by the issuing bank authority.")

    # 9. Signed QR Code (bottom right)
    qr_payload = {
        "fdr_no": fdr_number,
        "bank_code": bank_id,
        "inst_id": institution_info.get("code"),
        "principal": principal_amount,
        "mat_value": maturity_amount,
        "rate": interest_rate,
        "issue_date": issue_date.strftime("%Y-%m-%d"),
        "mat_date": maturity_date.strftime("%Y-%m-%d")
    }
    signed_qr_envelope_str = sign_qr_payload(qr_payload)

    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(signed_qr_envelope_str)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    from reportlab.lib.utils import ImageReader
    qr_reader = ImageReader(qr_buffer)
    c.drawImage(qr_reader, width - 165, 45, width=115, height=115)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(palette["primary"])
    c.drawCentredString(width - 108, 35, "[Ed25519 SIGNED QR]")

    # 10. Official Signatory Seal (bottom left)
    c.setStrokeColor(palette["accent"])
    c.setLineWidth(1)
    c.rect(45, 45, 200, 95)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(palette["primary"])
    c.drawString(55, 125, "AUTHORIZED BANK SIGNATORY")
    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawString(55, 105, "Digitally Verified & Locked")
    c.drawString(55, 90, f"Issued by: Branch Operations Head, {bank_info.get('name')}")
    c.drawString(55, 75, f"Date: {issue_str}")
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.HexColor("#2E6F40"))
    c.drawString(55, 55, "STATUS: VALID BANK LIEN ACTIVE")

    c.showPage()
    c.save()

    raw_pdf_bytes = pdf_buffer.getvalue()

    # 11. Optional PyHanko digital signature
    if sign_pdf:
        try:
            signer_key_path, signer_cert_path, ca_cert_path = get_or_create_test_ca()
            signer = SimpleSigner.load(
                key_file=signer_key_path,
                cert_file=signer_cert_path,
                ca_chain_files=[ca_cert_path]
            )
            out_buf = io.BytesIO()
            w = IncrementalPdfFileWriter(io.BytesIO(raw_pdf_bytes))
            pdf_signer = PdfSigner(
                signature_meta=PdfSignatureMetadata(field_name="BankSignatureField"),
                signer=signer
            )
            pdf_signer.sign_pdf(w, output=out_buf)
            raw_pdf_bytes = out_buf.getvalue()
        except Exception as e:
            # Fallback if pyHanko metadata field differs
            pass

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(raw_pdf_bytes)

    return output_path
