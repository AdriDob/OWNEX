"""Moonshot $50k/mes: matemática de factibilidad, no promesa."""

from __future__ import annotations


def _tracker(tmp_path):
    from cores.first_money.tracker import FirstMoneyTracker

    return FirstMoneyTracker(storage_path=tmp_path / "fm")


class TestMoonshot:
    def test_50k_no_factible_solo_con_30h(self, tmp_path):
        out = _tracker(tmp_path).get_moonshot_plan(50000, 30)
        assert out["target_monthly_usd"] == 50000
        assert out["feasible_solo"] is False
        assert out["shortfall_usd"] >= 0
        assert out["leverage_needed"], "sin apalancamiento no hay plan honesto"
        assert out["verdict"].startswith("NO_FACTIBLE_SOLO")
        assert "HIPÓTESIS" in out["assumptions"]

    def test_meta_chica_si_factible(self, tmp_path):
        out = _tracker(tmp_path).get_moonshot_plan(3000, 30)
        assert out["feasible_solo"] is True
        assert out["shortfall_usd"] == 0
        assert out["verdict"].startswith("FACTIBLE_SOLO")

    def test_horas_mandan(self, tmp_path):
        poco = _tracker(tmp_path).get_moonshot_plan(20000, 5)
        mucho = _tracker(tmp_path).get_moonshot_plan(20000, 80)
        assert poco["hours_per_week_needed"] == mucho["hours_per_week_needed"]
        assert poco["feasible_solo"] is False
        assert mucho["feasible_solo"] is True

    def test_suma_no_supera_objetivo(self, tmp_path):
        out = _tracker(tmp_path).get_moonshot_plan(50000, 30)
        total = sum(a["monthly_usd"] for a in out["allocation"])
        assert total <= 50000
        assert total + out["shortfall_usd"] == 50000

    def test_endpoint_200_y_422(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.first_money import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        r = client.get("/first-money/moonshot-plan?target_monthly_usd=50000&hours_per_week=30")
        assert r.status_code == 200
        assert r.json()["target_monthly_usd"] == 50000
        assert client.get("/first-money/moonshot-plan?target_monthly_usd=-5").status_code == 422


class TestBugbounty7mo:
    def test_meses_y_acumulados_coherentes(self, tmp_path):
        from cores.first_money.tracker import FirstMoneyTracker

        out = FirstMoneyTracker(storage_path=tmp_path / "fm").get_bugbounty_7mo_plan()
        assert len(out["months"]) == 7
        cum = out["cumulative"]
        assert cum["flojo"] == sum(m["low"] for m in out["months"])
        assert cum["central"] == sum(m["central"] for m in out["months"])
        assert cum["fuerte"] == sum(m["high"] for m in out["months"])
        assert cum["flojo"] <= cum["central"] <= cum["fuerte"]
        assert 12000 <= cum["central"] <= 18000
        assert "HIPÓTESIS" in out["basis"]

    def test_endpoint_200(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.first_money import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        r = client.get("/first-money/bugbounty-7mo-plan")
        assert r.status_code == 200
        assert len(r.json()["months"]) == 7


class TestBugbountyProgress:
    def _tracker(self, tmp_path):
        from cores.first_money.tracker import FirstMoneyTracker

        return FirstMoneyTracker(storage_path=tmp_path / "fm")

    def test_mes_determinista_por_fecha(self, tmp_path):
        t = self._tracker(tmp_path)
        assert t.get_bugbounty_progress("2026-10-15")["month"]["m"] == 1
        assert t.get_bugbounty_progress("2027-02-01")["month"]["m"] == 5
        assert t.get_bugbounty_progress("2027-12-01")["month"]["m"] == 7  # cap
        assert t.get_bugbounty_progress("2026-01-01")["month"]["m"] == 1  # floor

    def test_sin_datos_no_inventa(self, tmp_path):
        out = self._tracker(tmp_path).get_bugbounty_progress("2026-10-15")
        assert out["earned_usd"] == 0.0
        assert out["expected_cum_central_usd"] == 0
        assert out["status"] == "on_track"

    def test_detras_con_gap(self, tmp_path):
        out = self._tracker(tmp_path).get_bugbounty_progress("2027-04-15")
        assert out["month"]["m"] == 7
        assert out["status"] == "behind"
        assert "revisar volumen" in out["verdict"]

    def test_endpoint_200(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.first_money import router

        app = FastAPI()
        app.include_router(router)
        r = TestClient(app).get("/first-money/bugbounty-progress")
        assert r.status_code == 200
        assert {"month", "earned_usd", "status", "verdict"} <= set(r.json())
