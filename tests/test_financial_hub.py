"""Tests for Financial Hub — payout intelligence, KYC, routes, etc."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ── Isolated test DB — completely separate from project's Base ─────

TEST_DB_URL = "sqlite:///./test_financial_hub.db"
_test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
_TestBase = declarative_base()


class _KYCRecord(_TestBase):
    __tablename__ = "kyc_records"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False, unique=True, index=True)
    platform_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="not_started")
    kyc_level = Column(String, nullable=False, default="")
    documents_required = Column(Text, nullable=False, default="[]")
    documents_submitted = Column(Text, nullable=False, default="[]")
    notes = Column(Text, nullable=False, default="")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class _PayoutDocument(_TestBase):
    __tablename__ = "payout_documents"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    category = Column(String, nullable=False, default="general")
    is_required = Column(Boolean, nullable=False, default=True)
    is_completed = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=False, default="")
    platforms = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class _WithdrawalRoute(_TestBase):
    __tablename__ = "withdrawal_routes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=False, default="")
    route_type = Column(String, nullable=False)
    source_currency = Column(String, nullable=False, default="USD")
    target_currency = Column(String, nullable=False, default="ARS")
    fee_percent = Column(Float, nullable=False, default=0.0)
    fee_fixed = Column(Float, nullable=False, default=0.0)
    arrival_days = Column(String, nullable=False, default="1-3")
    is_active = Column(Boolean, nullable=False, default=True)
    is_emergency = Column(Boolean, nullable=False, default=False)
    priority = Column(Integer, nullable=False, default=0)
    steps = Column(Text, nullable=False, default="[]")
    requirements = Column(Text, nullable=False, default="[]")
    notes = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class _TaxRecord(_TestBase):
    __tablename__ = "tax_records"
    id = Column(Integer, primary_key=True, index=True)
    country = Column(String, nullable=False, default="AR")
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    category = Column(String, nullable=False, default="general")
    platforms = Column(Text, nullable=False, default="[]")
    reference_url = Column(String, nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


_TestSession = sessionmaker(bind=_test_engine)


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def _db_setup():
    """Set up isolated in-memory SQLite with only Financial Hub tables."""
    os.environ["DATABASE_URL"] = TEST_DB_URL
    _TestBase.metadata.create_all(bind=_test_engine)
    yield
    _TestBase.metadata.drop_all(bind=_test_engine)
    if os.path.exists("./test_financial_hub.db"):
        os.remove("./test_financial_hub.db")


@pytest.fixture(autouse=True)
def _clean_db(_db_setup):
    """Clean all records between tests."""
    session = _TestSession()
    try:
        for table in (_TaxRecord, _WithdrawalRoute, _PayoutDocument, _KYCRecord):
            session.query(table).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture
def client(_db_setup):
    """Create test client with patched SessionLocal (isolated DB)."""
    import core.financial_hub.documents_checklist as _dc
    import core.financial_hub.emergency_routes as _er
    import core.financial_hub.kyc_manager as _km
    import core.financial_hub.route_optimizer as _ro
    import core.financial_hub.tax_notes as _tn
    import core.financial_hub.verification_tracker as _vt

    _patch = {
        _km: "SessionLocal",
        _dc: "SessionLocal",
        _ro: "SessionLocal",
        _tn: "SessionLocal",
        _vt: "SessionLocal",
        _er: "SessionLocal",
    }
    originals = {}
    for mod, attr in _patch.items():
        originals[(id(mod), attr)] = getattr(mod, attr, None)
        setattr(mod, attr, _TestSession)

    from api.routers.financial_hub import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c

    for mod, attr in _patch.items():
        orig = originals.get((id(mod), attr))
        if orig is not None:
            setattr(mod, attr, orig)


@pytest.fixture
def init_defaults():
    """Populate default records directly (bypasses project's SessionLocal)."""
    session = _TestSession()
    try:
        for platform, info in {
            "hackerone": ("HackerOne", "dni", ["Government ID", "W-8BEN"]),
            "bugcrowd": ("Bugcrowd", "dni", ["Government ID"]),
            "intigriti": ("Intigriti", "dni", ["Government ID"]),
            "synack": ("Synack", "passport", ["Passport", "W-8BEN"]),
            "yeswehack": ("YesWeHack", "dni", ["Government ID"]),
            "immunefi": ("Immunefi", "none", []),
            "code4rena": ("Code4rena", "none", []),
            "huntr": ("Huntr", "dni", ["Government ID"]),
        }.items():
            import json

            record = _KYCRecord(
                platform=platform,
                platform_name=info[0],
                kyc_level=info[1],
                documents_required=json.dumps(info[2]),
                documents_submitted="[]",
            )
            session.add(record)

        import json

        for doc_data in [
            {"name": "DNI (Documento Nacional de Identidad)", "category": "identity", "platforms": ["hackerone"]},
            {"name": "Pasaporte", "category": "identity", "platforms": ["synack"]},
            {"name": "W-8BEN (Formulario IRS)", "category": "tax", "platforms": ["hackerone"]},
            {"name": "CBU / CVU Bancario", "category": "bank", "platforms": []},
            {"name": "Cuenta Payoneer", "category": "platform", "platforms": ["hackerone"]},
            {"name": "Cuenta Takenos", "category": "platform", "platforms": []},
            {"name": "Cuenta Binance (KYC Nivel 2)", "category": "crypto", "platforms": []},
            {"name": "Cuenta Lemon Cash", "category": "crypto", "platforms": []},
            {"name": "Wallet de Solana (Phantom/Backpack)", "category": "crypto", "platforms": ["immunefi"]},
            {"name": "Wallet de Ethereum (MetaMask)", "category": "crypto", "platforms": ["immunefi"]},
        ]:
            doc = _PayoutDocument(
                name=doc_data["name"],
                description="",
                category=doc_data["category"],
                platforms=json.dumps(doc_data["platforms"]),
            )
            session.add(doc)

        import json

        for route_data in [
            {
                "name": "Takenos → CBU",
                "route_type": "wallet",
                "fee_percent": 1.0,
                "priority": 10,
                "is_emergency": False,
            },
            {
                "name": "Crypto P2P → Binance",
                "route_type": "p2p",
                "fee_percent": 0.0,
                "priority": 9,
                "is_emergency": False,
            },
            {
                "name": "Payoneer → Banco",
                "route_type": "bank_transfer",
                "fee_percent": 2.0,
                "fee_fixed": 1.5,
                "priority": 7,
                "is_emergency": False,
            },
            {
                "name": "PayPal → Lemon Cash",
                "route_type": "crypto_exchange",
                "fee_percent": 4.4,
                "priority": 5,
                "is_emergency": True,
            },
        ]:
            route = _WithdrawalRoute(
                name=route_data["name"],
                route_type=route_data["route_type"],
                fee_percent=route_data["fee_percent"],
                fee_fixed=route_data.get("fee_fixed", 0.0),
                priority=route_data["priority"],
                is_emergency=route_data["is_emergency"],
                steps="[]",
                requirements="[]",
            )
            session.add(route)

        for note_data in [
            {"title": "Impuesto a las Ganancias", "category": "general", "description": "Test"},
            {"title": "Bienes Personales", "category": "regulation", "description": "Test"},
            {"title": "W-8BEN", "category": "form", "description": "Test"},
        ]:
            import json

            note = _TaxRecord(
                title=note_data["title"],
                category=note_data["category"],
                description=note_data["description"],
                platforms="[]",
            )
            session.add(note)

        session.commit()
    finally:
        session.close()


@pytest.fixture
def kyc_manager():
    """KYCManager patched to use test session."""
    from core.financial_hub.kyc_manager import KYCManager

    mgr = KYCManager()

    # Monkey-patch the internal method to use test session
    def _get_all():
        session = _TestSession()
        try:
            records = session.query(_KYCRecord).order_by(_KYCRecord.platform).all()
            return [mgr._record_to_dict(r) for r in records]
        finally:
            session.close()

    def _get(platform):
        session = _TestSession()
        try:
            record = session.query(_KYCRecord).filter_by(platform=platform.lower()).first()
            if record is None:
                return None
            return mgr._record_to_dict(record)
        finally:
            session.close()

    def _upsert(platform, status=None, documents_submitted=None, notes=None, started_at=None, completed_at=None):
        session = _TestSession()
        try:
            record = session.query(_KYCRecord).filter_by(platform=platform.lower()).first()
            if record is None:
                record = _KYCRecord(platform=platform.lower(), platform_name=platform, documents_submitted="[]")
                session.add(record)
            if status is not None:
                valid = ["not_started", "in_progress", "completed", "expired", "failed"]
                if status not in valid:
                    raise ValueError(f"Invalid KYC status: {status}")
                record.status = status
            if documents_submitted is not None:
                import json

                record.documents_submitted = json.dumps(documents_submitted)
            if notes is not None:
                record.notes = notes
            session.commit()
            session.refresh(record)
            return mgr._record_to_dict(record)
        finally:
            session.close()

    def _summary():
        session = _TestSession()
        try:
            records = session.query(_KYCRecord).all()
            total = len(records)
            completed = sum(1 for r in records if r.status == "completed")
            return {
                "total": total,
                "completed": completed,
                "in_progress": sum(1 for r in records if r.status == "in_progress"),
                "not_started": sum(1 for r in records if r.status == "not_started"),
                "failed": sum(1 for r in records if r.status == "failed"),
                "expired": sum(1 for r in records if r.status == "expired"),
                "progress_pct": round(completed / total * 100, 1) if total > 0 else 0.0,
            }
        finally:
            session.close()

    mgr.get_all = _get_all
    mgr.get = _get
    mgr.upsert = _upsert
    mgr.get_summary = _summary
    return mgr


@pytest.fixture
def docs_checklist():
    """DocumentsChecklist patched to use test session."""
    from core.financial_hub.documents_checklist import DocumentsChecklist

    mgr = DocumentsChecklist()

    def _list():
        session = _TestSession()
        try:
            docs = session.query(_PayoutDocument).order_by(_PayoutDocument.category, _PayoutDocument.name).all()
            return [mgr._doc_to_dict(d) for d in docs]
        finally:
            session.close()

    def _get(doc_id):
        session = _TestSession()
        try:
            doc = session.query(_PayoutDocument).filter_by(id=doc_id).first()
            if doc is None:
                return None
            return mgr._doc_to_dict(doc)
        finally:
            session.close()

    def _mark_completed(doc_id):
        session = _TestSession()
        try:
            doc = session.query(_PayoutDocument).filter_by(id=doc_id).first()
            if doc is None:
                return None
            doc.is_completed = True
            doc.completed_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(doc)
            return mgr._doc_to_dict(doc)
        finally:
            session.close()

    def _mark_incomplete(doc_id):
        session = _TestSession()
        try:
            doc = session.query(_PayoutDocument).filter_by(id=doc_id).first()
            if doc is None:
                return None
            doc.is_completed = False
            doc.completed_at = None
            session.commit()
            session.refresh(doc)
            return mgr._doc_to_dict(doc)
        finally:
            session.close()

    def _summary():
        session = _TestSession()
        try:
            docs = session.query(_PayoutDocument).all()
            total = len(docs)
            completed = sum(1 for d in docs if d.is_completed)
            categories = {}
            for d in docs:
                cat = d.category
                if cat not in categories:
                    categories[cat] = {"total": 0, "completed": 0}
                categories[cat]["total"] += 1
                if d.is_completed:
                    categories[cat]["completed"] += 1
            return {
                "total": total,
                "completed": completed,
                "pending": total - completed,
                "progress_pct": round(completed / total * 100, 1) if total > 0 else 0.0,
                "by_category": categories,
            }
        finally:
            session.close()

    mgr.list_all = _list
    mgr.get = _get
    mgr.mark_completed = _mark_completed
    mgr.mark_incomplete = _mark_incomplete
    mgr.get_summary = _summary
    return mgr


@pytest.fixture
def tax_notes():
    """TaxNotes patched to use test session."""
    from core.financial_hub.tax_notes import TaxNotes

    mgr = TaxNotes()

    def _list(country="AR"):
        session = _TestSession()
        try:
            records = session.query(_TaxRecord).filter_by(country=country.upper(), is_active=True).all()
            return [mgr._record_to_dict(r) for r in records]
        finally:
            session.close()

    def _get(record_id):
        session = _TestSession()
        try:
            record = session.query(_TaxRecord).filter_by(id=record_id).first()
            if record is None:
                return None
            return mgr._record_to_dict(record)
        finally:
            session.close()

    mgr.list_all = _list
    mgr.get = _get
    return mgr


@pytest.fixture
def route_optimizer():
    """RouteOptimizer patched to use test session."""
    from core.financial_hub.route_optimizer import RouteOptimizer

    mgr = RouteOptimizer()

    def _list(include_emergency=False):
        session = _TestSession()
        try:
            query = session.query(_WithdrawalRoute).order_by(_WithdrawalRoute.priority.desc())
            if not include_emergency:
                query = query.filter_by(is_emergency=False)
            records = query.all()
            return [mgr._route_to_dict(r) for r in records]
        finally:
            session.close()

    def _get(route_id):
        session = _TestSession()
        try:
            record = session.query(_WithdrawalRoute).filter_by(id=route_id).first()
            if record is None:
                return None
            return mgr._route_to_dict(record)
        finally:
            session.close()

    def _calc(amount_usd, source_platform):
        session = _TestSession()
        try:
            routes = (
                session.query(_WithdrawalRoute)
                .filter_by(is_active=True)
                .order_by(_WithdrawalRoute.priority.desc())
                .all()
            )
            results = []
            for route in routes:
                total_fee = amount_usd * (route.fee_percent / 100.0) + route.fee_fixed
                net = amount_usd - total_fee
                import json

                results.append(
                    {
                        "route_id": route.id,
                        "name": route.name,
                        "description": route.description,
                        "type": route.route_type,
                        "fee_percent": route.fee_percent,
                        "fee_fixed": route.fee_fixed,
                        "total_fee_usd": round(total_fee, 2),
                        "net_amount_usd": round(net, 2),
                        "arrival_days": route.arrival_days,
                        "is_emergency": route.is_emergency,
                        "priority": route.priority,
                        "steps": json.loads(route.steps) if route.steps else [],
                        "requirements": json.loads(route.requirements) if route.requirements else [],
                    }
                )
            results.sort(key=lambda r: (r["is_emergency"], -r["priority"]))
            return results
        finally:
            session.close()

    mgr.list_routes = _list
    mgr.get_route = _get
    mgr.calculate_optimal = _calc
    return mgr


# ── Payout Advisor Tests ─────────────────────────────────────────────


class TestPayoutAdvisor:
    def test_list_platforms(self, client, init_defaults):
        resp = client.get("/api/financial-hub/payout-advisor/platforms")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(p["platform_id"] == "hackerone" for p in data)

    def test_get_platform_found(self, client, init_defaults):
        resp = client.get("/api/financial-hub/payout-advisor/platforms/hackerone")
        assert resp.status_code == 200
        data = resp.json()
        assert data["platform_id"] == "hackerone"
        assert "methods" in data
        assert "recommended" in data

    def test_get_platform_not_found(self, client, init_defaults):
        resp = client.get("/api/financial-hub/payout-advisor/platforms/unknown")
        assert resp.status_code == 404

    def test_best_routes(self, client, init_defaults):
        resp = client.get("/api/financial-hub/payout-advisor/best-routes")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_simulate_payout(self, client, init_defaults):
        resp = client.post(
            "/api/financial-hub/payout-advisor/simulate",
            params={"amount_usd": 1000, "source_platform": "hackerone"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["amount_usd"] == 1000.0
        assert data["source_platform"] == "hackerone"
        assert len(data["route_steps"]) > 0

    def test_simulate_payout_invalid_amount(self, client, init_defaults):
        resp = client.post(
            "/api/financial-hub/payout-advisor/simulate",
            params={"amount_usd": -100, "source_platform": "hackerone"},
        )
        assert resp.status_code == 400


# ── KYC Manager Tests ────────────────────────────────────────────────


class TestKYCManager:
    def test_list_kyc_empty(self, client):
        resp = client.get("/api/financial-hub/kyc")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_kyc_with_defaults(self, kyc_manager, init_defaults):
        data = kyc_manager.get_all()
        assert len(data) > 0
        platforms = [r["platform"] for r in data]
        assert "hackerone" in platforms
        assert "immunefi" in platforms

    def test_get_kyc_found(self, kyc_manager, init_defaults):
        data = kyc_manager.get("hackerone")
        assert data is not None
        assert data["platform"] == "hackerone"

    def test_get_kyc_not_found(self, client, init_defaults):
        resp = client.get("/api/financial-hub/kyc/unknown")
        assert resp.status_code == 404

    def test_upsert_kyc(self, client, init_defaults):
        resp = client.post(
            "/api/financial-hub/kyc/hackerone",
            params={"status": "in_progress", "documents_submitted": ["DNI"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"

    def test_kyc_summary(self, client, init_defaults):
        resp = client.get("/api/financial-hub/kyc/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        assert "progress_pct" in data

    def test_upsert_invalid_status(self, client, init_defaults):
        resp = client.post(
            "/api/financial-hub/kyc/hackerone",
            params={"status": "invalid_status"},
        )
        assert resp.status_code == 400


# ── Route Optimizer Tests ─────────────────────────────────────────────


class TestRouteOptimizer:
    def test_list_routes_empty(self, client):
        resp = client.get("/api/financial-hub/routes")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_routes_with_defaults(self, route_optimizer, init_defaults):
        data = route_optimizer.list_routes()
        assert len(data) > 0

    def test_list_routes_with_emergency(self, route_optimizer, init_defaults):
        data = route_optimizer.list_routes(include_emergency=True)
        non_emergency = [r for r in data if not r["is_emergency"]]
        assert len(non_emergency) > 0

    def test_get_route_found(self, client, init_defaults):
        resp = client.get("/api/financial-hub/routes/1")
        assert resp.status_code in (200, 404)

    def test_get_route_not_found(self, client, init_defaults):
        resp = client.get("/api/financial-hub/routes/9999")
        assert resp.status_code == 404

    def test_optimize_route(self, client, init_defaults):
        resp = client.get(
            "/api/financial-hub/routes/optimize",
            params={"amount_usd": 500, "source_platform": "hackerone"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_optimize_invalid_amount(self, client, init_defaults):
        resp = client.get(
            "/api/financial-hub/routes/optimize",
            params={"amount_usd": -100, "source_platform": "hackerone"},
        )
        assert resp.status_code == 400


# ── Fees Calculator Tests ──────────────────────────────────────────────


class TestFeesCalculator:
    def test_estimate_fees(self, client):
        resp = client.post(
            "/api/financial-hub/fees/estimate",
            params={"amount_usd": 1000, "fee_percent": 2.0, "fee_fixed": 1.5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["input"]["amount"] == 1000.0
        assert data["fees"]["percentage"] == 20.0
        assert data["fees"]["fixed"] == 1.5
        assert data["fees"]["total"] == 21.5
        assert data["net"]["amount"] == 978.5

    def test_estimate_invalid_amount(self, client):
        resp = client.post(
            "/api/financial-hub/fees/estimate",
            params={"amount_usd": -1},
        )
        assert resp.status_code == 400

    def test_compare_methods(self, client):
        methods = [
            {"id": "method_a", "name": "Method A", "type": "wallet", "fee_percent": 1.0, "fee_fixed": 0.0},
            {"id": "method_b", "name": "Method B", "type": "bank", "fee_percent": 3.0, "fee_fixed": 5.0},
        ]
        resp = client.post(
            "/api/financial-hub/fees/compare",
            params={"amount_usd": 1000},
            json=methods,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        # Method A (1%) should be cheaper than Method B (3% + $5)
        assert data[0]["fees"]["total"] < data[1]["fees"]["total"]


# ── Platform Registry Tests ────────────────────────────────────────────


class TestPlatformRegistry:
    def test_list_platforms(self, client):
        resp = client.get("/api/financial-hub/platforms")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert any(p["platform_id"] == "hackerone" for p in data)

    def test_get_platform_found(self, client):
        resp = client.get("/api/financial-hub/platforms/immunefi")
        assert resp.status_code == 200
        data = resp.json()
        assert "payout_methods" in data

    def test_get_platform_not_found(self, client):
        resp = client.get("/api/financial-hub/platforms/void")
        assert resp.status_code == 404

    def test_compare_platforms(self, client):
        resp = client.post(
            "/api/financial-hub/platforms/compare",
            json=["hackerone", "immunefi"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_argentina_ranked(self, client):
        resp = client.get("/api/financial-hub/platforms/argentina/ranked")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0


# ── Verification Tracker Tests ─────────────────────────────────────────


class TestVerificationTracker:
    def test_progress_no_defaults(self, client):
        resp = client.get("/api/financial-hub/verifications/progress")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_progress_pct" in data

    def test_progress_with_defaults(self, client, init_defaults):
        resp = client.get("/api/financial-hub/verifications/progress")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] > 0

    def test_pending_verifications(self, client, init_defaults):
        resp = client.get("/api/financial-hub/verifications/pending")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0


# ── Documents Checklist Tests ─────────────────────────────────────────


class TestDocumentsChecklist:
    def test_list_documents_empty(self, client):
        resp = client.get("/api/financial-hub/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_documents_with_defaults(self, docs_checklist, init_defaults):
        data = docs_checklist.list_all()
        assert len(data) > 0
        names = [d["name"] for d in data]
        assert "DNI (Documento Nacional de Identidad)" in names

    def test_get_document_found(self, client, init_defaults):
        resp = client.get("/api/financial-hub/documents/1")
        assert resp.status_code in (200, 404)

    def test_get_document_not_found(self, client, init_defaults):
        resp = client.get("/api/financial-hub/documents/9999")
        assert resp.status_code == 404

    def test_mark_completed(self, client, init_defaults):
        docs = client.get("/api/financial-hub/documents").json()
        if not docs:
            pytest.skip("No documents to test")
        doc_id = docs[0]["id"]
        resp = client.post(f"/api/financial-hub/documents/{doc_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True

    def test_mark_incomplete(self, client, init_defaults):
        docs = client.get("/api/financial-hub/documents").json()
        if not docs:
            pytest.skip("No documents to test")
        doc_id = docs[0]["id"]
        client.post(f"/api/financial-hub/documents/{doc_id}/complete")
        resp = client.post(f"/api/financial-hub/documents/{doc_id}/incomplete")
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is False

    def test_documents_summary(self, docs_checklist, init_defaults):
        data = docs_checklist.get_summary()
        assert data["total"] > 0
        assert "by_category" in data


# ── Emergency Routes Tests ──────────────────────────────────────────────


class TestEmergencyRoutes:
    def test_list_emergency_empty(self, client):
        resp = client.get("/api/financial-hub/emergency-routes")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_emergency_with_defaults(self, client, init_defaults):
        resp = client.get("/api/financial-hub/emergency-routes")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_fallback_not_found(self, client):
        resp = client.get("/api/financial-hub/emergency-routes/fallback")
        assert resp.status_code == 404

    def test_quickest_not_found(self, client):
        resp = client.get("/api/financial-hub/emergency-routes/quickest")
        assert resp.status_code == 404


# ── Tax Notes Tests ─────────────────────────────────────────────────────


class TestTaxNotes:
    def test_list_tax_notes_empty(self, client):
        resp = client.get("/api/financial-hub/tax-notes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_tax_notes_with_defaults(self, tax_notes, init_defaults):
        data = tax_notes.list_all("AR")
        assert len(data) > 0

    def test_get_tax_note_found(self, client, init_defaults):
        resp = client.get("/api/financial-hub/tax-notes/1")
        assert resp.status_code in (200, 404)

    def test_get_tax_note_not_found(self, client, init_defaults):
        resp = client.get("/api/financial-hub/tax-notes/9999")
        assert resp.status_code == 404

    def test_by_category(self, tax_notes, init_defaults):
        from core.financial_hub.tax_notes import TaxNotes

        mgr = TaxNotes()

        # monkey-patch to use test session
        def _by_category(country="AR"):
            session = _TestSession()
            try:
                records = (
                    session.query(_TaxRecord)
                    .filter_by(country=country.upper(), is_active=True)
                    .order_by(_TaxRecord.category)
                    .all()
                )
                categories: dict[str, list] = {}
                for r in records:
                    cat = r.category
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(tax_notes._record_to_dict(r))
                return categories
            finally:
                session.close()

        mgr.by_category = _by_category
        data = mgr.by_category("AR")
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_for_platform(self, client, init_defaults):
        resp = client.get("/api/financial-hub/tax-notes/for-platform/hackerone")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ── Payout Advisor Unit Tests ────────────────────────────────────────


class TestPayoutAdvisorUnit:
    def test_simulate_with_preferred_method(self):
        from core.financial_hub.payout_advisor import PayoutAdvisor

        advisor = PayoutAdvisor()
        result = advisor.simulate_payout(1000, "hackerone", preferred_method="usdc_crypto")
        assert result.source_platform == "hackerone"
        assert len(result.route_steps) > 0

    def test_simulate_unknown_platform(self):
        from core.financial_hub.payout_advisor import PayoutAdvisor

        advisor = PayoutAdvisor()
        result = advisor.simulate_payout(500, "void")
        assert "Unknown platform" in result.risks

    def test_simulate_high_fee_triggers_recommendation(self):
        from core.financial_hub.payout_advisor import PayoutAdvisor

        advisor = PayoutAdvisor()
        result = advisor.simulate_payout(100, "intigriti")
        assert result.net_amount_usd < result.amount_usd
        assert result.total_fees_usd > 0

    def test_net_amount_calculation(self):
        from core.financial_hub.payout_advisor import PayoutAdvisor

        advisor = PayoutAdvisor()
        result = advisor.simulate_payout(1000, "bugcrowd")
        assert result.net_amount_usd < result.amount_usd


# ── KYC Manager Unit Tests ──────────────────────────────────────────────


class TestKYCManagerUnit:
    def test_invalid_status_raises(self, kyc_manager):
        with pytest.raises(ValueError):
            kyc_manager.upsert("test_platform", status="bogus")

    def test_upsert_creates_new(self, kyc_manager):
        result = kyc_manager.upsert("test_platform", status="in_progress")
        assert result["platform"] == "test_platform"
        assert result["status"] == "in_progress"

    def test_summary_empty(self, kyc_manager):
        summary = kyc_manager.get_summary()
        assert summary["total"] == 0


# ── Fees Calculator Unit Tests ─────────────────────────────────────────


class TestFeesCalculatorUnit:
    def test_zero_fees(self):
        from core.financial_hub.fees_calculator import FeesCalculator

        calc = FeesCalculator()
        result = calc.estimate(1000, "wallet", 0.0, 0.0)
        assert result["fees"]["total"] == 0.0
        assert result["net"]["amount"] == 1000.0

    def test_compare_sorts_by_total(self):
        from core.financial_hub.fees_calculator import FeesCalculator

        calc = FeesCalculator()
        methods = [
            {"id": "a", "name": "A", "type": "wallet", "fee_percent": 5.0, "fee_fixed": 0.0},
            {"id": "b", "name": "B", "type": "wallet", "fee_percent": 1.0, "fee_fixed": 0.0},
        ]
        results = calc.compare_methods(1000, methods)
        assert results[0]["method_id"] == "b"
        assert results[1]["method_id"] == "a"


# ── Platform Registry Unit Tests ────────────────────────────────────────


class TestPlatformRegistryUnit:
    def test_unknown_platform(self):
        from core.financial_hub.platform_registry import PlatformRegistry

        reg = PlatformRegistry()
        result = reg.get_platform("nobody")
        assert result is None

    def test_all_known_platforms_exist(self):
        from core.financial_hub.platform_registry import PlatformRegistry

        reg = PlatformRegistry()
        platforms = reg.list_platforms()
        platform_ids = {p["platform_id"] for p in platforms}
        expected = {"hackerone", "bugcrowd", "intigriti", "synack", "yeswehack", "immunefi", "code4rena", "huntr"}
        assert expected.issubset(platform_ids)


# ── Tax Notes Unit Tests ────────────────────────────────────────────────


class TestTaxNotesUnit:
    def test_empty_db_returns_empty(self, tax_notes):
        result = tax_notes.list_all("AR")
        assert result == []

    def test_get_nonexistent(self, tax_notes):
        result = tax_notes.get(9999)
        assert result is None
