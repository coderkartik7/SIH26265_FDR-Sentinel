from pathlib import Path
from typing import Dict, Any
import pikepdf


def apply_metadata_tamper(pdf_path: str) -> None:
    """
    Simulate metadata modification after document signing/generation:
    Uses pikepdf to alter Author, ModDate, and add custom suspicious metadata.
    """
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        with pdf.open_metadata() as meta:
            meta["dc:creator"] = ["Unauthorized PDF Editor v4.2"]
            meta["xmp:ModifyDate"] = "2026-10-21T18:00:00+05:30"
            meta["pdf:Producer"] = "Cracked PDF Editor Pro"
        pdf.save(pdf_path)


def apply_signature_breaking_edit(pdf_path: str) -> None:
    """
    Simulate bit-level tampering in a signed PDF document:
    Replaces a byte sequence in the stream to invalidate the pyHanko CMS digital signature.
    """
    with open(pdf_path, "rb") as f:
        data = bytearray(f.read())

    # Find a text stream marker or byte block and flip bytes
    target = b"SECURITY DEPOSIT"
    pos = data.find(target)
    if pos != -1:
        data[pos:pos+len(target)] = b"MODIFIED DEPOSIT"
    else:
        # Flip a byte halfway through
        mid = len(data) // 2
        data[mid] = (data[mid] + 1) % 256

    with open(pdf_path, "wb") as f:
        f.write(data)
