"""Vidriera estática Droppinglabel — render honesto desde ACTIVE reales."""

from __future__ import annotations


def _prod(**kw):
    base = {
        "id": "p1",
        "name": "Khamrah 100ml",
        "sale_price_ars": 95000,
        "sale_price_usd": 0,
        "authenticity": "official",
        "niche": "perfumes",
        "image": "",
        "meli_url": "",
    }
    base.update(kw)
    return base


class TestRender:
    def test_vacia_honesta(self):
        from cores.ecommerce.storefront import render_storefront

        page = render_storefront([])
        assert "en preparación" in page
        assert "0 productos" in page

    def test_precio_ars_preferido(self):
        from cores.ecommerce.storefront import render_storefront

        page = render_storefront([_prod(sale_price_ars=95000, sale_price_usd=100)])
        assert "$ 95.000" in page
        assert "USD" not in page

    def test_sin_precio_no_hay_tarjeta(self):
        from cores.ecommerce.storefront import render_storefront

        page = render_storefront([_prod(sale_price_ars=0, sale_price_usd=0)])
        assert "Khamrah" not in page
        assert "en preparación" in page

    def test_escape_xss(self):
        from cores.ecommerce.storefront import render_storefront

        page = render_storefront([_prod(name="<script>alert(1)</script>")])
        assert "<script>" not in page
        assert "&lt;script&gt;" in page

    def test_tag_replica_visible(self):
        from cores.ecommerce.storefront import render_storefront

        page = render_storefront([_prod(authenticity="replica")])
        assert "réplica" in page

    def test_wa_link_con_numero_y_generico(self):
        from cores.ecommerce.storefront import _wa_order_url

        assert _wa_order_url("X", "5491100000000").startswith("https://wa.me/5491100000000?text=")
        assert _wa_order_url("X").startswith("https://wa.me/?text=")

    def test_meli_link_solo_si_hay(self):
        from cores.ecommerce.storefront import render_storefront

        assert "Comprar en Meli" in render_storefront([_prod(meli_url="https://articulo.mercadolibre.com.ar/x")])
        assert "Comprar en Meli" not in render_storefront([_prod()])


class TestBuild:
    def test_build_tmp_roundtrip(self, tmp_path):
        from cores.ecommerce.storefront import build_storefront_file

        class FakeEngine:
            def list_products(self, status=None):
                from types import SimpleNamespace

                return [
                    SimpleNamespace(
                        id="p1",
                        name="Yara 100ml",
                        sale_price_ars=105000,
                        sale_price_usd=0,
                        authenticity="official",
                        supplier_id="canevic_perf",
                        category="perfumes",
                        images=[],
                        marketplace_listings={},
                    )
                ]

        out = build_storefront_file(FakeEngine(), path=tmp_path / "index.html")
        assert out["success"] is True
        assert out["products"] == 1
        content = (tmp_path / "index.html").read_text(encoding="utf-8")
        assert "Yara" in content and "$ 105.000" in content

    def test_build_sin_active(self, tmp_path):
        from cores.ecommerce.storefront import build_storefront_file

        class FakeEngine:
            def list_products(self, status=None):
                return []

        out = build_storefront_file(FakeEngine(), path=tmp_path / "index.html")
        assert out["success"] is True
        assert out["products"] == 0


class TestEndpoints:
    def test_preview_y_build_200(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.ecommerce import router

        bare = FastAPI()
        bare.include_router(router)
        client = TestClient(bare)
        r = client.get("/api/ecommerce/storefront/preview")
        assert r.status_code == 200
        assert "Catálogo" in r.text or "catalogo" in r.text.lower() or "html" in r.text.lower()
        r2 = client.post("/api/ecommerce/storefront/build")
        assert r2.status_code == 200
        assert r2.json()["success"] is True


class TestProSections:
    def _page(self):
        from cores.ecommerce.storefront import render_storefront

        return render_storefront(
            [
                _prod(name="Khamrah", niche="perfumes"),
                _prod(id="p2", name="Retro 86", sale_price_ars=59900, niche="futbol", authenticity="replica"),
            ]
        )

    def test_agrupa_por_categoria_con_anclas(self):
        page = self._page()
        assert "id='perfumes'" in page
        assert "id='futbol'" in page
        assert "href='#perfumes'" in page
        assert "Perfumes árabes y nicho" in page

    def test_trust_faq_y_jsonld(self):
        page = self._page()
        assert "Envío a todo el país" in page
        assert "Preguntas frecuentes" in page
        assert "application/ld+json" in page
        assert '"@type":"Store"' in page

    def test_sin_testimonios_ni_descuentos_inventados(self):
        page = self._page()
        assert "testimon" not in page.lower()
        assert "opiniones de clientes" not in page.lower()
        assert "% off" not in page.lower()
        assert "quedan" not in page.lower()

    def test_meta_seo_y_boton_flotante(self):
        page = self._page()
        assert "name='description'" in page
        assert "class='float'" in page
        assert "viewport" in page


class TestGratisYAutomatico:
    """Invariantes $0 + auto: sin dependencias pagas, jobs que nunca rompen."""

    def test_sin_dependencias_externas_pagas(self):
        from cores.ecommerce.storefront import render_storefront

        page = render_storefront([_prod(image="https://proveedor.com/foto.jpg")])
        assert "<script src" not in page
        assert "<link" not in page
        assert "@import" not in page
        assert "fonts.googleapis" not in page
        assert "fonts.gstatic" not in page

    def test_render_nunca_raisea_con_basura(self):
        from cores.ecommerce.storefront import render_storefront

        for garbage in (None, "x", [None, 123, {}, {"name": None}], [{"name": "A"}]):
            page = render_storefront(garbage)  # type: ignore[arg-type]
            assert "<!DOCTYPE html>" in page

    def test_job_registrado_y_handler_resuelve(self):
        import importlib

        from cores.ecommerce.pipeline import get_ecommerce_jobs

        jobs = {j.job_id: j for j in get_ecommerce_jobs()}
        assert "ecommerce_storefront_refresh" in jobs
        mod_name, attr = jobs["ecommerce_storefront_refresh"].handler.split(":")
        assert callable(getattr(importlib.import_module(mod_name), attr))

    def test_handler_corre_sin_credenciales(self, tmp_path, monkeypatch):
        from cores.ecommerce.pipeline import run_ecommerce_storefront_refresh

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        out = run_ecommerce_storefront_refresh()
        assert out["success"] is True
        assert (tmp_path / "droppinglabel_index.html").exists()
