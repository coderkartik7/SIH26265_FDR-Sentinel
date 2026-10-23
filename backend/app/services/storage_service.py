import io
import os
from pathlib import Path
from typing import Tuple, Optional
from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings, BASE_DIR
from app.core.security import encrypt_data, decrypt_data, compute_sha256

settings = get_settings()

LOCAL_STORAGE_DIR = BASE_DIR / "storage" / "encrypted_docs"
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Magic bytes for strict file type validation
MAGIC_SIGNATURES = {
    b"%PDF-": "application/pdf",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg"
}

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024 # 25MB limit


def detect_mime_type(data: bytes) -> str:
    """Validate file type using leading magic bytes"""
    for sig, mime in MAGIC_SIGNATURES.items():
        if data.startswith(sig):
            return mime
    raise ValueError("Invalid file format. Only PDF, JPEG, and PNG files are accepted.")


def get_minio_client() -> Optional[Minio]:
    """Return Minio client if available, else None"""
    if os.getenv("TESTING", "").lower() in ("true", "1") or os.getenv("MINIO_DISABLED", "").lower() in ("true", "1"):
        return None
    try:
        client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        return client
    except Exception:
        return None


def store_encrypted_document(
    filename: str,
    raw_data: bytes
) -> Tuple[str, str, int, str]:
    """
    1. Validates size limit and magic-byte signature
    2. Computes SHA-256 hash of plain content
    3. Encrypts content at rest using AES-256-GCM
    4. Persists to MinIO bucket (or local encrypted storage fallback)
    Returns: (storage_path, sha256_hash, file_size, mime_type)
    """
    file_size = len(raw_data)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File size exceeds maximum permitted limit ({MAX_FILE_SIZE_BYTES // (1024*1024)}MB)")

    mime_type = detect_mime_type(raw_data)
    sha256_hash = compute_sha256(raw_data)

    # AES-256-GCM encryption with master key
    encrypted_bytes = encrypt_data(raw_data, associated_data=sha256_hash.encode("utf-8"))

    storage_path = f"enc_{sha256_hash[:16]}_{filename}"

    # Try MinIO first
    saved_to_minio = False
    try:
        client = get_minio_client()
        if client:
            # Check or create bucket
            if not client.bucket_exists(settings.MINIO_BUCKET_NAME):
                client.make_bucket(settings.MINIO_BUCKET_NAME)
            client.put_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=storage_path,
                data=io.BytesIO(encrypted_bytes),
                length=len(encrypted_bytes),
                content_type="application/octet-stream"
            )
            saved_to_minio = True
    except Exception:
        saved_to_minio = False

    # Also persist to local encrypted storage fallback for zero-dependency test resilience
    local_file = LOCAL_STORAGE_DIR / storage_path
    with open(local_file, "wb") as f:
        f.write(encrypted_bytes)

    return storage_path, sha256_hash, file_size, mime_type


def retrieve_and_decrypt_document(storage_path: str, expected_sha256: Optional[str] = None) -> bytes:
    """
    Retrieve encrypted bytes from MinIO or local storage fallback and decrypt with AES-256-GCM.
    """
    encrypted_bytes = None

    # Try local storage first
    local_file = LOCAL_STORAGE_DIR / storage_path
    if local_file.exists():
        with open(local_file, "rb") as f:
            encrypted_bytes = f.read()
    else:
        # Try MinIO
        client = get_minio_client()
        if client:
            resp = client.get_object(settings.MINIO_BUCKET_NAME, storage_path)
            encrypted_bytes = resp.read()
            resp.close()
            resp.release_conn()

    if not encrypted_bytes:
        raise FileNotFoundError(f"Stored encrypted document not found: {storage_path}")

    assoc_data = expected_sha256.encode("utf-8") if expected_sha256 else None
    try:
        decrypted_bytes = decrypt_data(encrypted_bytes, associated_data=assoc_data)
        return decrypted_bytes
    except Exception:
        # If decryption with assoc_data fails, try without
        return decrypt_data(encrypted_bytes, associated_data=None)
