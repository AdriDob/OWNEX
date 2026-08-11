"""Repo Analyzer — Clone, detect setup, run tests for autonomous coding."""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# from core.autonomy.browser_agent import BrowserResult  # Will import after browser_agent is fixed


@dataclass
class BrowserResult:
    """Result of an operation."""

    success: bool
    action: str
    target: str
    message: str = ""
    data: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class RepoInfo:
    """Information about a cloned repository."""

    path: Path
    language: str
    package_manager: str | None
    test_command: str | None
    build_command: str | None
    dev_command: str | None
    framework: str | None
    entry_points: list[str] = field(default_factory=list)
    test_files: list[Path] = field(default_factory=list)
    config_files: dict[str, Path] = field(default_factory=dict)
    git_remote: str | None = None
    default_branch: str = "main"


class RepoAnalyzer:
    """Analyzes repository structure, detects language/setup, runs tests."""

    LANGUAGE_DETECTORS = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile", "poetry.lock"],
        "javascript": ["package.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb"],
        "typescript": ["tsconfig.json"],
        "go": ["go.mod", "go.sum"],
        "rust": ["Cargo.toml", "Cargo.lock"],
        "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "csharp": ["*.csproj", "*.sln"],
        "php": ["composer.json", "composer.lock"],
        "ruby": ["Gemfile", "Gemfile.lock", "Rakefile"],
    }

    PACKAGE_MANAGERS = {
        "python": ["uv", "pip", "poetry", "pipenv"],
        "javascript": ["pnpm", "npm", "yarn", "bun"],
        "typescript": ["pnpm", "npm", "yarn", "bun"],
        "go": ["go"],
        "rust": ["cargo"],
        "java": ["maven", "gradle"],
        "csharp": ["dotnet"],
        "php": ["composer"],
        "ruby": ["bundle"],
    }

    TEST_COMMANDS = {
        "python": ["pytest", "python -m pytest", "python -m unittest"],
        "javascript": ["npm test", "pnpm test", "yarn test", "bun test"],
        "typescript": ["npm test", "pnpm test", "yarn test", "bun test"],
        "go": ["go test ./..."],
        "rust": ["cargo test"],
        "java": ["mvn test", "./gradlew test"],
        "csharp": ["dotnet test"],
        "php": ["phpunit", "php vendor/bin/phpunit"],
        "ruby": ["rspec", "bundle exec rspec"],
    }

    BUILD_COMMANDS = {
        "python": ["pip install -e .", "uv pip install -e .", "poetry install"],
        "javascript": ["npm install", "pnpm install", "yarn install", "bun install"],
        "typescript": ["npm install", "pnpm install", "yarn install", "bun install"],
        "go": ["go mod download", "go build ./..."],
        "rust": ["cargo build"],
        "java": ["mvn compile", "./gradlew build"],
        "csharp": ["dotnet restore", "dotnet build"],
        "php": ["composer install"],
        "ruby": ["bundle install"],
    }

    def __init__(self, work_dir: Path | None = None):
        self.work_dir = work_dir or Path(tempfile.gettempdir()) / "ownex_repos"
        self.work_dir.mkdir(parents=True, exist_ok=True)

    async def clone_repo(
        self,
        repo_url: str,
        branch: str | None = None,
        shallow: bool = True,
        token: str | None = None,
    ) -> BrowserResult:
        """Clone repository to work directory."""
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_path = self.work_dir / repo_name

        # Clean existing
        if repo_path.exists():
            shutil.rmtree(repo_path)

        # Build clone URL with token if provided
        clone_url = repo_url
        if token and "github.com" in repo_url:
            clone_url = repo_url.replace("https://github.com/", f"https://{token}@github.com/")

        cmd = ["git", "clone"]
        if shallow:
            cmd.extend(["--depth", "1"])
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([clone_url, str(repo_path)])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return BrowserResult(False, "clone_repo", repo_url, error=stderr.decode())

            # Get default branch
            default_branch = await self._get_default_branch(repo_path)

            return BrowserResult(
                True,
                "clone_repo",
                repo_url,
                f"Cloned to {repo_path}",
                data={"path": str(repo_path), "default_branch": default_branch},
            )
        except Exception as e:
            return BrowserResult(False, "clone_repo", repo_url, error=str(e))

    async def _get_default_branch(self, repo_path: Path) -> str:
        """Get default branch name."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "symbolic-ref",
                "refs/remotes/origin/HEAD",
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode().strip().split("/")[-1]
        except Exception:
            pass
        return "main"

    async def analyze_repo(self, repo_path: Path) -> RepoInfo:
        """Analyze repository structure and detect configuration."""
        info = RepoInfo(path=repo_path, language="unknown", package_manager=None)

        # Detect language
        info.language = self._detect_language(repo_path)

        # Detect package manager
        info.package_manager = self._detect_package_manager(repo_path, info.language)

        # Detect test command
        info.test_command = self._detect_test_command(repo_path, info.language)

        # Detect build command
        info.build_command = self._detect_build_command(repo_path, info.language)

        # Find config files
        info.config_files = self._find_config_files(repo_path, info.language)

        # Find test files
        info.test_files = self._find_test_files(repo_path, info.language)

        # Find entry points
        info.entry_points = self._find_entry_points(repo_path, info.language)

        # Get git remote
        info.git_remote = await self._get_git_remote(repo_path)

        # Detect framework
        info.framework = self._detect_framework(repo_path, info.language)

        return info

    def _detect_language(self, repo_path: Path) -> str:
        """Detect primary programming language."""
        scores = {}
        for lang, patterns in self.LANGUAGE_DETECTORS.items():
            score = 0
            for pattern in patterns:
                matches = list(repo_path.rglob(pattern))
                score += len(matches)
            if score > 0:
                scores[lang] = score

        if not scores:
            return "unknown"

        # Prefer more specific languages (typescript over javascript)
        if "typescript" in scores and "javascript" in scores:
            scores["typescript"] += scores["javascript"]
            del scores["javascript"]

        return max(scores, key=scores.get)

    def _detect_package_manager(self, repo_path: Path, language: str) -> str | None:
        """Detect package manager from lock files."""
        managers = self.PACKAGE_MANAGERS.get(language, [])
        for manager in managers:
            if manager == "uv" and (repo_path / "uv.lock").exists():
                return "uv"
            if manager == "pip" and (repo_path / "requirements.txt").exists():
                return "pip"
            if manager == "poetry" and (repo_path / "poetry.lock").exists():
                return "poetry"
            if manager == "pipenv" and (repo_path / "Pipfile.lock").exists():
                return "pipenv"
            if manager == "pnpm" and (repo_path / "pnpm-lock.yaml").exists():
                return "pnpm"
            if manager == "yarn" and (repo_path / "yarn.lock").exists():
                return "yarn"
            if manager == "bun" and (repo_path / "bun.lockb").exists():
                return "bun"
            if manager == "npm" and (repo_path / "package-lock.json").exists():
                return "npm"
            if manager == "cargo" and (repo_path / "Cargo.lock").exists():
                return "cargo"
            if manager == "go" and (repo_path / "go.sum").exists():
                return "go"
            if manager == "maven" and (repo_path / "pom.xml").exists():
                return "maven"
            if manager == "gradle" and (repo_path / "build.gradle").exists():
                return "gradle"
            if manager == "composer" and (repo_path / "composer.lock").exists():
                return "composer"
            if manager == "bundle" and (repo_path / "Gemfile.lock").exists():
                return "bundle"
            if manager == "dotnet" and list(repo_path.rglob("*.csproj")):
                return "dotnet"

        return managers[0] if managers else None

    def _detect_test_command(self, repo_path: Path, language: str) -> str | None:
        """Detect test command from config files."""
        commands = self.TEST_COMMANDS.get(language, [])

        # Check package.json for test script
        if language in ["javascript", "typescript"]:
            pkg_json = repo_path / "package.json"
            if pkg_json.exists():
                try:
                    data = json.loads(pkg_json.read_text())
                    if "scripts" in data and "test" in data["scripts"]:
                        return f"{self._detect_package_manager(repo_path, language) or 'npm'} test"
                except Exception:
                    pass

        # Check pyproject.toml for pytest
        if language == "python":
            pyproject = repo_path / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text()
                if "[tool.pytest" in content or "pytest" in content:
                    return "pytest"

        # Check Cargo.toml for test
        if language == "rust":
            cargo = repo_path / "Cargo.toml"
            if cargo.exists() and "[[test]]" in cargo.read_text():
                return "cargo test"

        # Return first available command
        for cmd in commands:
            # Could verify command exists, but skip for speed
            return cmd

        return None

    def _detect_build_command(self, repo_path: Path, language: str) -> str | None:
        """Detect build/install command."""
        commands = self.BUILD_COMMANDS.get(language, [])
        for cmd in commands:
            return cmd  # Return first available
        return None

    def _find_config_files(self, repo_path: Path, language: str) -> dict[str, Path]:
        """Find important config files."""
        configs = {}

        config_patterns = {
            "python": [
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                "requirements.txt",
                "Pipfile",
                "poetry.lock",
                "uv.lock",
            ],
            "javascript": ["package.json", "tsconfig.json", "eslint.config.js", ".eslintrc.js", "prettier.config.js"],
            "typescript": ["tsconfig.json", "package.json"],
            "go": ["go.mod", "go.sum", "Makefile"],
            "rust": ["Cargo.toml", "Cargo.lock", "rust-toolchain.toml"],
            "java": ["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"],
            "csharp": ["*.csproj", "*.sln", "Directory.Build.props"],
            "php": ["composer.json", "composer.lock", "phpunit.xml"],
            "ruby": ["Gemfile", "Gemfile.lock", "Rakefile", ".rubocop.yml"],
        }

        patterns = config_patterns.get(language, [])
        for pattern in patterns:
            matches = list(repo_path.rglob(pattern))
            if matches:
                configs[pattern] = matches[0]

        return configs

    def _find_test_files(self, repo_path: Path, language: str) -> list[Path]:
        """Find test files in repository."""
        test_patterns = {
            "python": ["test_*.py", "*_test.py", "tests/**/*.py"],
            "javascript": ["*.test.js", "*.spec.js", "test/**/*.js", "tests/**/*.js"],
            "typescript": ["*.test.ts", "*.spec.ts", "test/**/*.ts", "tests/**/*.ts"],
            "go": ["*_test.go"],
            "rust": ["tests/*.rs", "*_test.rs"],
            "java": ["*Test.java", "*Tests.java", "test/**/*.java"],
            "csharp": ["*Tests.cs", "*Test.cs", "Tests/**/*.cs"],
            "php": ["*Test.php", "tests/**/*.php"],
            "ruby": ["*_spec.rb", "spec/**/*.rb"],
        }

        patterns = test_patterns.get(language, [])
        test_files = []
        for pattern in patterns:
            test_files.extend(repo_path.rglob(pattern))

        return test_files[:50]  # Limit to 50 files

    def _find_entry_points(self, repo_path: Path, language: str) -> list[str]:
        """Find likely entry points (main files)."""
        entry_patterns = {
            "python": ["main.py", "__main__.py", "cli.py", "app.py", "run.py", "server.py"],
            "javascript": ["index.js", "main.js", "app.js", "server.js", "cli.js"],
            "typescript": ["index.ts", "main.ts", "app.ts", "server.ts", "cli.ts"],
            "go": ["main.go", "cmd/main.go", "cmd/*/main.go"],
            "rust": ["src/main.rs", "src/bin/*.rs"],
            "java": ["src/main/java/**/Main.java", "src/main/java/**/Application.java"],
            "csharp": ["Program.cs", "*/Program.cs"],
            "php": ["index.php", "public/index.php"],
            "ruby": ["main.rb", "app.rb", "bin/*"],
        }

        patterns = entry_patterns.get(language, [])
        entries = []
        for pattern in patterns:
            matches = list(repo_path.rglob(pattern))
            entries.extend([str(p.relative_to(repo_path)) for p in matches])

        return entries[:10]

    def _detect_framework(self, repo_path: Path, language: str) -> str | None:
        """Detect web/app framework."""
        frameworks = {
            "python": {
                "fastapi": ["fastapi", "FastAPI"],
                "django": ["django", "Django"],
                "flask": ["flask", "Flask"],
                "starlette": ["starlette"],
                "tornado": ["tornado"],
            },
            "javascript": {
                "express": ["express"],
                "next": ["next"],
                "nuxt": ["nuxt"],
                "react": ["react"],
                "vue": ["vue"],
                "svelte": ["svelte"],
                "nest": ["@nestjs"],
            },
            "typescript": {
                "next": ["next"],
                "nest": ["@nestjs"],
                "react": ["react"],
            },
            "go": {
                "gin": ["gin-gonic/gin"],
                "echo": ["labstack/echo"],
                "fiber": ["gofiber/fiber"],
            },
            "rust": {
                "actix": ["actix-web"],
                "axum": ["axum"],
                "warp": ["warp"],
            },
        }

        lang_frameworks = frameworks.get(language, {})

        # Check package.json / Cargo.toml / pyproject.toml / go.mod for dependencies
        dep_files = {
            "python": ["pyproject.toml", "requirements.txt", "setup.py"],
            "javascript": ["package.json"],
            "typescript": ["package.json"],
            "go": ["go.mod"],
            "rust": ["Cargo.toml"],
        }

        files_to_check = dep_files.get(language, [])
        content = ""
        for f in files_to_check:
            matches = list(repo_path.rglob(f))
            if matches:
                content += matches[0].read_text() + "\n"

        for fw, keywords in lang_frameworks.items():
            for kw in keywords:
                if kw in content:
                    return fw

        return None

    async def _get_git_remote(self, repo_path: Path) -> str | None:
        """Get git remote URL."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "remote",
                "get-url",
                "origin",
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode().strip()
        except Exception:
            pass
        return None

    async def run_tests(self, repo_path: Path, test_command: str | None = None) -> BrowserResult:
        """Run tests in repository."""
        info = await self.analyze_repo(repo_path)
        cmd = test_command or info.test_command

        if not cmd:
            return BrowserResult(False, "run_tests", str(repo_path), error="No test command detected")

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            return BrowserResult(
                proc.returncode == 0,
                "run_tests",
                str(repo_path),
                "Tests passed" if proc.returncode == 0 else "Tests failed",
                data={
                    "command": cmd,
                    "stdout": stdout.decode()[-5000:],  # Last 5000 chars
                    "stderr": stderr.decode()[-5000:],
                    "returncode": proc.returncode,
                },
                error=None if proc.returncode == 0 else stderr.decode()[-1000:],
            )
        except Exception as e:
            return BrowserResult(False, "run_tests", str(repo_path), error=str(e))

    async def install_dependencies(self, repo_path: Path) -> BrowserResult:
        """Install dependencies using detected package manager."""
        info = await self.analyze_repo(repo_path)
        cmd = info.build_command

        if not cmd:
            return BrowserResult(False, "install_deps", str(repo_path), error="No build command detected")

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            return BrowserResult(
                proc.returncode == 0,
                "install_deps",
                str(repo_path),
                "Dependencies installed" if proc.returncode == 0 else "Install failed",
                data={"command": cmd, "stdout": stdout.decode()[-2000:], "stderr": stderr.decode()[-2000:]},
                error=None if proc.returncode == 0 else stderr.decode()[-1000:],
            )
        except Exception as e:
            return BrowserResult(False, "install_deps", str(repo_path), error=str(e))

    async def cleanup_repo(self, repo_path: Path) -> None:
        """Clean up cloned repository."""
        if repo_path.exists():
            shutil.rmtree(repo_path, ignore_errors=True)
