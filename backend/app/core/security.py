import os
import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import pyotp
import qrcode
import io
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import get_settings

ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash password using Argon2id"""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2 hash"""
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# --- TOTP MFA ---

def generate_totp_secret() -> str:
    """Generate a base32 TOTP secret"""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    """Provisioning URI for authenticator apps"""
    settings = get_settings()
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.APP_NAME)


def get_totp_qr_base64(secret: str, email: str) -> str:
    """Generate base64 data URI of QR code for TOTP enrollment"""
    uri = get_totp_uri(secret, email)
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"


def verify_totp(secret: str, token: str) -> bool:
    """Verify 6-digit TOTP code (validates current and +/- 1 step)"""
    if not secret or not token:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(token.strip(), valid_window=1)


# --- AES-256-GCM Encryption for Documents and Sensitive Data ---

def _get_aesgcm() -> AESGCM:
    settings = get_settings()
    key_bytes = bytes.fromhex(settings.AES_MASTER_KEY_HEX)
    if len(key_bytes) != 32:
        raise ValueError("AES_MASTER_KEY_HEX must be 32 bytes (64 hex characters)")
    return AESGCM(key_bytes)


def encrypt_data(data: bytes, associated_data: Optional[bytes] = None) -> bytes:
    """
    Encrypt bytes using AES-256-GCM.
    Returns: 12-byte nonce prepended to ciphertext+tag.
    """
    aesgcm = _get_aesgcm()
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, associated_data)
    return nonce + ciphertext


def decrypt_data(encrypted_payload: bytes, associated_data: Optional[bytes] = None) -> bytes:
    """
    Decrypt bytes with AES-256-GCM.
    Expected format: 12-byte nonce followed by ciphertext+tag.
    """
    if len(encrypted_payload) < 28:
        raise ValueError("Invalid encrypted payload length")
    nonce = encrypted_payload[:12]
    ciphertext = encrypted_payload[12:]
    aesgcm = _get_aesgcm()
    return aesgcm.decrypt(nonce, ciphertext, associated_data)


# --- Cryptographic Audit Hashing ---

def canonical_json(data: Dict[str, Any]) -> str:
    """Convert dict to canonical JSON representation (sorted keys, compact)"""
    return json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)


def compute_sha256(data: bytes) -> str:
    """Compute standard SHA-256 hex digest"""
    return hashlib.sha256(data).hexdigest()


def compute_audit_hash(prev_hash: Optional[str], event_payload: Dict[str, Any]) -> str:
    """
    Compute hash-chain link:
    hash = SHA256(prev_hash + canonical_json(event_payload))
    """
    chain_prev = prev_hash if prev_hash else "0" * 64
    payload_str = canonical_json(event_payload)
    to_hash = (chain_prev + payload_str).encode("utf-8")
    return hashlib.sha256(to_hash).hexdigest()
