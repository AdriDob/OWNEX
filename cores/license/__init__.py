"""License validation system for CATEYE.

Keys are signed with HMAC-SHA256 using a shared secret embedded in the binary.
In a production deployment, replace with asymmetric crypto (Ed25519) where the
public key is embedded and the private key lives on the licensing server.
"""

from cores.license.validator import is_license_valid, validate_license

