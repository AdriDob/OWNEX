"""
Core self-healing system for Rastro.
Validates imports, file integrity, and automated repairs for broken components.
"""
import ast
import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cores.events.event_bus import get_event_bus

logger = logging.getLogger(__name__)
class ImportValidationError(Exception):
    """Raised when an import cannot be validated."""

class SelfHealingError(Exception):
    """Raised when self-healing operations fail."""
class ImportValidator:
    """Validates Python imports for syntax errors and missing dependencies."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors_found = []

    def validate_import(self, file_path: Path) -> List[str]:
        """Validate a Python file for import issues."""
        errors = []

        try:
            # Parse the file with AST
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, str(file_path))

            # Check for obvious syntax errors that the parser would catch
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self._validate_import_name(alias.name):
                            errors.append(
                                f"Invalid import name '{alias.name}' in {file_path}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module and not self._validate_import_name(node.module):
                        errors.append(
                            f"Invalid module '{node.module}' in {file_path}"
                        )

        except SyntaxError as e:
            errors.append(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            errors.append(f"Error validating {file_path}: {e}")

        return errors

    def _validate_import_name(self, name: str) -> bool:
        """Validate an import name is syntactically correct."""
        try:
            # Test if the name could be a valid import
            if not name or name.strip() == "":
                return False

            # Basic validation - names should contain valid identifier characters
            import re
            # Component names can contain dots but not start/end with them
            components = name.split(".")
            for component in components:
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', component):
                    return False

            return True
        except Exception:
            return False

    def scan_project_for_imports(self) -> Dict[str, List[str]]:
        """Scan entire project for Python files and validate their imports."""
        import_results = {}
        py_files = self.project_root.rglob("*.py")

        # Skip virtual environment and cache directories
        excluded_dirs = {"__pycache__", ".venv", ".git", "env", ".env"}
        for py_file in py_files:
            if any(excl in py_file.parts for excl in excluded_dirs):
                continue

            try:
                errors = self.validate_import(py_file)
                if errors:
                    import_results[str(py_file)] = errors
                    self.errors_found.extend(errors)
                else:
                    import_results[str(py_file)] = []

            except Exception as e:
                import_results[str(py_file)] = [f"Scan error: {e}"]
                self.errors_found.append(f"Scan error for {py_file}: {e}")

        return import_results

    def fix_import_issues(self) -> bool:
        """Attempt to fix common import issues."""
        fixed_count = 0

        for file_path_str, errors in self.import_results.items():
            if not errors:
                continue

            # Try to fix basic import issues
            try:
                file_path = Path(file_path_str)
                content = file_path.read_text(encoding='utf-8')
                original_content = content

                # Basic cleanup - remove problematic imports
                for error in errors:
                    if "Invalid import name" in error:
                        content = self._clean_import_name_errors(content)
                    elif "Syntax error" in error:
                        content = self._clean_syntax_errors(content)

                if content != original_content:
                    file_path.write_text(content, encoding='utf-8')
                    fixed_count += 1
                    logger.info("Fixed import issues in: %s", file_path_str)

            except Exception as e:
                logger.error("Failed to fix import issues in %s: %s", file_path_str, e)

        if fixed_count > 0:
            logger.info("Fixed import issues in %d files", fixed_count)

        return fixed_count > 0

    def _clean_import_name_errors(self, content: str) -> str:
        """Remove invalid import names from content."""
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            if 'import' in line and not self._validate_line_import(line):
                # Skip problematic import lines
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _validate_line_import(self, line: str) -> bool:
        """Validate a single import line."""
        try:
            # Extract import statement
            stripped = line.strip()
            if not stripped.startswith('import ') and not stripped.startswith('from '):
                return True

            # Simple validation - could be enhanced
            if 'import' in stripped and 'import from' not in stripped:
                parts = stripped.split(' import ')
                if len(parts) == 2:
                    module = parts[1].strip()
                    return bool(module.replace('.', '').replace('_', '').replace('-', ''))

            return True
        except Exception:
            return False

    def _clean_syntax_errors(self, content: str) -> str:
        """Attempt to clean up basic syntax errors."""
        # Remove incomplete lines or obvious syntax issues
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            if line.strip():
                # Basic syntax check - skip lines that look problematic
                if line.count("(") != line.count(")"):
                    continue
                if line.count("[") != line.count("]"):
                    continue
                if line.count("{") != line.count("}"):
                    continue

            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def process_imports(self, import_results: Dict[str, List[str]]) -> None:
        """Process import validation results."""
        self.import_results = import_results

        if self.errors_found:
            logger.warning("Import validation found %d issues", len(self.errors_found))
            self.fix_import_issues()
        else:
            logger.info("Import validation complete - no issues found")


class FileIntegrityChecker:
    """Validates file integrity and structure."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues_found = []

    def validate_file_structure(self) -> Dict[str, Dict[str, Any]]:
        """Validate project file structure."""
        results = {}

        for expected_dir in ["api", "cores", "extensions", "apps", "core"]:
            dir_path = self.project_root / expected_dir
            if dir_path.exists() and dir_path.is_dir():
                results[expected_dir] = {
                    "exists": True,
                    "type": "directory",
                    "issues": self._check_directory_integrity(dir_path)
                }
            else:
                results[expected_dir] = {
                    "exists": False,
                    "type": "missing",
                    "issues": [f"Required directory {expected_dir} not found"]
                }

        return results

    def _check_directory_integrity(self, dir_path: Path) -> List[str]:
        """Check for integrity issues in a directory."""
        issues = []

        try:
            for item in dir_path.iterdir():
                if item.name.startswith(".") and item.name not in [".env.example", "README.md"]:
                    continue

                if item.is_file() and item.suffix == ".py":
                    # Validate Python files
                    try:
                        content = item.read_text(encoding='utf-8')
                        ast.parse(content, str(item))
                    except SyntaxError as e:
                        issues.append(f"Invalid syntax in {item.name}: {e}")
                    except Exception as e:
                        issues.append(f"Error reading {item.name}: {e}")

                elif item.is_dir():
                    # Recursively check subdirectories
                    subdir_issues = self._check_directory_integrity(item)
                    issues.extend([f"{item.name}: {i}" for i in subdir_issues])

        except Exception as e:
            issues.append(f"Error scanning directory {dir_path.name}: {e}")

        return issues

    def auto_fix_issues(self, results: Dict[str, Dict[str, Any]]) -> int:
        """Attempt to fix file integrity issues."""
        fixed_count = 0

        for dir_name, dir_info in results.items():
            if dir_info["issues"]:
                dir_path = self.project_root / dir_name
                if dir_path.exists():
                    for issue in dir_info["issues"][:]:  # Copy list
                        if "Invalid syntax" in issue:
                            # Attempt to fix corrupted files
                            fixed = self._fix_corrupted_file(dir_path, issue)
                            if fixed:
                                dir_info["issues"].remove(issue)
                                fixed_count += 1

        return fixed_count

    def _fix_corrupted_file(self, dir_path: Path, issue: str) -> bool:
        """Attempt to fix a corrupted file."""
        try:
            # Find the specific file with the issue
            for file_path in dir_path.rglob("*.py"):
                if file_path.name in issue:
                    # Try to create a basic valid structure
                    content = self._create_basic_file_content(file_path)
                    if content:
                        file_path.write_text(content, encoding='utf-8')
                        logger.info("Fixed corrupted file: %s", file_path)
                        return True
        except Exception as e:
            logger.error("Failed to fix corrupted file: %s", e)

        return False

    def _create_basic_file_content(self, file_path: Path) -> Optional[str]:
        """Create basic valid content for a file."""
        try:
            if "routers" in str(file_path):
                return """from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok"}
"""
            elif "cores" in str(file_path):
                return """from typing import Dict, Any

class SystemComponent:
    \"\"\"Base class for system components with health checks.\"\"\"

    def __init__(self, name: str):
        self.name = name
        self.health_status = "healthy"

    def health_check(self) -> Dict[str, Any]:
        return {"name": self.name, "status": self.health_status}
"""
            else:
                return "# Placeholder - file was corrupted\npass\n"

        except Exception:
            return None


