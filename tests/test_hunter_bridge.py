"""Tests for hunter bridge — external bug bounty toolkit integrations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.integrations.ext.hunter_bridge import (
    HUNTER_TO_RASTRO_VULN,
    WEB3_VULN_CLASSES,
    check_hunter,
    check_mcp_hunter,
    check_web3_skills,
    get_web3_poc_template,
    get_web3_skill_path,
    install_hunter,
    run_hunter_scan,
    status_summary,
)

# ── Tests: vuln class mapping ──────────────────────────────────────


class TestVulnMapping:
    def test_hunter_covers_20_vuln_classes(self):
        assert len(HUNTER_TO_RASTRO_VULN) >= 20

    def test_web3_covers_10_vuln_classes(self):
        assert len(WEB3_VULN_CLASSES) == 10

    def test_idor_maps_correctly(self):
        assert HUNTER_TO_RASTRO_VULN["idor"] == "idor"

    def test_auth_bypass_maps(self):
        assert HUNTER_TO_RASTRO_VULN["auth-bypass"] == "auth_bypass"

    def test_ssrf_maps(self):
        assert HUNTER_TO_RASTRO_VULN["ssrf"] == "ssrf"

    def test_all_values_are_unique_except_idor_bola(self):
        """idor and bola both map to 'idor' (duplicate on purpose)."""
        vals = list(HUNTER_TO_RASTRO_VULN.values())
        non_idor = [v for v in vals if v != "idor"]
        assert len(non_idor) == len(set(non_idor))


# ── Tests: check_* status ─────────────────────────────────────────


class TestCheckHunter:
    def test_not_installed(self):
        with patch("core.integrations.ext.hunter_bridge.HUNTER_REPO_DIR") as mock_path:
            mock_path.exists.return_value = False
            result = check_hunter()
            assert result["installed"] is False

    def test_installed_reports_version(self):
        with patch("core.integrations.ext.hunter_bridge.HUNTER_REPO_DIR") as mock_path:
            mock_path.exists.return_value = True
            (mock_path / ".git" / "HEAD").exists.return_value = True
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "abc123 fix: stuff\n"
                (mock_path / "engine.py").exists.return_value = True
                (mock_path / "install.sh").exists.return_value = True
                result = check_hunter()
                assert result["installed"] is True
                assert result["has_engine"] is True
                assert result["vuln_classes"] == len(HUNTER_TO_RASTRO_VULN)


class TestCheckWeb3Skills:
    def test_not_installed(self):
        with patch("core.integrations.ext.hunter_bridge.WEB3_SKILLS_DIR") as mock_path:
            mock_path.exists.return_value = False
            result = check_web3_skills()
            assert result["installed"] is False

    def test_installed_reports_skills(self):
        with patch("core.integrations.ext.hunter_bridge.WEB3_SKILLS_DIR") as mock_path:
            mock_path.exists.return_value = True
            mock_path.glob.return_value = [MagicMock() for _ in range(5)]
            (mock_path / ".git" / "HEAD").exists.return_value = True
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "def456\n"
                result = check_web3_skills()
                assert result["installed"] is True
                assert result["skill_files"] == 5


class TestCheckMCPHunter:
    def test_not_installed(self):
        with patch("core.integrations.ext.hunter_bridge.MCP_HUNTER_DIR") as mock_path:
            mock_path.exists.return_value = False
            result = check_mcp_hunter()
            assert result["installed"] is False

    def test_installed(self):
        with patch("core.integrations.ext.hunter_bridge.MCP_HUNTER_DIR") as mock_path:
            mock_path.exists.return_value = True
            (mock_path / ".git" / "HEAD").exists.return_value = True
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "ghi789\n"
                (mock_path / "bounty_hunter" / "server.py").exists.return_value = True
                result = check_mcp_hunter()
                assert result["installed"] is True
                assert result["has_server"] is True


# ── Tests: install helpers ─────────────────────────────────────────


class TestInstallHunter:
    def test_already_installed(self):
        with patch("core.integrations.ext.hunter_bridge.HUNTER_REPO_DIR") as mock_path:
            mock_path.exists.return_value = True
            mock_path.parent.mkdir = MagicMock()
            result = install_hunter()
            assert result["status"] == "already_installed"

    def test_clone_success(self):
        with patch("core.integrations.ext.hunter_bridge.HUNTER_REPO_DIR") as mock_path:
            mock_path.exists.return_value = False
            mock_path.parent.mkdir = MagicMock()
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                result = install_hunter()
                assert result["status"] == "installed"

    def test_clone_failure(self):
        with patch("core.integrations.ext.hunter_bridge.HUNTER_REPO_DIR") as mock_path:
            mock_path.exists.return_value = False
            mock_path.parent.mkdir = MagicMock()
            with patch("subprocess.run", side_effect=Exception("git error")):
                result = install_hunter()
                assert result["status"] == "error"


# ── Tests: execution bridges ───────────────────────────────────────


class TestRunHunterScan:
    def test_not_installed(self):
        with patch("core.integrations.ext.hunter_bridge.check_hunter") as mock_check:
            mock_check.return_value = {"installed": False}
            result = run_hunter_scan("test.com")
            assert result["status"] == "not_installed"

    def test_scan_timeout(self):
        with patch("core.integrations.ext.hunter_bridge.check_hunter") as mock_check:
            mock_check.return_value = {"installed": True}
            with patch("shutil.which") as mock_which:
                mock_which.return_value = "/usr/bin/python3"
                with patch(
                    "subprocess.run", side_effect=__import__("subprocess").TimeoutExpired(cmd="test", timeout=600)
                ):
                    result = run_hunter_scan("test.com")
                    assert result["status"] == "timeout"

    def test_scan_success(self):
        with patch("core.integrations.ext.hunter_bridge.check_hunter") as mock_check:
            mock_check.return_value = {"installed": True}
            with patch("shutil.which") as mock_which:
                mock_which.return_value = "/usr/local/bin/bughunter"
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stdout = "Found 3 endpoints"
                    mock_run.return_value.stderr = ""
                    result = run_hunter_scan("test.com", vuln_classes=["idor", "ssrf"])
                    assert result["status"] == "completed"


# ── Tests: web3 helpers ────────────────────────────────────────────


class TestWeb3Helpers:
    def test_get_skill_path_not_installed(self):
        with patch("core.integrations.ext.hunter_bridge.check_web3_skills") as mock_check:
            mock_check.return_value = {"installed": False}
            assert get_web3_skill_path("reentrancy") is None

    def test_get_poc_template_not_installed(self):
        with patch("core.integrations.ext.hunter_bridge.check_web3_skills") as mock_check:
            mock_check.return_value = {"installed": False}
            assert get_web3_poc_template("reentrancy") is None


# ── Tests: status_summary ─────────────────────────────────────────


class TestStatusSummary:
    def test_summary_includes_all_keys(self):
        with patch("core.integrations.ext.hunter_bridge.check_hunter") as mock_h:
            mock_h.return_value = {"installed": False}
            with patch("core.integrations.ext.hunter_bridge.check_web3_skills") as mock_w:
                mock_w.return_value = {"installed": False}
                with patch("core.integrations.ext.hunter_bridge.check_mcp_hunter") as mock_m:
                    mock_m.return_value = {"installed": False}
                    summary = status_summary()
                    assert "claude_bug_bounty" in summary
                    assert "web3_bug_bounty_skills" in summary
                    assert "bounty_hunter_mcp" in summary
                    assert "checked_at" in summary
