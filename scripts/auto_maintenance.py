"""OWNEX Auto Maintenance Framework

Basic auto-diagnosis and recommendation system for OWNEX.
Detects errors, outdated libraries, old documentation, incorrect configurations.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class AutoMaintenance:
    """Auto maintenance framework for OWNEX."""

    def __init__(self):
        self.issues = []
        self.recommendations = []

    def check_python_dependencies(self) -> list[dict[str, Any]]:
        """Check for outdated Python dependencies."""
        issues = []

        try:
            result = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"], capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                outdated = json.loads(result.stdout)
                for pkg in outdated:
                    issues.append(
                        {
                            "type": "outdated_dependency",
                            "severity": "medium",
                            "package": pkg["name"],
                            "current": pkg["version"],
                            "latest": pkg["latest_version"],
                            "recommendation": f"Upgrade {pkg['name']} from {pkg['version']} to {pkg['latest_version']}",
                        }
                    )
        except Exception as e:
            issues.append(
                {
                    "type": "dependency_check_failed",
                    "severity": "low",
                    "error": str(e),
                    "recommendation": "Manual dependency review required",
                }
            )

        return issues

    def check_frontend_dependencies(self) -> list[dict[str, Any]]:
        """Check for outdated frontend dependencies."""
        issues = []

        try:
            result = subprocess.run(
                ["npm", "outdated", "--json"], capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT / "frontend"
            )

            if result.returncode == 0:
                outdated = json.loads(result.stdout)
                for pkg, info in outdated.items():
                    issues.append(
                        {
                            "type": "outdated_frontend_dependency",
                            "severity": "medium",
                            "package": pkg,
                            "current": info["current"],
                            "latest": info["latest"],
                            "recommendation": f"Upgrade {pkg} from {info['current']} to {info['latest']}",
                        }
                    )
        except Exception as e:
            issues.append(
                {
                    "type": "frontend_dependency_check_failed",
                    "severity": "low",
                    "error": str(e),
                    "recommendation": "Manual frontend dependency review required",
                }
            )

        return issues

    def check_lint_errors(self) -> list[dict[str, Any]]:
        """Check for lint errors."""
        issues = []

        try:
            result = subprocess.run(["ruff", "check", "."], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                error_count = result.stdout.count("\n")
                issues.append(
                    {
                        "type": "lint_errors",
                        "severity": "high" if error_count > 50 else "medium",
                        "error_count": error_count,
                        "recommendation": f"Fix {error_count} lint errors with 'ruff check --fix'",
                    }
                )
        except Exception as e:
            issues.append(
                {
                    "type": "lint_check_failed",
                    "severity": "low",
                    "error": str(e),
                    "recommendation": "Manual lint review required",
                }
            )

        return issues

    def check_test_failures(self) -> list[dict[str, Any]]:
        """Check for test failures."""
        issues = []

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--timeout=60", "-q"], capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0:
                failed_tests = result.stdout.count("FAILED")
                issues.append(
                    {
                        "type": "test_failures",
                        "severity": "high",
                        "failed_tests": failed_tests,
                        "recommendation": f"Fix {failed_tests} failing tests",
                    }
                )
        except Exception as e:
            issues.append(
                {
                    "type": "test_check_failed",
                    "severity": "low",
                    "error": str(e),
                    "recommendation": "Manual test review required",
                }
            )

        return issues

    def check_documentation_age(self) -> list[dict[str, Any]]:
        """Check for old documentation files."""
        issues = []
        now = datetime.now()

        ai_dir = PROJECT_ROOT / ".ai"
        if ai_dir.exists():
            for md_file in ai_dir.glob("*.md"):
                modified_time = datetime.fromtimestamp(md_file.stat().st_mtime)
                days_old = (now - modified_time).days

                if days_old > 30:
                    issues.append(
                        {
                            "type": "old_documentation",
                            "severity": "low",
                            "file": md_file.name,
                            "days_old": days_old,
                            "recommendation": f"Review and update {md_file.name} (last updated {days_old} days ago)",
                        }
                    )

        return issues

    def check_orphaned_files(self) -> list[dict[str, Any]]:
        """Check for orphaned or unused files."""
        issues = []

        # Check for orphaned scripts (not in git or not referenced)
        scripts_dir = PROJECT_ROOT / "scripts"
        if scripts_dir.exists():
            for script_file in scripts_dir.glob("*.py"):
                # Check if script is referenced in any documentation
                script_name = script_file.name
                is_referenced = False

                # Check README
                readme = PROJECT_ROOT / "README.md"
                if readme.exists():
                    content = readme.read_text()
                    if script_name in content:
                        is_referenced = True

                if not is_referenced:
                    issues.append(
                        {
                            "type": "potentially_orphaned_script",
                            "severity": "low",
                            "file": script_name,
                            "recommendation": f"Review {script_name} - may be unused",
                        }
                    )

        return issues

    def check_configuration_files(self) -> list[dict[str, Any]]:
        """Check for missing or incorrect configuration files."""
        issues = []

        # Check for .env.example
        env_example = PROJECT_ROOT / ".env.example"
        if not env_example.exists():
            issues.append(
                {
                    "type": "missing_env_example",
                    "severity": "medium",
                    "file": ".env.example",
                    "recommendation": "Create .env.example for configuration template",
                }
            )

        # Check for requirements.txt
        requirements = PROJECT_ROOT / "requirements.txt"
        if not requirements.exists():
            issues.append(
                {
                    "type": "missing_requirements",
                    "severity": "high",
                    "file": "requirements.txt",
                    "recommendation": "Create requirements.txt for Python dependencies",
                }
            )

        return issues

    def run_full_diagnosis(self) -> dict[str, Any]:
        """Run full system diagnosis."""
        print("Running OWNEX Auto Maintenance Diagnosis...")

        all_issues = []

        all_issues.extend(self.check_python_dependencies())
        all_issues.extend(self.check_frontend_dependencies())
        all_issues.extend(self.check_lint_errors())
        all_issues.extend(self.check_test_failures())
        all_issues.extend(self.check_documentation_age())
        all_issues.extend(self.check_orphaned_files())
        all_issues.extend(self.check_configuration_files())

        # Categorize by severity
        critical = [i for i in all_issues if i.get("severity") == "high"]
        medium = [i for i in all_issues if i.get("severity") == "medium"]
        low = [i for i in all_issues if i.get("severity") == "low"]

        diagnosis = {
            "timestamp": datetime.now().isoformat(),
            "total_issues": len(all_issues),
            "critical": len(critical),
            "medium": len(medium),
            "low": len(low),
            "issues": all_issues,
            "recommendations": [i.get("recommendation") for i in all_issues if "recommendation" in i],
        }

        return diagnosis

    def generate_report(self, diagnosis: dict[str, Any]) -> str:
        """Generate human-readable report."""
        report = f"""
