import os
import json
import base64
from pathlib import Path
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

KEYS_DIR = Path(__file__).resolve().parent / "keys"


def ensure_keys_dir():
    KEYS_DIR.mkdir(parents=True, exist_ok=True)


def get_or_create_ed25519_issuer_key():
    """Get or generate persistent Ed25519 key pair for mock bank issuer QR signing"""
    ensure_keys_dir()
    priv_path = KEYS_DIR / "issuer_ed25519_priv.pem"
    pub_path = KEYS_DIR / "issuer_ed25519_pub.pem"

    if priv_path.exists() and pub_path.exists():
        with open(priv_path, "rb") as f:
            priv_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(pub_path, "rb") as f:
            pub_key = serialization.load_pem_public_key(f.read())
        return priv_key, pub_key

    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_key = priv_key.public_key()

    with open(priv_path, "wb") as f:
        f.write(priv_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open(pub_path, "wb") as f:
        f.write(pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    return priv_key, pub_key


def sign_qr_payload(payload_dict: dict) -> str:
    """
    Sign canonical JSON representation of QR payload with Mock Issuer's Ed25519 key.
    Returns compact JSON string containing payload + base64 signature.
    """
    priv_key, _ = get_or_create_ed25519_issuer_key()
    canonical_bytes = json.dumps(payload_dict, sort_keys=True, separators=(',', ':')).encode("utf-8")
    signature = priv_key.sign(canonical_bytes)
    sig_b64 = base64.b64encode(signature).decode("utf-8")

    qr_envelope = {
        "data": payload_dict,
        "sig": sig_b64,
        "alg": "Ed25519",
        "iss": "FDR_SENTINEL_MOCK_TEST_ISSUER"
    }
    return json.dumps(qr_envelope, separators=(',', ':'))


def verify_qr_payload(envelope_dict: dict) -> bool:
    """Verify Ed25519 signature on QR payload envelope"""
    try:
        _, pub_key = get_or_create_ed25519_issuer_key()
        payload = envelope_dict.get("data")
        sig_b64 = envelope_dict.get("sig")
        if not payload or not sig_b64:
            return False
        signature = base64.b64decode(sig_b64)
        canonical_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode("utf-8")
        pub_key.verify(signature, canonical_bytes)
        return True
    except Exception:
        return False


def get_or_create_test_ca():
    """
    Generate our own local test Root CA and signing certificate for pyHanko PDF signing.
    """
    ensure_keys_dir()
    ca_key_path = KEYS_DIR / "test_ca_key.pem"
    ca_cert_path = KEYS_DIR / "test_ca_cert.pem"
    signer_key_path = KEYS_DIR / "signer_key.pem"
    signer_cert_path = KEYS_DIR / "signer_cert.pem"

    if (ca_key_path.exists() and ca_cert_path.exists() and
            signer_key_path.exists() and signer_cert_path.exists()):
        return str(signer_key_path), str(signer_cert_path), str(ca_cert_path)

    # 1. Generate CA private key & cert
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FDR Sentinel Synthetic Test CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "FDR Sentinel Root CA"),
    ])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_subject)
        .issuer_name(ca_subject)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    # 2. Generate Signer private key & cert
    signer_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    signer_subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Apex Commercial Trust Bank Test Signer"),
        x509.NameAttribute(NameOID.COMMON_NAME, "ACT Bank Digital Signatory"),
    ])
    signer_cert = (
        x509.CertificateBuilder()
        .subject_name(signer_subject)
        .issuer_name(ca_subject)
        .public_key(signer_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1825))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    # Save all to files
    with open(ca_key_path, "wb") as f:
        f.write(ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open(ca_cert_path, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    with open(signer_key_path, "wb") as f:
        f.write(signer_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open(signer_cert_path, "wb") as f:
        f.write(signer_cert.public_bytes(serialization.Encoding.PEM))

    return str(signer_key_path), str(signer_cert_path), str(ca_cert_path)
