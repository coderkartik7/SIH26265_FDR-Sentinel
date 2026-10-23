import pytest
import pyotp
from app.models.entities import User, UserRole
from app.core.security import hash_password, verify_password, create_access_token


def test_user_registration_and_argon2_hashing(client, db):
    reg_payload = {
        "email": "test_registrar@institution.edu.in",
        "password": "SecurePassword123!",
        "full_name": "Test Registrar",
        "role": "institution"
    }
    response = client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == reg_payload["email"]
    assert data["role"] == "institution"

    # Verify password in DB is Argon2 hashed, not plaintext
    user = db.query(User).filter(User.email == reg_payload["email"]).first()
    assert user is not None
    assert user.hashed_password != "SecurePassword123!"
    assert verify_password("SecurePassword123!", user.hashed_password) is True


def test_duplicate_registration_prevented(client):
    reg_payload = {
        "email": "duplicate@institution.edu.in",
        "password": "SecurePassword123!",
        "full_name": "Duplicate User",
        "role": "institution"
    }
    resp1 = client.post("/api/v1/auth/register", json=reg_payload)
    assert resp1.status_code == 201
    resp2 = client.post("/api/v1/auth/register", json=reg_payload)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


def test_login_success_and_invalid_credentials(client, db):
    user = User(
        email="login_test@example.com",
        hashed_password=hash_password("MyPassword2026"),
        full_name="Login Test",
        role=UserRole.INSTITUTION,
        is_active=True
    )
    db.add(user)
    db.commit()

    # Successful login
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "login_test@example.com",
        "password": "MyPassword2026"
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    assert login_data["role"] == "institution"

    # Bad password
    bad_resp = client.post("/api/v1/auth/login", json={
        "email": "login_test@example.com",
        "password": "WrongPassword!"
    })
    assert bad_resp.status_code == 401


def test_totp_setup_and_verification(client, db):
    user = User(
        email="totp_user@example.com",
        hashed_password=hash_password("TOTPPassword2026"),
        full_name="TOTP User",
        role=UserRole.OFFICIAL,
        is_active=True
    )
    db.add(user)
    db.commit()

    token = create_access_token({"sub": user.id, "role": user.role, "email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Setup TOTP
    setup_resp = client.post("/api/v1/auth/totp/setup", headers=headers)
    assert setup_resp.status_code == 200
    secret = setup_resp.json()["secret"]
    assert len(secret) >= 16

    # Verify with generated code
    totp = pyotp.TOTP(secret)
    current_code = totp.now()

    verify_resp = client.post("/api/v1/auth/totp/verify", json={"code": current_code}, headers=headers)
    assert verify_resp.status_code == 200

    # Ensure user now requires TOTP on subsequent login
    db.refresh(user)
    assert user.totp_enabled is True

    # Login without TOTP code must fail with TOTP_REQUIRED
    login_no_totp = client.post("/api/v1/auth/login", json={
        "email": "totp_user@example.com",
        "password": "TOTPPassword2026"
    })
    assert login_no_totp.status_code == 403
    assert login_no_totp.json()["detail"] == "TOTP_REQUIRED"

    # Login with valid TOTP code succeeds
    login_with_totp = client.post("/api/v1/auth/login", json={
        "email": "totp_user@example.com",
        "password": "TOTPPassword2026",
        "totp_code": totp.now()
    })
    assert login_with_totp.status_code == 200
    assert "access_token" in login_with_totp.json()


def test_rbac_restriction(client, db):
    # Create an institution user
    inst_user = User(
        email="inst_rbac@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Inst User",
        role=UserRole.INSTITUTION,
        is_active=True
    )
    # Create an official user
    off_user = User(
        email="off_rbac@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Official User",
        role=UserRole.OFFICIAL,
        is_active=True
    )
    db.add_all([inst_user, off_user])
    db.commit()

    inst_token = create_access_token({"sub": inst_user.id, "role": inst_user.role, "email": inst_user.email})
    off_token = create_access_token({"sub": off_user.id, "role": off_user.role, "email": off_user.email})

    # Official endpoint /api/v1/audit/logs should deny institution role (403)
    resp_inst = client.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {inst_token}"})
    assert resp_inst.status_code == 403

    # Official endpoint should allow official role (200)
    resp_off = client.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {off_token}"})
    assert resp_off.status_code == 200