OWNEX Auto Maintenance Report
{"=" * 50}
Generated: {diagnosis["timestamp"]}

SUMMARY
-------
Total Issues: {diagnosis["total_issues"]}
Critical: {diagnosis["critical"]}
Medium: {diagnosis["medium"]}
Low: {diagnosis["low"]}

ISSUES BY SEVERITY
{"=" * 50}

CRITICAL ({diagnosis["critical"]})
{"-" * 50}
"""

        for issue in diagnosis["issues"]:
            if issue.get("severity") == "high":
                report += f"• {issue.get('type', 'Unknown')}: {issue.get('recommendation', 'No recommendation')}\n"

        report += f"\nMEDIUM ({diagnosis['medium']})\n{'-' * 50}\n"

        for issue in diagnosis["issues"]:
            if issue.get("severity") == "medium":
                report += f"• {issue.get('type', 'Unknown')}: {issue.get('recommendation', 'No recommendation')}\n"

        report += f"\nLOW ({diagnosis['low']})\n{'-' * 50}\n"

        for issue in diagnosis["issues"]:
            if issue.get("severity") == "low":
                report += f"• {issue.get('type', 'Unknown')}: {issue.get('recommendation', 'No recommendation')}\n"

        report += f"\nRECOMMENDATIONS\n{'=' * 50}\n"

        for i, rec in enumerate(diagnosis["recommendations"], 1):
            report += f"{i}. {rec}\n"

        return report


def main():
    """Run auto maintenance diagnosis."""
    maintenance = AutoMaintenance()
    diagnosis = maintenance.run_full_diagnosis()
    report = maintenance.generate_report(diagnosis)

    print(report)

    # Save diagnosis to file
    diagnosis_file = PROJECT_ROOT / ".ai" / "AUTO_MAINTENANCE_REPORT.json"
    diagnosis_file.parent.mkdir(parents=True, exist_ok=True)

    with open(diagnosis_file, "w") as f:
        json.dump(diagnosis, f, indent=2)

    print(f"\n✓ Diagnosis saved to: {diagnosis_file}")


if __name__ == "__main__":
    main()