class StateValidator:
    """Validates system state and configuration."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.state_issues = []

    def validate_startup_config(self) -> Dict[str, Any]:
        """Validate startup configuration."""
        issues = []

        # Check for essential config files
        essential_files = [
            self.project_root / ".env.example",
            self.project_root / "pyproject.toml",
            self.project_root / "requirements.txt",
            self.project_root / "README.md",
        ]

        for config_file in essential_files:
            if not config_file.exists():
                issues.append(f"Missing essential config file: {config_file.name}")

        # Check for corrupted configuration files
        for config_file in essential_files:
            if config_file.exists():
                try:
                    if config_file.suffix == '.toml':
                        content = config_file.read_text(encoding='utf-8')
                        # Basic validation for TOML
                        if content.count('[') != content.count(']'):
                            issues.append(f"Potential corruption in {config_file.name}: bracket mismatch")
                except Exception as e:
                    issues.append(f"Error reading {config_file.name}: {e}")

        return {
            "status": "healthy" if not issues else "issues_found",
            "issues": issues,
            "checked_files": len(essential_files)
        }

    def auto_fix_state_issues(self, results: Dict[str, Any]) -> bool:
        """Attempt to fix state validation issues."""
        issues = results.get("issues", [])
        if not issues:
            return False

        logger.info("Attempting to fix %d state issues", len(issues))

        for issue in issues:
            try:
                if "Missing essential config file" in issue:
                    self._create_missing_config_file(issue)
                elif "corruption" in issue.lower():
                    self._fix_corrupted_config(issue)

                results["issues"] = [i for i in issues if i not in issue]
                if not results["issues"]:
                    results["status"] = "healthy"
                    break

            except Exception as e:
                logger.error("Failed to fix state issue '%s': %s", issue, e)

        return len(results["issues"]) < len(issues)

    def _create_missing_config_file(self, issue: str):
        """Create a missing configuration file."""
        try:
            if ".env.example" in issue:
                env_content = """# Rastro Environment Configuration
