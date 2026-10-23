from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, generate_totp_secret, get_totp_qr_base64, get_totp_uri, verify_totp
)
from app.models.entities import User, UserRole, Institution
from app.schemas.auth import (
    UserRegister, UserLogin, TokenResponse, TOTPSetupResponse,
    TOTPVerifyRequest, UserResponse
)
from app.services.audit_service import record_audit_event
from app.api.deps import get_current_user, limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, user_in: UserRegister, db: Session = Depends(get_db)):
    # Check if email already registered
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    # Validate institution if provided
    if user_in.institution_id:
        inst = db.query(Institution).filter(Institution.id == user_in.institution_id).first()
        if not inst:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provided institution ID does not exist.",
            )

    new_user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        institution_id=user_in.institution_id,
        is_active=True,
        totp_enabled=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Record hash-chained audit event
    record_audit_event(
        db=db,
        actor_id=new_user.id,
        actor_role=new_user.role,
        action="USER_REGISTERED",
        target_type="USER",
        target_id=new_user.id,
        details_json={"email": new_user.email, "role": new_user.role}
    )

    return new_user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # TOTP MFA verification if enabled on account
    if user.totp_enabled:
        if not credentials.totp_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="TOTP_REQUIRED",
            )
        if not verify_totp(user.totp_secret, credentials.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 6-digit TOTP verification code",
            )

    access_token = create_access_token(data={"sub": user.id, "role": user.role, "email": user.email})
    refresh_token = create_refresh_token(data={"sub": user.id})

    record_audit_event(
        db=db,
        actor_id=user.id,
        actor_role=user.role,
        action="USER_LOGIN_SUCCESS",
        target_type="USER",
        target_id=user.id,
        details_json={"email": user.email, "totp_used": user.totp_enabled}
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role.upper(),
        totp_required=False,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        institution_id=user.institution_id
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/totp/setup", response_model=TOTPSetupResponse)
def setup_totp(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    secret = generate_totp_secret()
    current_user.totp_secret = secret
    db.commit()

    uri = get_totp_uri(secret, current_user.email)
    qr_base64 = get_totp_qr_base64(secret, current_user.email)

    return TOTPSetupResponse(
        secret=secret,
        provisioning_uri=uri,
        qr_code_base64=qr_base64
    )


@router.post("/totp/verify")
def verify_and_enable_totp(
    req: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP setup has not been initiated. Call /totp/setup first.",
        )

    if not verify_totp(current_user.totp_secret, req.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code. Please check your authenticator application.",
        )

    current_user.totp_enabled = True
    db.commit()

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="TOTP_MFA_ENABLED",
        target_type="USER",
        target_id=current_user.id,
        details_json={"email": current_user.email}
    )

    return {"message": "Two-factor authentication successfully verified and enabled."}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access_token = create_access_token(data={"sub": user.id, "role": user.role, "email": user.email})
    new_refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        role=user.role,
        totp_required=False,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        institution_id=user.institution_id
    )
