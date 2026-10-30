"""Secret scanning: dejar de reportar "0 secretos" sin haber escaneado.

Por qué existe (auditoría 2026-10-05):

`bugbounty_hunter._stage_secrets(domain)` llamaba
`adapter.run(domain, repo_path=f"https://github.com/{domain}")`. Gitleaks sólo
acepta **paths locales** en `--source`, así que `FileNotFoundError` → output
vacío → el `except` del caller lo logueaba como warning y el stage terminaba
reportando "0 secretos".

Peor: la URL tampoco era un repo. Con `domain="docs.hackerone.com"` armaba
`https://github.com/docs.hackerone.com`, que no existe como repositorio. El
stage **no podía** funcionar nunca, para ningún dominio.

Un escáner que siempre devuelve 0 hallazgos no es un escáner: es ruido que
se lee como "revisado y limpio".

Estos tests fijan: sin repo configurado, el stage se OMITE (no reporta 0
hallazgos); con repo, escanea ese repo.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cores.revenue_multiplier.bugbounty_hunter import BugBountyHunter
from cores.revenue_multiplier.config import RevenueMultiplierConfig


@pytest.fixture
def hunter() -> BugBountyHunter:
    return BugBountyHunter(RevenueMultiplierConfig(secret_scan_repos={}))


class TestSecretScanNotFaked:
    def test_sin_repo_configurado_no_escanea(self, hunter: BugBountyHunter) -> None:
        """El caso del bug: sin repo, NO se inventa un escaneo."""
        adapter = MagicMock()
        adapter.run.return_value = []

        with patch.object(hunter, "_get_adapter", return_value=adapter):
            hunter._stage_secrets("acme.com")

        adapter.run.assert_not_called(), "no debe escanear nada sin repo configurado"
        assert hunter._findings == [], "y no debe inventar hallazgos"

    def test_url_de_dominio_nunca_se_trata_como_repo(self, hunter: BugBountyHunter) -> None:
        """`https://github.com/{dominio}` no es un repo: no debe armarse solo."""
        adapter = MagicMock()
        adapter.run.return_value = []

        with patch.object(hunter, "_get_adapter", return_value=adapter):
            hunter._stage_secrets("docs.hackerone.com")

        for call in adapter.run.call_args_list:
            url = call.args[0] if call.args else ""
            assert "docs.hackerone.com" not in str(url), f"se armó una URL de dominio: {url}"

    def test_con_repo_escanea_ese_repo(self) -> None:
        cfg = RevenueMultiplierConfig(secret_scan_repos={"acme.com": ["https://github.com/acme/api"]})
        hunter = BugBountyHunter(cfg)
        adapter = MagicMock()
        adapter.run.return_value = [MagicMock(tool="gitleaks")]

        with patch.object(hunter, "_get_adapter", return_value=adapter):
            hunter._stage_secrets("acme.com")

        adapter.run.assert_called_once_with("https://github.com/acme/api")

    def test_escancha_multiples_repos(self) -> None:
        cfg = RevenueMultiplierConfig(
            secret_scan_repos={"acme.com": ["https://github.com/acme/api", "https://github.com/acme/web"]}
        )
        hunter = BugBountyHunter(cfg)
        adapter = MagicMock()
        adapter.run.return_value = []

        with patch.object(hunter, "_get_adapter", return_value=adapter):
            hunter._stage_secrets("acme.com")

        assert adapter.run.call_count == 2

    def test_error_de_un_repo_no_mata_el_siguiente(self) -> None:
        cfg = RevenueMultiplierConfig(
            secret_scan_repos={"acme.com": ["https://github.com/acme/bad", "https://github.com/acme/good"]}
        )
        hunter = BugBountyHunter(cfg)
        adapter = MagicMock()
        adapter.run.side_effect = [RuntimeError("boom"), []]
        hunter._findings = []

        with patch.object(hunter, "_get_adapter", return_value=adapter):
            hunter._stage_secrets("acme.com")

        assert adapter.run.call_count == 2, "un repo roto no puede cortar el stage"


class TestGitleaksCloneGuard:
    def test_url_no_github_devuelve_none(self) -> None:
        """Sólo github.com: un dominio suelto no es clonable."""
        from cores.revenue_multiplier.adapters.base import GitleaksAdapter

        path, tmp = GitleaksAdapter._clone_for_scan("https://gitlab.com/acme/api")
        assert path is None and tmp is None

    def test_url_github_tiene_forma_correcta(self) -> None:
        """Guard de parsing: owner/repo, sin query ni fragment."""
        import re

        url = "https://github.com/acme/api.git?tab=readme#x"
        m = re.match(r"^https?://github\.com/([^/]+)/([^/?#]+)", url)
        assert m is not None
        assert m.group(1) == "acme"
        assert m.group(2).removesuffix(".git") == "api"
