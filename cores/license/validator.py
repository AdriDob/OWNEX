"""License key validation using Ed25519 asymmetric signatures.

The 25-char key (XXXXX-XXXXX-XXXXX-XXXXX-XXXXX) is a human-readable identifier.
The real Ed25519 signature (64 bytes) is stored in license.json alongside the key.
First activation writes both key + signature to the store; subsequent runs verify
from the store using the embedded Ed25519 public key.

Key format encodes: version(1) + year(2) + month(2) + day(2) + expiry_year(2) +
expiry_month(2) + expiry_day(2) + hw_prefix(7) + base32_sig(5)
Data: 20 chars, Display sig: 5 chars -> 25 total.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from cores.license.hardware import get_hardware_id
from cores.license.store import get_license_store

logger = logging.getLogger("cateye.license.validator")

# Ed25519 public key (safe to embed — only used for verification)
# Override via CATEYE_LICENSE_PUBLIC_KEY env var for custom builds.
# Fix 2026-08-25 (P1 order-dependency): la clave se resolvía a nivel de
# módulo y quedaba congelada en el import; en suite completa el validator
# era importado durante la COLECCIÓN (antes del fixture autouse de conftest
# que genera el keypair efímero) → firmaba con priv de conftest pero
# verificaba contra el default embebido → "Invalid signature" solo en
# suite completa. Resolución lazy: mismo valor en prod (sin env → embedded),
# correcto en tests sin importar el orden. Semántica criptográfica intacta.
_EMBEDDED_PUBLIC_KEY_B64 = "r2abXG9wBnkfJCbF8nKK9ElOWXB8UWnUNH2JWYRRo8Y="


def _get_public_key_b64() -> str:
    return os.environ.get("CATEYE_LICENSE_PUBLIC_KEY", _EMBEDDED_PUBLIC_KEY_B64)


KEY_PATTERN = re.compile(r"^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$")

BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def _get_verifier() -> ed25519.Ed25519PublicKey:
    raw = base64.b64decode(_get_public_key_b64())
    return ed25519.Ed25519PublicKey.from_public_bytes(raw)


def _b32_encode(data: bytes) -> str:
    result = []
    buffer = 0
    bits = 0
    for byte in data:
        buffer = (buffer << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            result.append(BASE32_ALPHABET[(buffer >> bits) & 0x1F])
    if bits:
        result.append(BASE32_ALPHABET[(buffer << (5 - bits)) & 0x1F])
    return "".join(result)


def _b32_decode(s: str) -> bytes:
    result = bytearray()
    buffer = 0
    bits = 0
    for ch in s.upper():
        if ch not in BASE32_ALPHABET:
            continue
        value = BASE32_ALPHABET.index(ch)
        buffer = (buffer << 5) | value
        bits += 5
        while bits >= 8:
            bits -= 8
            result.append((buffer >> bits) & 0xFF)
    return bytes(result)


def _generate_key_data(hw_id: str, expiry_days: int = 365) -> tuple[str, bytes]:
    now = time.gmtime()
    year = now.tm_year % 100
    month = now.tm_mon
    day = now.tm_mday
    expiry_year = (now.tm_year + (expiry_days // 365)) % 100
    expiry_month = month
    expiry_day = day

    version = 1
    hw_prefix = hw_id[:7].upper()
    data_str = (
        f"{version:01d}{year:02d}{month:02d}{day:02d}{expiry_year:02d}{expiry_month:02d}{expiry_day:02d}{hw_prefix}"
    )
    payload = data_str.encode("ascii")
    return data_str, payload


def _format_key(data_str: str, sig: str) -> str:
    raw = data_str + sig
    groups = [raw[i : i + 5] for i in range(0, len(raw), 5)]
    return "-".join(groups)


def generate_license(expiry_days: int = 365) -> str:
    """Generate a license key and store the full Ed25519 signature.

    Returns the 25-char key for display.  The full base64-encoded Ed25519
    signature is stored in license.json so that subsequent validation can
    verify it asymmetrically.

    In production, this runs ONLY on the licensing server with the private key.
    For dev/test, set CATEYE_LICENSE_PRIVATE_KEY (raw Ed25519 private key, base64).
    """
    priv_b64 = os.environ.get("CATEYE_LICENSE_PRIVATE_KEY")
    if not priv_b64:
        logger.error("Cannot sign — CATEYE_LICENSE_PRIVATE_KEY not set")
        return ""

    hw_id = get_hardware_id()
    data_str, payload = _generate_key_data(hw_id, expiry_days)

    priv_raw = base64.b64decode(priv_b64)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_raw)
    sig_raw = private_key.sign(payload)
    sig_b64 = base64.b64encode(sig_raw).decode()

    # The 5-char key suffix is a truncated hash of the real signature (display only)
    sig_hash = hashlib.sha256(sig_raw).digest()
    display_sig = _b32_encode(sig_hash)[:5]
    key = _format_key(data_str, display_sig)

    # Persist the real signature alongside the key
    store = get_license_store()
    if store:
        store.save(key, hw_id, signature_b64=sig_b64)

    return key


def parse_license(key: str) -> dict | None:
    """Parse a license key without verifying signature."""
    clean = key.replace("-", "").upper()
    if len(clean) != 25:
        logger.warning("Invalid license key length: %d", len(clean))
        return None

    data_str = clean[:20]
    sig_str = clean[20:]

    version = int(data_str[0])
    year = 2000 + int(data_str[1:3])
    month = int(data_str[3:5])
    day = int(data_str[5:7])
    exp_year = 2000 + int(data_str[7:9])
    exp_month = int(data_str[9:11])
    exp_day = int(data_str[11:13])
    hw_prefix = data_str[13:20]

    return {
        "version": version,
        "issued": f"{year}-{month:02d}-{day:02d}",
        "expires": f"{exp_year}-{exp_month:02d}-{exp_day:02d}",
        "hardware_prefix": hw_prefix,
        "signature": sig_str,
    }


def verify_license_key(key: str) -> tuple[bool, str]:
    """Verify a license key by Ed25519 signature from the store."""
    parsed = parse_license(key)
    if not parsed:
        return False, "Invalid key format"

    clean = key.replace("-", "").upper()
    data_str = clean[:20]
    payload = data_str.encode("ascii")

    # Load the full Ed25519 signature from the license store
    store = get_license_store()
    stored = store.load() if store else None
    if not stored:
        return False, "No license activated"

    sig_b64 = stored.get("signature_b64")
    if not sig_b64:
        return False, "No Ed25519 signature stored — license must be re-activated"

    try:
        sig_raw = base64.b64decode(sig_b64)
        verifier = _get_verifier()
        verifier.verify(sig_raw, payload)
    except InvalidSignature:
        return False, "Invalid signature"
    except Exception as e:
        return False, f"Verification error: {e}"

    # Quick integrity: the 5-char display hash should match
    sig_hash = hashlib.sha256(sig_raw).digest()
    expected_display = _b32_encode(sig_hash)[:5]
    if clean[20:] != expected_display:
        return False, "License key does not match stored signature"

    exp_parts = parsed["expires"].split("-")
    exp_year = int(exp_parts[0])
    exp_month = int(exp_parts[1])
    exp_day = int(exp_parts[2])

    now = time.gmtime()
    current = now.tm_year * 10000 + now.tm_mon * 100 + now.tm_mday
    expiry = exp_year * 10000 + exp_month * 100 + exp_day
    if current > expiry:
        return False, "License has expired"

    return True, "Valid"


def validate_license(license_key: str) -> tuple[bool, str]:
    """Full license validation: signature + hardware binding + expiry."""
    valid, reason = verify_license_key(license_key)
    if not valid:
        return valid, reason

    store = get_license_store()
    stored = store.load() if store else None
    hw_id = get_hardware_id()
    parsed = parse_license(license_key)

    # First activation: already handled by generate_license via store.save
    if not stored:
        return False, "No license activated"

    # Verify hardware binding with full HWID
    stored_hw = stored.get("hardware_id", "")
    if stored_hw and stored_hw != hw_id:
        portable = os.environ.get("CATEYE_PORTABLE") == "1"
        if not portable:
            return False, "Hardware mismatch — license bound to different machine"
        logger.info("Portable mode: HW mismatch ignored for migration")

    if parsed and not hw_id.upper().startswith(parsed["hardware_prefix"]):
        portable = os.environ.get("CATEYE_PORTABLE") == "1"
        if not portable:
            return False, "Hardware prefix mismatch"
        logger.info("Portable mode: HW prefix mismatch ignored for migration")

    return True, "Valid"


def is_license_valid() -> tuple[bool, str]:
    """Check if a valid license is already activated on this machine."""
    store = get_license_store()
    stored = store.load() if store else None
    if not stored:
        return False, "No license activated"
    return validate_license(stored["license_key"])
