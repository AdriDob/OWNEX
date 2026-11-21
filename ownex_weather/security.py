"""
OWNEX V13 — Weather Intelligence & Prediction Markets
Security & License Compliance — AGPL-3.0 Guard

CRITICAL COMPLIANCE HARD CONSTRAINTS:
- NO AGPL-3.0 code reuse under any circumstances
- PolyWeather: API external consumption only (black box)
- All new code written from scratch
- MIT concepts from GFS/Hermes repos freely reusable with attribution
- credentials.txt from Repo 4 — DO NOT OPEN OR USE SECRETS
"""

from enum import Enum


class LicenseType(str, Enum):
    """License type enumeration."""

    MIT = "mit"
    AGPL_3_0 = "agpl-3.0"
    ACADMIC_EXPERIMENTAL = "academic-experimental"
    UNKNOWN = "unknown"


class ComplianceStatus(str, Enum):
    """Compliance status enumeration."""

    COMPLIANT = "compliant"
    VIOLATION_DETECTED = "violation_detected"
    WARNING = "warning"
    UNKNOWN = "unknown"


# --- AGPL-3.0 Guard — Hard Compliance Enforcement ---


class AGPLGuard:
    """AGPL-3.0 License Guard — enforces strict compliance.

    ⚠️  NON-NEGOTIABLE CONSTRAINTS:
    1. NO AGPL-3.0 code reuse under any circumstances
    2. PolyWeather consumed as external API only (black box)
    3. All new code written from scratch — no copied implementations
    4. MIT concepts from GFS/Hermes repos reusable with attribution
    5. credentials.txt from Repo 4 — DO NOT OPEN OR USE SECRETS
    6. No geoblocking bypass for Argentina access
    7. No real trading execution without human gate approval
    """

    def __init__(self):
        self.license_type = LicenseType.UNKNOWN
        self.compliance_status = ComplianceStatus.UNKNOWN
        self.violations: List[dict] = []
        self.attributions: List[dict] = []

        # ⚠️ PolyWeather: API external only — never code reuse
        self.polyweather_api_black_box = True
        self.mit_concepts_attribution_required = True
        self.credentials_txt_respected = True

    def verify_license_compliance(
        self,
        code_origin: str,
        license: LicenseType,
        involves_polyweather: bool = False,
        involves_credentials_txt: bool = False,
    ) -> dict:
        """Verify license compliance of code/module.

        Returns compliance status and any violations detected.
        """
        violations = []
        attributions = []
        compliant = True

        # Check 1: AGPL-3.0 code — absolutely prohibited
        if license == LicenseType.AGPL_3_0:
            compliant = False
            violations.append(
                {
                    "type": "agpl_code_reuse",
                    "severity": "critical",
                    "message": (
                        "AGPL-3.0 code detected — absolutely prohibited. "
                        "Cannot copy AGPL-3.0 code into OWNEX codebase. "
                        "PolyWeather must be consumed as external API only (black box)."
                    ),
                }
            )

        # Check 2: PolyWeather API — black box only, no code reuse
        if involves_polyweather and not self.polyweather_api_black_box:
            compliant = False
            violations.append(
                {
                    "type": "polyweather_code_reuse",
                    "severity": "critical",
                    "message": (
                        "PolyWeather code reuse detected — AGPL-3.0 constraint violation. "
                        "PolyWeather must be consumed as external API only. "
                        "No implementation code, datasets, or internal logic sharing."
                    ),
                }
            )

        # Check 3: credentials.txt — DO NOT OPEN OR USE SECRETS
        if involves_credentials_txt:
            compliant = False
            violations.append(
                {
                    "type": "credentials_txt_violation",
                    "severity": "critical",
                    "message": (
                        "credentials.txt detected — DO NOT OPEN OR USE SECRETS. "
                        "This file may contain sensitive authentication data. "
                        "Never open, read, or use credentials from this file."
                    ),
                }
            )

        # Check 4: MIT concepts — require attribution
        if license == LicenseType.MIT and self.mit_concepts_attribution_required:
            # MIT code is fine but attribution must be included
            attributions.append(
                {
                    "type": "mit_attribution",
                    "severity": "info",
                    "message": "MIT-licensed concepts detected — attribution required in documentation.",
                }
            )

        # Update state
        if violations:
            self.compliance_status = ComplianceStatus.VIOLATION_DETECTED
        elif attributions:
            self.compliance_status = ComplianceStatus.WARNING
        else:
            self.compliance_status = ComplianceStatus.COMPLIANT

        self.violations.extend(violations)
        self.attributions.extend(attributions)

        return {
            "compliant": compliant,
            "compliance_status": self.compliance_status.value,
            "license_type": self.license_type.value,
            "violations": violations,
            "attributions": attributions,
            "polyweather_black_box": self.polyweather_api_black_box,
        }

    def verify_no_geoblocking_bypass(self, involves_argentina: bool = False) -> dict:
        """Verify no geoblocking bypass for Argentina access."""
        violation = False

        if involves_argentina:
            # Check if any geoblocking or account restriction bypass is detected
            violation = True  # Would be checked in real implementation

        if violation:
            self.compliance_status = ComplianceStatus.VIOLATION_DETECTED
            self.violations.append(
                {
                    "type": "geoblocking_bypass",
                    "severity": "critical",
                    "message": "Geoblocking bypass detected for Argentina access — strictly prohibited.",
                }
            )

        return {
            "geoblocking_bypass": violation,
            "compliance_status": self.compliance_status.value,
        }

    def verify_no_real_trading(self, involves_real_trading: bool = False) -> dict:
        """Verify no real trading execution without human gate approval."""
        if involves_real_trading:
            self.compliance_status = ComplianceStatus.VIOLATION_DETECTED
            self.violations.append(
                {
                    "type": "real_trading_without_approval",
                    "severity": "critical",
                    "message": "Real trading execution detected without human gate approval — strictly prohibited.",
                }
            )

        return {
            "real_trading_without_approval": not involves_real_trading,
            "compliance_status": self.compliance_status.value,
        }

    def generate_compliance_report(self) -> dict:
        """Generate full compliance report."""
        return {
            "license_type": self.license_type.value,
            "compliance_status": self.compliance_status.value,
            "total_violations": len(self.violations),
            "violations": [v["message"] for v in self.violations],
            "attributions": [a["message"] for a in self.attributions],
            "polyweather_black_box": self.polyweather_api_black_box,
            "criteria": {
                "no_agpl_code_reuse": len([v for v in self.violations if "agpl_code_reuse" in v["type"]]) == 0,
                "polyweather_api_black_box": self.polyweather_api_black_box,
                "no_credentials_txt_abuse": len([v for v in self.violations if "credentials_txt" in v["type"]]) == 0,
                "no_geoblocking_bypass": len([v for v in self.violations if "geoblocking" in v["type"]]) == 0,
                "no_real_trading_without_approval": len([v for v in self.violations if "real_trading" in v["type"]]) == 0,
            },
        }


