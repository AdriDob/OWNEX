"""Secure Account Vault — encrypted credential storage with audit logging.

Manages:
- API tokens and keys
- OAuth tokens (access/refresh)
- Session cookies
- Service credentials

All secrets are encrypted at rest. Every access is audited.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from core.events.event_bus import get_core_event_bus

logger = logging.getLogger("ownex.vault")


class CredentialType(Enum):
    """Types of credentials stored in the vault."""
    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"
    OAUTH_REFRESH = "oauth_refresh"
    SESSION_COOKIE = "session_cookie"
    USERNAME_PASSWORD = "username_password"
    SSH_KEY = "ssh_key"
    CERTIFICATE = "certificate"
    GENERIC_SECRET = "generic_secret"


class VaultOperation(Enum):
    """Operations on the vault for audit logging."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    ROTATE = "rotate"
    EXPORT = "export"
    IMPORT = "import"


@dataclass
class CredentialMetadata:
    """Metadata for a stored credential (no sensitive data)."""
    id: str
    name: str
    type: CredentialType
    platform: str
    account: str
    description: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    last_accessed: datetime | None = None
    expires_at: datetime | None = None
    rotation_interval_days: int | None = None
    is_active: bool = True
    access_count: int = 0


@dataclass
class AuditEntry:
    """Audit log entry for vault operations."""
    id: str
    timestamp: datetime
    operation: VaultOperation
    credential_id: str | None
    credential_name: str | None
    actor: str  # "user", "system", "agent:<name>"
    success: bool
    details: dict[str, Any]
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass
class VaultConfig:
    """Vault configuration."""
    encryption_key_path: str = ".vault/encryption.key"
    vault_data_path: str = ".vault/credentials.enc"
    audit_log_path: str = ".vault/audit.log"
    master_key_iterations: int = 100000
    auto_lock_minutes: int = 30
    max_audit_entries: int = 10000
    require_approval_for: set[VaultOperation] = field(default_factory=lambda: {
        VaultOperation.EXPORT,
        VaultOperation.DELETE,
        VaultOperation.ROTATE,
    })


class EncryptionManager:
    """Handles encryption/decryption of vault data."""

    def __init__(self, config: VaultConfig):
        self.config = config
        self._fernet: Fernet | None = None
        self._master_key: bytes | None = None

    def initialize(self, master_password: str) -> None:
        """Initialize encryption with master password."""
        # Load or create salt
        salt_path = self.config.encryption_key_path + ".salt"
        if os.path.exists(salt_path):
            with open(salt_path, "rb") as f:
                salt = f.read()
        else:
            salt = secrets.token_bytes(16)
            os.makedirs(os.path.dirname(salt_path), exist_ok=True)
            with open(salt_path, "wb") as f:
                f.write(salt)

        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.config.master_key_iterations,
        )
        self._master_key = kdf.derive(master_password.encode())
        self._fernet = Fernet(base64.urlsafe_b64encode(self._master_key))

        logger.info("Encryption initialized")

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        return self._fernet.decrypt(data)

    def is_initialized(self) -> bool:
        """Check if encryption is initialized."""
        return self._fernet is not None

    def lock(self) -> None:
        """Lock the encryption (clear keys from memory)."""
        self._fernet = None
        self._master_key = None
        logger.info("Vault locked")


