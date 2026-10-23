import pytest
from app.models.entities import User, UserRole, AuditLog
from app.services.audit_service import record_audit_event, verify_audit_chain, tamper_audit_row_for_demo
from app.core.security import hash_password, create_access_token


def test_audit_hash_chain_integrity(db):
    # Record 5 sequential audit events
    events = [
        ("U1", "institution", "FDR_UPLOAD", "FDR_CASE", "CASE-001", {"file": "fdr1.pdf"}),
        ("U1", "institution", "FDR_SUBMIT", "FDR_CASE", "CASE-001", {"amount": 500000}),
        ("U2", "official", "FORENSIC_CHECK_RUN", "FDR_CASE", "CASE-001", {"checks": 7}),
        ("U2", "official", "VERIFY_CONNECTOR", "FDR_CASE", "CASE-001", {"connector": "QR"}),
        ("U2", "official", "SEAL_APPROVED", "FDR_CASE", "CASE-001", {"status": "SEALED"})
    ]

    for actor, role, action, target_type, target_id, details in events:
        record_audit_event(
            db=db,
            actor_id=actor,
            actor_role=role,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details_json=details
        )

    # Verify the entire chain
    result = verify_audit_chain(db)
    assert result["is_valid"] is True
    assert result["total_records"] >= 5
    assert result["broken_index"] is None


def test_audit_tamper_detection_pinpoints_corrupted_record(db):
    # Empty any existing test table logs or record a sequence
    e1 = record_audit_event(db, "A1", "admin", "INIT", "SYSTEM", "SYS", {"v": 1})
    e2 = record_audit_event(db, "A1", "admin", "UPDATE", "POLICY", "P1", {"rule": "allow"})
    e3 = record_audit_event(db, "A1", "admin", "DELETE", "TEMP", "T1", {"done": True})

    # Verify valid before tampering
    before = verify_audit_chain(db)
    assert before["is_valid"] is True

    # Tamper with the middle record e2 directly in the database
    tamper_audit_row_for_demo(
        db=db,
        record_id=e2.id,
        forged_action="MALICIOUS_UNAUTHORIZED_OVERRIDE",
        forged_details={"rule": "hacked"}
    )

    # Now verify the chain - must detect the tamper at e2
    after = verify_audit_chain(db)
    assert after["is_valid"] is False
    assert after["broken_id"] == e2.id
    assert "tamper detected" in after["reason"] or "mismatch" in after["reason"]


def test_audit_verify_api_endpoint(client, db):
    # Verify via API endpoint GET /api/v1/audit/verify
    resp = client.get("/api/v1/audit/verify")
    assert resp.status_code == 200
    assert "is_valid" in resp.json()
    assert "total_records" in resp.json()


def test_audit_tamper_demo_api_workflow(client, db):
    # Create an admin user for tamper demo authorization
    admin = User(
        email="admin_audit@example.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin Audit",
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(admin)
    db.commit()

    admin_token = create_access_token({"sub": admin.id, "role": admin.role, "email": admin.email})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Record two valid events
    e1 = record_audit_event(db, admin.id, admin.role, "CONFIG_CHANGE", "SYSTEM", "CFG", {"key": "val1"})
    e2 = record_audit_event(db, admin.id, admin.role, "CONFIG_CHANGE", "SYSTEM", "CFG", {"key": "val2"})

    # Prior to tampering: valid
    res_before = client.get("/api/v1/audit/verify")
    assert res_before.json()["is_valid"] is True

    # Call /api/v1/audit/tamper-demo
    tamper_resp = client.post(
        "/api/v1/audit/tamper-demo",
        json={"record_id": e1.id, "forged_action": "FORGED_APPROVAL"},
        headers=headers
    )
    assert tamper_resp.status_code == 200
    assert tamper_resp.json()["is_tampered"] is True

    # Subsequent verification must detect broken chain at e1
    res_after = client.get("/api/v1/audit/verify")
    assert res_after.status_code == 200
    assert res_after.json()["is_valid"] is False
    assert res_after.json()["broken_id"] == e1.id