# --- License Documentation ---


class LicenseDocumentation:
    """License documentation and compliance records."""

    @staticmethod
    def mit_attribution() -> str:
        """Return MIT license attribution string."""
        return (
            "MIT License concepts reused from GFS Weather Bot and Hermes WeatherBot "
            "repositories. Original work credited. MIT terms: free to reuse architecture "
            "patterns, algorithmic approaches, and data structures (re-implemented in own "
            "code). Must include attribution and not sublicense in conflicting way."
        )

    @staticmethod
    def agpl_warning() -> str:
        """Return AGPL-3.0 warning string."""
        return (
            "AGPL-3.0 POLYWEATHER: Consumed as external API service only (black box). "
            "NO code reuse, NO implementation copying, NO dataset sharing. "
            "Network interaction obligations met via HTTP API calls only. "
            "For full terms: https://www.gnu.org/licenses/agpl-3.0.enr.html"
        )

    @staticmethod
    def credentials_warning() -> str:
        """Return credentials.txt warning string."""
        return (
            "⚠️ CREDENTIALS.TXT WARNING: File present in external repository (Repo 4: "
            "ML Weather Model). DO NOT OPEN OR USE SECRETS. This file may contain "
            "sensitive authentication data (API keys, database credentials, etc.). "
            "Experimental model only — not considered production-ready. Reference "
            "methodology concepts only, not code or datasets."
        )


# --- Export ---
__all__ = [
    "LicenseType",
    "ComplianceStatus",
    "AGPLGuard",
    "LicenseDocumentation",
]
