"""Auto-Account Setup — crea y verifica cuentas en nuevas plataformas.

Cuando OWNEX descubre una nueva plataforma, intenta crear cuenta automáticamente:
- Genera datos de usuario
- Verifica email (si hay API)
- Configura 2FA (notifica al usuario si es manual)
- Guarda credenciales en el vault
"""

from __future__ import annotations

import logging
import os
import secrets
import string
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("orion.auto_account")


class AutoAccountSetup:
    """Automatically creates and configures accounts on new platforms."""

    def __init__(self) -> None:
        self._vault_path = os.path.expanduser("~/.config/ownex/accounts/")
        os.makedirs(self._vault_path, exist_ok=True)

    def generate_password(self, length: int = 20) -> str:
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def generate_username(self, base: str = "rastro") -> str:
        """Generate a unique username."""
        suffix = secrets.token_hex(4)
        return f"{base}_{suffix}"

    async def create_account(
        self,
        platform: str,
        email: str,
        username: str = "",
        password: str = "",
    ) -> dict[str, Any]:
        """Create an account on a platform."""
        if not password:
            password = self.generate_password()
        if not username:
            username = self.generate_username()

        result = {
            "platform": platform,
            "username": username,
            "email": email,
            "created": False,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Platform-specific account creation
        platform_lower = platform.lower()
        if platform_lower == "github":
            result.update(await self._create_github(username, email, password))
        elif platform_lower == "hackerone":
            result.update(await self._create_hackerone(username, email, password))
        elif platform_lower == "bugcrowd":
            result.update(await self._create_bugcrowd(username, email, password))
        elif platform_lower == "freelancer":
            result.update(await self._create_freelancer(username, email, password))
        else:
            result["method"] = "manual_required"
            result["note"] = f"Automatic creation not supported for {platform}. Manual signup required."

        # Save credentials to vault
        if result.get("created"):
            self._save_credentials(platform, username, email, password)

        return result

    async def _create_github(self, username: str, email: str, password: str) -> dict[str, Any]:
        """Create GitHub account (requires email verification)."""
        return {
            "created": False,
            "method": "api_or_manual",
            "url": "https://github.com/signup",
            "note": "GitHub requires email verification. Complete signup, then add GITHUB_TOKEN to env.",
            "credentials": {"username": username, "email": email, "password": password},
        }

    async def _create_hackerone(self, username: str, email: str, password: str) -> dict[str, Any]:
        """Create HackerOne account."""
        return {
            "created": False,
            "method": "manual_required",
            "url": "https://hackerone.com/users/sign_up",
            "note": "HackerOne requires manual signup + ID verification. Complete and add HACKERONE_API_KEY.",
            "credentials": {"username": username, "email": email, "password": password},
        }

    async def _create_bugcrowd(self, username: str, email: str, password: str) -> dict[str, Any]:
        """Create Bugcrowd account."""
        return {
            "created": False,
            "method": "manual_required",
            "url": "https://bugcrowd.com/users/sign_up",
            "note": "Bugcrowd requires manual signup. Complete and add BUGCROWD_API_KEY.",
            "credentials": {"username": username, "email": email, "password": password},
        }

    async def _create_freelancer(self, username: str, email: str, password: str) -> dict[str, Any]:
        """Create Freelancer.com account."""
        return {
            "created": False,
            "method": "manual_required",
            "url": "https://www.freelancer.com/register",
            "note": "Freelancer requires manual signup. Complete and add FREELANCER_API_KEY.",
            "credentials": {"username": username, "email": email, "password": password},
        }

    def _save_credentials(self, platform: str, username: str, email: str, password: str) -> None:
        """Save credentials to the vault."""
        import json

        cred_file = os.path.join(self._vault_path, f"{platform}.json")
        data = {
            "platform": platform,
            "username": username,
            "email": email,
            "password": password,  # In production, encrypt this!
            "created_at": datetime.now(UTC).isoformat(),
        }
        with open(cred_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("[AUTO_ACCOUNT] Credentials saved for %s", platform)

    def get_credentials(self, platform: str) -> dict[str, Any]:
        """Get saved credentials for a platform."""
        import json

        cred_file = os.path.join(self._vault_path, f"{platform}.json")
        if os.path.exists(cred_file):
            with open(cred_file) as f:
                return json.load(f)
        return {}

    def list_accounts(self) -> list[dict[str, Any]]:
        """List all saved accounts."""
        import json

        accounts = []
        if os.path.exists(self._vault_path):
            for fname in os.listdir(self._vault_path):
                if fname.endswith(".json"):
                    with open(os.path.join(self._vault_path, fname)) as f:
                        accounts.append(json.load(f))
        return accounts


_engine: AutoAccountSetup | None = None


def get_account_setup() -> AutoAccountSetup:
    """Get singleton AutoAccountSetup."""
    global _engine
    if _engine is None:
        _engine = AutoAccountSetup()
    return _engine