# Copy to .env and fill in values

DATABASE_URL=sqlite:///./data/app.db
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000
DEBUG=true
"""
                (self.project_root / ".env.example").write_text(env_content, encoding='utf-8')
                logger.info("Created .env.example file")

            elif "requirements.txt" in issue:
                req_content = """fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.1
python-multipart==0.0.14
"""
                (self.project_root / "requirements.txt").write_text(req_content, encoding='utf-8')
                logger.info("Created requirements.txt file")

        except Exception as e:
            logger.error("Failed to create config file: %s", e)

    def _fix_corrupted_config(self, issue: str):
        """Fix a corrupted configuration file."""
        try:
            for config_file in self.project_root.glob("*.toml"):
                if config_file.name in issue or "corruption" in issue:
                    # Restore to a known good config
                    config_content = """[tool.poetry]
name = "rastro"
version = "5.4.0"
description = "Auto-healed configuration"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.1"
uvicorn = "^0.24.0"
sqlalchemy = "^2.0.23"
pydantic = "^2.5.1"
"""
                    config_file.write_text(config_content, encoding='utf-8')
                    logger.info("Restored corrupted config file: %s", config_file.name)
                    break

        except Exception as e:
            logger.error("Failed to fix corrupted config: %s", e)


class SelfHealingSystem:
    """Main self-healing system orchestrating all repair operations."""

    def __init__(self, project_root: str = "/home/adrie/projects/Rastro"):
        self.project_root = Path(project_root)
        self.import_validator = ImportValidator(self.project_root)
        self.file_integrity_checker = FileIntegrityChecker(self.project_root)
        self.state_validator = StateValidator(self.project_root)
        self.repairs_performed = []
        self.health_status = "healthy"

    def validate_system(self) -> Dict[str, Any]:
        """Run complete system validation."""
        logger.info("Starting system validation")

        validation_results = {
            "import_validation": {},
            "file_integrity": {},
            "state_validation": {},
            "overall_status": "healthy",
            "repairs_attempted": 0,
            "repairs_successful": 0
        }

        # Validate imports
        import_results = self.import_validator.scan_project_for_imports()
        validation_results["import_validation"] = {
            "status": "healthy" if not self.import_validator.errors_found else "issues_found",
            "errors_count": len(self.import_validator.errors_found)
        }
        self.import_validator.process_imports(import_results)
        validation_results["repairs_attempted"] += 1 if self.import_validator.fix_import_issues() else 0

        # Validate file integrity
        file_integrity_results = self.file_integrity_checker.validate_file_structure()
        validation_results["file_integrity"] = {
            "status": "healthy" if all(
                not dir_info["issues"] for dir_info in file_integrity_results.values()
            ) else "issues_found",
            "directories": file_integrity_results
        }
        validation_results["repairs_attempted"] += self.file_integrity_checker.auto_fix_issues(
            file_integrity_results
        )

        # Validate system state
        state_results = self.state_validator.validate_startup_config()
        validation_results["state_validation"] = state_results
        validation_results["repairs_attempted"] += 1 if self.state_validator.auto_fix_state_issues(state_results) else 0

        # Determine overall status
        if (
            validation_results["import_validation"]["status"] == "healthy" and
            validation_results["file_integrity"]["status"] == "healthy" and
            validation_results["state_validation"]["status"] == "healthy"
        ):
            self.health_status = "healthy"
            validation_results["overall_status"] = "healthy"
            logger.info("System validation complete - all systems healthy")
        else:
            self.health_status = "degraded"
            validation_results["overall_status"] = "degraded"
            logger.warning("System validation complete - issues found and repaired")

        # Emit health event
        self._emit_health_event(validation_results)

        return validation_results

    def _emit_health_event(self, results: Dict[str, Any]):
        """Emit a health event to the event bus."""
        try:
            from cores.events.event_bus import get_event_bus

            bus = get_event_bus()
            event_data = {
                "event_type": "system:health:validated",
                "status": self.health_status,
                "results": results,
            }

            bus.publish("system:health", **event_data)
            logger.debug("Health event emitted: %s", self.health_status)

        except Exception as e:
            logger.warning("Failed to emit health event: %s", e)

    def get_health_status(self) -> str:
        """Get current system health status."""
        return self.health_status

    def get_repairs_summary(self) -> List[str]:
        """Get summary of repairs performed."""
        return self.repairs_performed.copy()

    def add_repair(self, repair: str):
        """Add a repair to the summary."""
        self.repairs_performed.append(repair)


def get_self_healing_system() -> SelfHealingSystem:
    """Get or create the self-healing system instance."""
    return SelfHealingSystem()