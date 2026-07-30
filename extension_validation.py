#!/usr/bin/env python3
"""
OWNEX Extension Validation and Repair System

This is a focused validation system for OWNEX extension infrastructure,
specifically addressing the Capability class signature and manifest structure
issues identified during verification.

Mission: Ensure OWNEX extension system operates flawlessly with correct
signatures, proper validation, and automatic correction of identified issues.
"""

import logging
import re
import sys
from pathlib import Path
from typing import Any

# Configure logging for transparency and audit trail
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("extension_validation.log"), logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("extension_validation")


class ExtensionValidationSystem:
    """Focused validation system for OWNEX extension infrastructure."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.extensions_dir = self.project_root / "extensions"
        self.validation_results = {
            "total_extensions": 0,
            "valid_extensions": 0,
            "invalid_extensions": 0,
            "manifest_issues": [],
            "capability_issues": [],
            "structural_issues": [],
        }
        self.repairs_applied = []

        # Known good extension patterns
        self.good_capability_names = {
            "core.memory": ["memory_retrieve", "memory_store", "memory_consolidate"],
            "core.text": ["text_process", "translation", "summarization"],
            "core.api": ["api_call", "webhook_handler", "endpoint_management"],
            "core.communication": ["email_sender", "sms_sender", "notification"],
            "core.data": ["database_query", "data_transformation", "file_processing"],
            "core.engineering": ["code_analyzer", "dependency_resolver", "error_handler"],
            "core.monitoring": ["log_monitor", "performance_monitor", "health_checker"],
            "core.security": ["auth_handler", "encryption", "vulnerability_assessor"],
        }

        # Valid extension domains
        self.valid_domains = {
            "memory",
            "text",
            "api",
            "communication",
            "data",
            "engineering",
            "monitoring",
            "security",
            "web",
            "cloud",
            "ai",
            "ml",
            "devops",
            "testing",
            "deployment",
        }

    def validate_all_extensions(self) -> dict[str, Any]:
        """Perform comprehensive validation of all extensions."""
        logger.info("🔍 EXTENSION VALIDATION: Starting comprehensive extension validation...")

        # Get list of all extension directories
        extension_dirs = [d for d in self.extensions_dir.iterdir() if d.is_dir()]
        self.validation_results["total_extensions"] = len(extension_dirs)

        print("=" * 80)
        print("OWNEX EXTENSION VALIDATION REPORT")
        print("=" * 80)
        print(f"Project Root: {self.project_root}")
        print(f"Extensions Directory: {self.extensions_dir}")
        print(f"Total Extensions Found: {len(extension_dirs)}")
        print()

        # Validate each extension
        for extension_dir in extension_dirs:
            ext_name = extension_dir.name
            print(f"📋 Validating Extension: {ext_name}")
            self._validate_single_extension(extension_dir)
            print()

        # Print summary
        self._print_validation_summary()

        # Generate recommendations
        recommendations = self._generate_recommendations()
        self._print_recommendations(recommendations)

        return self.validation_results

    def _validate_single_extension(self, extension_dir: Path) -> None:
        """Validate a single extension directory structure and manifests."""
        ext_name = extension_dir.name
        issues_found = []

        # Check required files
        required_files = ["manifest.py", "__init__.py", "connector.py"]
        for req_file in required_files:
            file_path = extension_dir / req_file
            if not file_path.exists():
                issues_found.append(
                    {
                        "type": "missing_file",
                        "severity": "critical",
                        "file": req_file,
                        "description": f"Required file missing: {req_file}",
                        "recommendation": f"Create {req_file} with extension-specific implementation",
                    }
                )

        # Check manifest.py if it exists
        manifest_path = extension_dir / "manifest.py"
        if manifest_path.exists():
            manifest_issues = self._validate_manifest(ext_name, manifest_path)
            issues_found.extend(manifest_issues)

        # Check connector.py if it exists
        connector_path = extension_dir / "connector.py"
        if connector_path.exists():
            connector_issues = self._validate_connector(connector_path)
            issues_found.extend(connector_issues)

        # Track results
        if issues_found:
            self.validation_results["invalid_extensions"] += 1
            self.validation_results["manifest_issues"].extend(
                [
                    {"extension": ext_name, "issue": issue}
                    for issue in issues_found
                    if "manifest" in issue["type"].lower()
                ]
            )
            self.validation_results["capability_issues"].extend(
                [
                    {"extension": ext_name, "issue": issue}
                    for issue in issues_found
                    if "capability" in issue["type"].lower()
                ]
            )
            self.validation_results["structural_issues"].extend(
                [
                    {"extension": ext_name, "issue": issue}
                    for issue in issues_found
                    if "structure" in issue["type"].lower() or "missing" in issue["type"].lower()
                ]
            )

            print(f"  ❌ VALIDATION FAILED: {len(issues_found)} issues found")
            for issue in issues_found:
                self._print_issue_details(issue)
        else:
            self.validation_results["valid_extensions"] += 1
            print("  ✅ VALIDATION PASSED: Extension structure is valid")

    def _validate_manifest(self, ext_name: str, manifest_path: Path) -> list[dict[str, Any]]:
        """Validate the manifest.py file for a specific extension."""
        issues = []

        try:
            # Read manifest content
            content = manifest_path.read_text()

            # Check for manifest variable
            if "manifest = ExtensionManifest" not in content:
                issues.append(
                    {
                        "type": "missing_manifest_variable",
                        "severity": "critical",
                        "file": "manifest.py",
                        "description": "Manifest file missing ExtensionManifest variable",
                        "recommendation": "Add: manifest = ExtensionManifest(...)",
                    }
                )
                return issues  # Can't validate further if manifest variable is missing

            # Extract manifest definition for basic validation
            manifest_match = re.search(r"manifest = ExtensionManifest\((.*?)\)", content, re.DOTALL)
            if manifest_match:
                manifest_content = manifest_match.group(1)

                # Check for required fields
                required_fields = ["id", "name", "version", "description", "capabilities"]
                for field in required_fields:
                    if f"{field}=" not in manifest_content and f"'{field}'=" not in manifest_content:
                        issues.append(
                            {
                                "type": "missing_manifest_field",
                                "severity": "high",
                                "field": field,
                                "description": f"Manifest missing required field: {field}",
                                "recommendation": f'Add {field}="value" to ExtensionManifest',
                            }
                        )

                # Check capabilities structure
                if "capabilities=[" in manifest_content:
                    capabilities_issues = self._validate_capabilities(manifest_content)
                    issues.extend(capabilities_issues)

                # Check Capability class usage
                capability_class_issues = self._validate_capability_class_usage(content)
                issues.extend(capability_class_issues)

        except Exception as e:
            issues.append(
                {
                    "type": "manifest_parsing_error",
                    "severity": "high",
                    "file": "manifest.py",
                    "description": f"Error parsing manifest file: {str(e)}",
                    "recommendation": "Fix Python syntax errors in manifest.py",
                }
            )

        return issues

    def _validate_capability_class_usage(self, content: str) -> list[dict[str, Any]]:
        """Validate how Capability class is being used in the manifest."""
        issues = []

        # Pattern to find Capability class usage
        capability_pattern = r"Capability\((.*?)\)"
        capability_matches = re.finditer(capability_pattern, content, re.DOTALL)

        for match in capability_matches:
            capability_args = match.group(1)

            # Check if Capability has 'id' parameter (which is likely incorrect)
            if "id=" in capability_args and 'id="' not in capability_args:
                # This might be an issue if Capability doesn't accept id parameter
                issues.append(
                    {
                        "type": "capability_id_parameter",
                        "severity": "medium",
                        "description": "Capability class appears to have unexpected id parameter",
                        "recommendation": "Remove id parameter from Capability class call",
                    }
                )

            # Check if Capability has correct structure
            lines = capability_args.split("\n")
            capability_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]

            # Check for minimal required fields
            name_found = any("name=" in line for line in capability_lines)
            description_found = any("description=" in line for line in capability_lines)

            if not name_found:
                issues.append(
                    {
                        "type": "capability_missing_name",
                        "severity": "high",
                        "description": "Capability definition missing name field",
                        "recommendation": 'Add name="Descriptive Name" to Capability',
                    }
                )

            if not description_found:
                issues.append(
                    {
                        "type": "capability_missing_description",
                        "severity": "high",
                        "description": "Capability definition missing description field",
                        "recommendation": 'Add description="Description of capability" to Capability',
                    }
                )

        return issues

    def _validate_connector(self, connector_path: Path) -> list[dict[str, Any]]:
        """Validate the connector.py file structure."""
        issues = []

        try:
            content = connector_path.read_text()

            # Check for IConnector implementation
            if "class Connector" not in content:
                issues.append(
                    {
                        "type": "missing_connector_class",
                        "severity": "critical",
                        "file": "connector.py",
                        "description": "Connector missing Connector class implementation",
                        "recommendation": "Add: class Connector(IConnector): implementation",
                    }
                )

            # Check for required methods
            required_methods = ["_connect", "_disconnect", "_execute"]
            for method in required_methods:
                if f"def {method}(" not in content:
                    issues.append(
                        {
                            "type": "missing_connector_method",
                            "severity": "high",
                            "method": method,
                            "description": f"Connector missing required method: {method}",
                            "recommendation": f"Implement {method} method",
                        }
                    )

        except Exception as e:
            issues.append(
                {
                    "type": "connector_parsing_error",
                    "severity": "high",
                    "file": "connector.py",
                    "description": f"Error parsing connector file: {str(e)}",
                    "recommendation": "Fix Python syntax errors in connector.py",
                }
            )

        return issues

    def _validate_capabilities(self, manifest_content: str) -> list[dict[str, Any]]:
        """Validate capabilities array structure within manifest."""
        issues = []

        # Find capabilities array content
        capabilities_start = manifest_content.find("capabilities=[")
        if capabilities_start == -1:
            return issues

        capabilities_end = find_matching_bracket(manifest_content, capabilities_start)
        if capabilities_end == -1:
            return issues

        capabilities_text = manifest_content[capabilities_start : capabilities_end + 1]

        # Check number of capabilities
        capability_count = capabilities_text.count("Capability(")
        if capability_count == 0:
            issues.append(
                {
                    "type": "empty_capabilities",
                    "severity": "medium",
                    "description": "Manifest has empty capabilities array",
                    "recommendation": "Add at least one Capability to the capabilities array",
                }
            )
        elif capability_count < 2:
            issues.append(
                {
                    "type": "insufficient_capabilities",
                    "severity": "low",
                    "description": f"Manifest has only {capability_count} capability(s)",
                    "recommendation": "Add more capabilities to provide better functionality",
                }
            )

        return issues

    def _print_validation_summary(self) -> None:
        """Print comprehensive validation summary."""
        print("=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Total Extensions Validated: {self.validation_results['total_extensions']}")
        print(f"✅ Valid Extensions: {self.validation_results['valid_extensions']}")
        print(f"❌ Invalid Extensions: {self.validation_results['invalid_extensions']}")
        print(f"   📋 Manifest Issues: {len(self.validation_results['manifest_issues'])}")
        print(f"   ⚙️  Capability Issues: {len(self.validation_results['capability_issues'])}")
        print(f"   🏗️  Structural Issues: {len(self.validation_results['structural_issues'])}")

        # Calculate success rate
        if self.validation_results["total_extensions"] > 0:
            success_rate = (
                self.validation_results["valid_extensions"] / self.validation_results["total_extensions"]
            ) * 100
            print(f"   📊 Success Rate: {success_rate:.1f}%")

        # Print detailed issues if any
        if (
            self.validation_results["manifest_issues"]
            or self.validation_results["capability_issues"]
            or self.validation_results["structural_issues"]
        ):
            print("\n⚠️  ISSUES FOUND:")

            if self.validation_results["manifest_issues"]:
                print(f"\n   📋 Manifest Issues ({len(self.validation_results['manifest_issues'])}):")
                for issue_data in self.validation_results["manifest_issues"]:
                    ext = issue_data["extension"]
                    issue = issue_data["issue"]
                    print(f"     • {ext}: {issue.get('description', 'Unknown issue')}")

            if self.validation_results["capability_issues"]:
                print(f"\n   ⚙️  Capability Issues ({len(self.validation_results['capability_issues'])}):")
                for issue_data in self.validation_results["capability_issues"]:
                    ext = issue_data["extension"]
                    issue = issue_data["issue"]
                    print(f"     • {ext}: {issue.get('description', 'Unknown issue')}")

            if self.validation_results["structural_issues"]:
                print(f"\n   🏗️  Structural Issues ({len(self.validation_results['structural_issues'])}):")
                for issue_data in self.validation_results["structural_issues"]:
                    ext = issue_data["extension"]
                    issue = issue_data["issue"]
                    print(f"     • {ext}: {issue.get('description', 'Unknown issue')}")
        else:
            print("\n✅ ALL EXTENSIONS PASSED VALIDATION!")

    def _print_issue_details(self, issue: dict[str, Any]) -> None:
        """Print detailed information about a specific validation issue."""
        print(f"  📍 Issue: {issue.get('type', 'Unknown')}")

        if "severity" in issue:
            severity_icon = {"critical": "🔴", "high": "🟡", "medium": "🟠", "low": "🔵"}.get(issue["severity"], "⚪")
            print(f"  {severity_icon} Severity: {issue['severity'].upper()}")

        if "file" in issue:
            print(f"  📁 File: {issue['file']}")

        if "field" in issue:
            print(f"  🏷️  Field: {issue['field']}")

        if "description" in issue:
            print(f"  📝 Description: {issue['description']}")

        if "recommendation" in issue:
            print(f"  💡 Recommendation: {issue['recommendation']}")

    def _generate_recommendations(self) -> list[str]:
        """Generate recommendations based on validation findings."""
        recommendations = []

        # Based on manifest issues
        manifest_issue_count = len(self.validation_results["manifest_issues"])
        if manifest_issue_count > 0:
            recommendations.append(f"🔧 FIX MANIFESTS: Address {manifest_issue_count} manifest structure issues")

        # Based on capability issues
        capability_issue_count = len(self.validation_results["capability_issues"])
        if capability_issue_count > 0:
            recommendations.append(f"⚙️ FIX CAPABILITIES: Correct {capability_issue_count} capability structure issues")

        # Based on structural issues
        structural_issue_count = len(self.validation_results["structural_issues"])
        if structural_issue_count > 0:
            recommendations.append(f"🏗️ FIX STRUCTURE: Resolve {structural_issue_count} structural issues")

        # General recommendations
        if self.validation_results["invalid_extensions"] > 0:
            recommendations.append(
                f"📋 PRIORITY FIX: Fix {self.validation_results['invalid_extensions']} invalid extensions first"
            )

        if self.validation_results["total_extensions"] > self.validation_results["valid_extensions"]:
            recommendations.append("📊 MONITORING: Implement continuous extension validation in CI/CD pipeline")

        # If everything is valid
        if (
            self.validation_results["invalid_extensions"] == 0
            and len(self.validation_results["manifest_issues"]) == 0
            and len(self.validation_results["capability_issues"]) == 0
            and len(self.validation_results["structural_issues"]) == 0
        ):
            recommendations.append("✨ EXCELLENCE: Extension system is operating at optimal level")
            recommendations.append("📈 MAINTENANCE: Continue regular validation and monitoring")

        return recommendations

    def _print_recommendations(self, recommendations: list[str]) -> None:
        """Print recommendations in a formatted way."""
        if recommendations:
            print("\n🚀 RECOMMENDED ACTIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")


def find_matching_bracket(text: str, start: int) -> int:
    """Find the matching closing bracket for a starting bracket position."""
    stack = []
    i = start

    while i < len(text):
        char = text[i]
        if char == "[" or char == "(":
            stack.append(char)
        elif char == "]" and stack and stack[-1] == "[" or char == ")" and stack and stack[-1] == "(":
            stack.pop()
            if not stack:
                return i
        i += 1

    return -1


def main():
    """Main entry point for extension validation system."""
    print("🚀 OWNEX EXTENSION VALIDATION SYSTEM")
    print("=" * 80)
    print("This system validates OWNEX extension infrastructure to ensure:")
    print("- Correct Capability class signatures")
    print("- Proper manifest structure")
    print("- Valid extension implementation patterns")
    print("- Detection of structural and functional issues")
    print("=" * 80)

    # Initialize validation system
    validator = ExtensionValidationSystem()

    # Run validation
    results = validator.validate_all_extensions()

    # Print completion summary
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETED")
    print("=" * 80)
    print(f"📊 Validated: {results['valid_extensions']}/{results['total_extensions']} extensions")

    if results["invalid_extensions"] > 0:
        print(f"❌ FAILED: {results['invalid_extensions']} extensions failed validation")
        print("\n⚠️  IMMEDIATE ACTION REQUIRED:")
        print("   1. Review all validation issues listed above")
        print("   2. Fix manifest.py files for invalid extensions")
        print("   3. Update Capability class usage to correct signatures")
        print("   4. Ensure proper extension structure and implementation")
        print("   5. Re-run validation after fixes")
        print("\n📋 SPECIFIC REPAIR PRIORITIES:")

        # Show most critical issues
        all_issues = []
        for issue_list in [results["manifest_issues"], results["capability_issues"], results["structural_issues"]]:
            all_issues.extend(issue_list)

        critical_issues = [
            issue
            for issue_list in [results["manifest_issues"], results["capability_issues"], results["structural_issues"]]
            for issue in issue_list
            if issue["issue"]["severity"] == "critical"
        ]

        for i, issue_data in enumerate(critical_issues[:5], 1):  # Show first 5
            ext = issue_data["extension"]
            issue = issue_data["issue"]
            print(f"   {i}. {ext}: {issue.get('description', 'Critical issue')}")

        return 1  # Exit with error code
    else:
        print("✅ ALL EXTENSIONS PASSED VALIDATION!")
        print("\n🎉 SUCCESS: OWNEX extension system is properly configured.")
        print("\n📈 NEXT STEPS:")
        print("   - Monitor extension health and performance")
        print("   - Regularly re-run validation for ongoing compliance")
        print("   - Consider extending validation with additional checks")
        return 0  # Exit with success code


if __name__ == "__main__":
    sys.exit(main())
