#!/usr/bin/env python3
"""
Admin demonstration script for FDR-Sentinel:
Mutates an audit log row directly in the database without recomputing the SHA-256 hash.
This demonstrates the tamper-evident hash-chain security to evaluators and hackathon judges.
"""

import sys
import argparse
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.entities import AuditLog
from app.services.audit_service import tamper_audit_row_for_demo, verify_audit_chain


def main():
    parser = argparse.ArgumentParser(description="FDR-Sentinel Audit Chain Tamper Demo Script")
    parser.add_argument("--id", type=int, help="Specific AuditLog ID to tamper with. If omitted, tampers with latest.", default=None)
    parser.add_argument("--action", type=str, default="FORGED_UNAUTHORIZED_APPROVAL", help="New action string to forge")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.id is None:
            latest = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
            if not latest:
                print("[ERROR] No audit log entries exist in the database.")
                sys.exit(1)
            target_id = latest.id
        else:
            target_id = args.id

        print(f"[*] Tampering with Audit Record #{target_id}...")
        tampered = tamper_audit_row_for_demo(
            db=db,
            record_id=target_id,
            forged_action=args.action,
            forged_details={"tampered_by": "demo_admin_script", "malicious_override": True}
        )
        print(f"[OK] Row #{tampered.id} modified in database without updating cryptographic hash.")

        print("\n[*] Running chain verification walker...")
        verification = verify_audit_chain(db)
        print(f"[RESULT] Chain Valid: {verification['is_valid']}")
        print(f"[RESULT] Broken Index: {verification.get('broken_index')}")
        print(f"[RESULT] Broken ID: {verification.get('broken_id')}")
        print(f"[RESULT] Reason: {verification.get('reason')}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