class SecureVault:
    """
    Secure credential vault with encryption and audit logging.
    
    Features:
    - AES-256 encryption via Fernet
    - PBKDF2 key derivation
    - Audit logging for all operations
    - Automatic lock after inactivity
    - Credential rotation tracking
    - Expiration monitoring
    """

    def __init__(self, config: VaultConfig | None = None):
        self.config = config or VaultConfig()
        self.encryption = EncryptionManager(self.config)
        self._credentials: dict[str, dict[str, Any]] = {}  # id -> {metadata, secret}
        self._audit_log: list[AuditEntry] = []
        self._locked = True
        self._last_activity = time.time()
        self._approval_callbacks: list[callable] = []
        self.event_bus = get_core_event_bus()
        logger.info("SecureVault initialized")

    def unlock(self, master_password: str) -> bool:
        """Unlock the vault with master password."""
        try:
            self.encryption.initialize(master_password)

            # Load encrypted data
            if os.path.exists(self.config.vault_data_path):
                with open(self.config.vault_data_path, "rb") as f:
                    encrypted_data = f.read()
                decrypted = self.encryption.decrypt(encrypted_data)
                self._credentials = json.loads(decrypted.decode())

            # Load audit log
            if os.path.exists(self.config.audit_log_path):
                with open(self.config.audit_log_path) as f:
                    for line in f:
                        entry = json.loads(line)
                        self._audit_log.append(AuditEntry(**entry))

            self._locked = False
            self._last_activity = time.time()
            logger.info("Vault unlocked with %d credentials", len(self._credentials))
            return True

        except Exception as e:
            logger.error("Failed to unlock vault: %s", e)
            self._locked = True
            return False

    def lock(self) -> None:
        """Lock the vault."""
        self._save()
        self.encryption.lock()
        self._credentials.clear()
        self._audit_log.clear()
        self._locked = True
        logger.info("Vault locked")

    def is_locked(self) -> bool:
        """Check if vault is locked."""
        return self._locked

    def _check_auto_lock(self) -> None:
        """Check and apply auto-lock."""
        if not self._locked and self.config.auto_lock_minutes > 0:
            idle = time.time() - self._last_activity
            if idle > self.config.auto_lock_minutes * 60:
                logger.info("Auto-locking vault after %d minutes", self.config.auto_lock_minutes)
                self.lock()

    def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self._last_activity = time.time()

    def _require_approval(self, operation: VaultOperation) -> bool:
        """Check if operation requires approval."""
        return operation in self.config.require_approval_for

    async def _request_approval(self, operation: VaultOperation, details: dict) -> bool:
        """Request approval for sensitive operation."""
        for callback in self._approval_callbacks:
            try:
                approved = await callback(operation, details)
                if not approved:
                    return False
            except Exception as e:
                logger.error("Approval callback failed: %s", e)
                return False
        return True

    def _audit(
        self,
        operation: VaultOperation,
        credential_id: str | None = None,
        credential_name: str | None = None,
        actor: str = "system",
        success: bool = True,
        details: dict | None = None,
    ) -> None:
        """Record audit entry."""
        entry = AuditEntry(
            id=secrets.token_urlsafe(16),
            timestamp=datetime.now(UTC),
            operation=operation,
            credential_id=credential_id,
            credential_name=credential_name,
            actor=actor,
            success=success,
            details=details or {},
        )

        self._audit_log.append(entry)

        # Trim audit log
        if len(self._audit_log) > self.config.max_audit_entries:
            self._audit_log = self._audit_log[-self.config.max_audit_entries:]

        # Persist audit log
        try:
            os.makedirs(os.path.dirname(self.config.audit_log_path), exist_ok=True)
            with open(self.config.audit_log_path, "a") as f:
                f.write(json.dumps({
                    "id": entry.id,
                    "timestamp": entry.timestamp.isoformat(),
                    "operation": entry.operation.value,
                    "credential_id": entry.credential_id,
                    "credential_name": entry.credential_name,
                    "actor": entry.actor,
                    "success": entry.success,
                    "details": entry.details,
                }) + "\n")
        except Exception as e:
            logger.error("Failed to write audit log: %s", e)

        # Emit event
        self.event_bus.publish("vault:audit", {
            "operation": operation.value,
            "credential_id": credential_id,
            "actor": actor,
            "success": success,
        })

    def _save(self) -> None:
        """Save encrypted credentials to disk."""
        if self._locked:
            return

        try:
            data = json.dumps(self._credentials).encode()
            encrypted = self.encryption.encrypt(data)

            os.makedirs(os.path.dirname(self.config.vault_data_path), exist_ok=True)
            with open(self.config.vault_data_path, "wb") as f:
                f.write(encrypted)

            logger.debug("Vault saved with %d credentials", len(self._credentials))
        except Exception as e:
            logger.error("Failed to save vault: %s", e)

    def register_approval_callback(self, callback: callable) -> None:
        """Register approval callback for sensitive operations."""
        self._approval_callbacks.append(callback)

    # ──────────────────────────────────────────────────────────────────
    # CREDENTIAL OPERATIONS
    # ──────────────────────────────────────────────────────────────────

    def create_credential(
        self,
        name: str,
        type: CredentialType,
        platform: str,
        account: str,
        secret: str,
        description: str = "",
        tags: list[str] | None = None,
        expires_at: datetime | None = None,
        rotation_interval_days: int | None = None,
        actor: str = "user",
    ) -> str:
        """Create a new credential."""
        self._check_auto_lock()
        if self._locked:
            raise RuntimeError("Vault is locked")

        self._update_activity()

        credential_id = secrets.token_urlsafe(16)
        now = datetime.now(UTC)

        metadata = CredentialMetadata(
            id=credential_id,
            name=name,
            type=type,
            platform=platform,
            account=account,
            description=description,
            tags=tags or [],
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            rotation_interval_days=rotation_interval_days,
        )

        self._credentials[credential_id] = {
            "metadata": metadata.__dict__,
            "secret": secret,
        }

        self._save()
        self._audit(VaultOperation.CREATE, credential_id, name, actor, True, {
            "type": type.value,
            "platform": platform,
            "account": account,
        })

        logger.info("Created credential: %s (%s)", name, credential_id)
        return credential_id

    def get_credential(self, credential_id: str, actor: str = "system") -> str | None:
        """Get a credential secret by ID."""
        self._check_auto_lock()
        if self._locked:
            raise RuntimeError("Vault is locked")

        self._update_activity()

        cred = self._credentials.get(credential_id)
        if not cred:
            self._audit(VaultOperation.READ, credential_id, None, actor, False, {
                "reason": "not_found",
            })
            return None

        # Update access tracking
        cred["metadata"]["last_accessed"] = datetime.now(UTC).isoformat()
        cred["metadata"]["access_count"] = cred["metadata"].get("access_count", 0) + 1

        self._save()
        self._audit(VaultOperation.READ, credential_id, cred["metadata"]["name"], actor, True)

        return cred["secret"]

    def get_credential_metadata(self, credential_id: str) -> CredentialMetadata | None:
        """Get credential metadata (without secret)."""
        self._check_auto_lock()
        if self._locked:
            raise RuntimeError("Vault is locked")

        cred = self._credentials.get(credential_id)
        if not cred:
            return None

        meta = cred["metadata"]
        return CredentialMetadata(
            id=meta["id"],
            name=meta["name"],
            type=CredentialType(meta["type"]),
            platform=meta["platform"],
            account=meta["account"],
            description=meta["description"],
            tags=meta["tags"],
            created_at=datetime.fromisoformat(meta["created_at"]),
            updated_at=datetime.fromisoformat(meta["updated_at"]),
            last_accessed=datetime.fromisoformat(meta["last_accessed"]) if meta.get("last_accessed") else None,
            expires_at=datetime.fromisoformat(meta["expires_at"]) if meta.get("expires_at") else None,
            rotation_interval_days=meta.get("rotation_interval_days"),
            is_active=meta.get("is_active", True),
            access_count=meta.get("access_count", 0),
        )

    def update_credential(
        self,
        credential_id: str,
        secret: str | None = None,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        expires_at: datetime | None = None,
        rotation_interval_days: int | None = None,
        actor: str = "user",
    ) -> bool:
        """Update a credential."""
        self._check_auto_lock()
        if self._locked:
            raise RuntimeError("Vault is locked")

        cred = self._credentials.get(credential_id)
        if not cred:
            self._audit(VaultOperation.UPDATE, credential_id, None, actor, False, {
                "reason": "not_found",
            })
            return False

        self._update_activity()

        old_name = cred["metadata"]["name"]

        if secret is not None:
            cred["secret"] = secret
        if name is not None:
            cred["metadata"]["name"] = name
        if description is not None:
            cred["metadata"]["description"] = description
        if tags is not None:
            cred["metadata"]["tags"] = tags
        if expires_at is not None:
            cred["metadata"]["expires_at"] = expires_at.isoformat()
        if rotation_interval_days is not None:
            cred["metadata"]["rotation_interval_days"] = rotation_interval_days

        cred["metadata"]["updated_at"] = datetime.now(UTC).isoformat()

        self._save()
        self._audit(VaultOperation.UPDATE, credential_id, old_name, actor, True, {
            "fields_updated": [k for k, v in locals().items() if v is not None and k not in ["self", "credential_id", "actor", "cred"]],
        })

        logger.info("Updated credential: %s", credential_id)
        return True

    def delete_credential(self, credential_id: str, actor: str = "user", force: bool = False) -> bool:
        """Delete a credential (requires approval unless forced)."""
        self._check_auto_lock()
        if self._locked:
            raise RuntimeError("Vault is locked")

        cred = self._credentials.get(credential_id)
        if not cred:
            return False

        # Check approval requirement
        if not force and self._require_approval(VaultOperation.DELETE):
            # In real implementation, this would be async with callback
            logger.warning("DELETE requires approval, use force=True or implement approval callback")
            self._audit(VaultOperation.DELETE, credential_id, cred["metadata"]["name"], actor, False, {
                "reason": "approval_required",
            })
            return False

        self._update_activity()
        name = cred["metadata"]["name"]

        del self._credentials[credential_id]
        self._save()

        self._audit(VaultOperation.DELETE, credential_id, name, actor, True)
        logger.info("Deleted credential: %s", credential_id)
        return True

    def list_credentials(
        self,
        platform: str | None = None,
        type: CredentialType | None = None,
        active_only: bool = True,
        actor: str = "system",
    ) -> list[CredentialMetadata]:
        """List credentials with optional filters."""
        self._check_auto_lock()
        if self._locked:
            raise RuntimeError("Vault is locked")

        self._update_activity()

        results = []
        for cred in self._credentials.values():
            meta = cred["metadata"]

            if active_only and not meta.get("is_active", True):
                continue
            if platform and meta["platform"] != platform:
                continue
            if type and CredentialType(meta["type"]) != type:
                continue

            results.append(CredentialMetadata(
                id=meta["id"],
                name=meta["name"],
                type=CredentialType(meta["type"]),
                platform=meta["platform"],
                account=meta["account"],
                description=meta["description"],
                tags=meta["tags"],
                created_at=datetime.fromisoformat(meta["created_at"]),
                updated_at=datetime.fromisoformat(meta["updated_at"]),
                last_accessed=datetime.fromisoformat(meta["last_accessed"]) if meta.get("last_accessed") else None,
                expires_at=datetime.fromisoformat(meta["expires_at"]) if meta.get("expires_at") else None,
                rotation_interval_days=meta.get("rotation_interval_days"),
                is_active=meta.get("is_active", True),
                access_count=meta.get("access_count", 0),
            ))

        self._audit(VaultOperation.LIST, None, None, actor, True, {
            "count": len(results),
            "filters": {"platform": platform, "type": type.value if type else None},
        })

        return results

    def rotate_credential(
        self,
        credential_id: str,
        new_secret: str,
        actor: str = "system",
    ) -> bool:
        """Rotate a credential (update secret, track rotation)."""
        self._check_auto_lock()
        if self._locked:
            raise RuntimeError("Vault is locked")

        cred = self._credentials.get(credential_id)
        if not cred:
            return False

        # Check approval
        if self._require_approval(VaultOperation.ROTATE):
            logger.warning("ROTATE requires approval")
            self._audit(VaultOperation.ROTATE, credential_id, cred["metadata"]["name"], actor, False, {
                "reason": "approval_required",
            })
            return False

        self._update_activity()

        cred["secret"] = new_secret
        cred["metadata"]["updated_at"] = datetime.now(UTC).isoformat()
        cred["metadata"]["last_rotated"] = datetime.now(UTC).isoformat()

        self._save()
        self._audit(VaultOperation.ROTATE, credential_id, cred["metadata"]["name"], actor, True)

        logger.info("Rotated credential: %s", credential_id)
        return True

    def get_expiring_credentials(self, days: int = 30) -> list[CredentialMetadata]:
        """Get credentials expiring within specified days."""
        self._check_auto_lock()
        if self._locked:
            raise RuntimeError("Vault is locked")

        cutoff = datetime.now(UTC).timestamp() + (days * 86400)
        results = []

        for cred in self._credentials.values():
            meta = cred["metadata"]
            if meta.get("expires_at"):
                exp = datetime.fromisoformat(meta["expires_at"])
                if exp.timestamp() <= cutoff:
                    results.append(CredentialMetadata(
                        id=meta["id"],
                        name=meta["name"],
                        type=CredentialType(meta["type"]),
                        platform=meta["platform"],
                        account=meta["account"],
                        description=meta["description"],
                        tags=meta["tags"],
                        created_at=datetime.fromisoformat(meta["created_at"]),
                        updated_at=datetime.fromisoformat(meta["updated_at"]),
                        last_accessed=datetime.fromisoformat(meta["last_accessed"]) if meta.get("last_accessed") else None,
                        expires_at=exp,
                        rotation_interval_days=meta.get("rotation_interval_days"),
                        is_active=meta.get("is_active", True),
                        access_count=meta.get("access_count", 0),
                    ))

        return results

    def get_credentials_needing_rotation(self) -> list[CredentialMetadata]:
        """Get credentials that need rotation based on interval."""
        self._check_auto_lock()
        if self._locked:
            raise RuntimeError("Vault is locked")

        now = datetime.now(UTC)
        results = []

        for cred in self._credentials.values():
            meta = cred["metadata"]
            interval = meta.get("rotation_interval_days")
            last_rotated = meta.get("last_rotated")

            if interval and last_rotated:
                last = datetime.fromisoformat(last_rotated)
                if (now - last).days >= interval:
                    results.append(CredentialMetadata(
                        id=meta["id"],
                        name=meta["name"],
                        type=CredentialType(meta["type"]),
                        platform=meta["platform"],
                        account=meta["account"],
                        description=meta["description"],
                        tags=meta["tags"],
                        created_at=datetime.fromisoformat(meta["created_at"]),
                        updated_at=datetime.fromisoformat(meta["updated_at"]),
                        last_accessed=datetime.fromisoformat(meta["last_accessed"]) if meta.get("last_accessed") else None,
                        expires_at=datetime.fromisoformat(meta["expires_at"]) if meta.get("expires_at") else None,
                        rotation_interval_days=interval,
                        is_active=meta.get("is_active", True),
                        access_count=meta.get("access_count", 0),
                    ))

        return results

    # ──────────────────────────────────────────────────────────────────
    # AUDIT & HEALTH
    # ──────────────────────────────────────────────────────────────────

    def get_audit_log(
        self,
        limit: int = 100,
        operation: VaultOperation | None = None,
        credential_id: str | None = None,
        actor: str | None = None,
    ) -> list[AuditEntry]:
        """Get audit log entries with filters."""
        self._check_auto_lock()
        if self._locked:
            raise RuntimeError("Vault is locked")

        results = []
        for entry in reversed(self._audit_log):
            if operation and entry.operation != operation:
                continue
            if credential_id and entry.credential_id != credential_id:
                continue
            if actor and entry.actor != actor:
                continue

            results.append(entry)
            if len(results) >= limit:
                break

        return results

    def health_check(self) -> dict[str, Any]:
        """Check vault health."""
        issues = []

        if self._locked:
            issues.append("Vault is locked")

        # Check for expiring credentials
        expiring = self.get_expiring_credentials(7)
        if expiring:
            issues.append(f"{len(expiring)} credentials expiring within 7 days")

        # Check for rotation needed
        needing_rotation = self.get_credentials_needing_rotation()
        if needing_rotation:
            issues.append(f"{len(needing_rotation)} credentials need rotation")

        # Check audit log size
        if len(self._audit_log) > self.config.max_audit_entries * 0.9:
            issues.append("Audit log near capacity")

        return {
            "healthy": len(issues) == 0,
            "locked": self._locked,
            "total_credentials": len(self._credentials),
            "audit_entries": len(self._audit_log),
            "issues": issues,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get vault statistics."""
        by_platform = {}
        by_type = {}

        for cred in self._credentials.values():
            meta = cred["metadata"]
            platform = meta["platform"]
            ctype = meta["type"]

            by_platform[platform] = by_platform.get(platform, 0) + 1
            by_type[ctype] = by_type.get(ctype, 0) + 1

        return {
            "total_credentials": len(self._credentials),
            "by_platform": by_platform,
            "by_type": by_type,
            "audit_entries": len(self._audit_log),
            "locked": self._locked,
        }


# ──────────────────────────────────────────────────────────────────────────
# SINGLETON
# ──────────────────────────────────────────────────────────────────────────

_vault: SecureVault | None = None


def get_vault(config: VaultConfig | None = None) -> SecureVault:
    """Get or create the global vault instance."""
    global _vault
    if _vault is None:
        _vault = SecureVault(config)
    return _vault


async def initialize_vault(master_password: str, config: VaultConfig | None = None) -> SecureVault:
    """Initialize and unlock the vault."""
    vault = get_vault(config)
    success = vault.unlock(master_password)
    if not success:
        raise RuntimeError("Failed to unlock vault")

    health = vault.health_check()
    logger.info("Vault initialized: %s", "healthy" if health["healthy"] else "issues found")
    return vault
