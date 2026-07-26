from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import httpx


class TestTelegramBot:
    def test_import(self):
        from core.notifications.telegram.bot import TelegramBot, get_telegram_bot, reset_telegram_bot

        assert TelegramBot
        assert callable(get_telegram_bot)
        assert callable(reset_telegram_bot)

    def test_send_no_token(self):
        from core.notifications.telegram.bot import TelegramBot
        from core.notifications.telegram.config import TelegramConfig

        config = TelegramConfig(token="", chat_id="")
        bot = TelegramBot(config)
        result = bot.send("test")
        assert result["ok"] is False

    def test_send_alert_no_chat(self):
        from core.notifications.telegram.bot import TelegramBot
        from core.notifications.telegram.config import TelegramConfig

        config = TelegramConfig(token="abc", chat_id="")
        bot = TelegramBot(config)
        result = bot.send_alert(title="test", body="body", priority="high")
        assert result["ok"] is False
        assert "chat_id" in result["error"]

    def test_send_alert_formats_priority(self):
        from core.notifications.telegram.bot import TelegramBot
        from core.notifications.telegram.config import TelegramConfig

        config = TelegramConfig(token="abc", chat_id="123")
        bot = TelegramBot(config)
        with patch.object(bot, "_api", return_value={"ok": True}) as mock_api:
            bot.send_alert(title="Hello", body="World", priority="critical")
            call_text = mock_api.call_args[1]["text"]
            assert "🚨" in call_text
            assert "Hello" in call_text
            assert "World" in call_text


class TestHackerOneConnector:
    def test_import(self):
        from core.bugbounty.hackerone import HackerOneConnector, get_hackerone_connector

        assert HackerOneConnector
        assert callable(get_hackerone_connector)

    def test_is_enabled_false_by_default(self):
        from core.bugbounty.hackerone import HackerOneConnector

        conn = HackerOneConnector()
        assert conn.is_enabled is False

    def test_is_enabled_true_with_env(self):
        with patch.dict(os.environ, {"HACKERONE_API_USERNAME": "user", "HACKERONE_API_TOKEN": "tok"}):
            from core.bugbounty.hackerone import HackerOneConnector

            conn = HackerOneConnector()
            assert conn.is_enabled is True

    def test_get_programs_httpx_error(self):
        from core.bugbounty.hackerone import HackerOneConnector

        conn = HackerOneConnector()
        with patch.object(conn, "_enabled", True):
            with patch("httpx.get", side_effect=httpx.ConnectError("mock fail")):
                result = conn.get_programs()
        assert result == []

    def test_get_programs_empty_response(self):
        from core.bugbounty.hackerone import HackerOneConnector

        conn = HackerOneConnector()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": []}
        with patch.object(conn, "_enabled", True):
            with patch("httpx.get", return_value=mock_resp):
                result = conn.get_programs()
        assert result == []


class TestOSINTEngine:
    def test_import(self):
        from core.osint.engine import OSINTEngine, get_osint_engine

        assert OSINTEngine
        assert callable(get_osint_engine)

    def test_dns_resolve_no_records(self):
        from core.osint.engine import OSINTEngine

        engine = OSINTEngine()
        result = engine.dns_resolve("nonexistent.invalid.test", "A")
        assert isinstance(result, dict)
        assert "records" in result

    def test_crtsh_bad_domain(self):
        from core.osint.engine import OSINTEngine

        engine = OSINTEngine()
        result = engine.crtsh_search("")
        assert isinstance(result, (list, dict))

    def test_email_security_no_domain(self):
        from core.osint.engine import OSINTEngine

        engine = OSINTEngine()
        result = engine.email_security("")
        assert isinstance(result, dict)

    def test_geoip_error_on_invalid_ip(self):
        from core.osint.engine import OSINTEngine

        engine = OSINTEngine()
        result = engine.geoip("999.999.999.999")
        assert isinstance(result, dict)

    def test_reverse_ip_invalid(self):
        from core.osint.engine import OSINTEngine

        engine = OSINTEngine()
        result = engine.reverse_ip("999.999.999.999")
        assert "error" in result or "ip" in result or "domains" in result

    def test_domain_recon_edge_case(self):
        from core.osint.engine import OSINTEngine

        engine = OSINTEngine()
        result = engine.domain_recon("")
        assert isinstance(result, dict)

    def test_subdomain_discover_edge_case(self):
        from core.osint.engine import OSINTEngine

        engine = OSINTEngine()
        result = engine.subdomain_discover("")
        assert isinstance(result, (list, dict))

    def test_bridge_registration(self):
        from cores.notifications.bridges import register_telegram_channel

        assert callable(register_telegram_channel)
