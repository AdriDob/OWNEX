from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from core.offensive.web3.engine import Web3OffensiveEngine
from core.offensive.web3.models import SmartContractInfo

router = APIRouter(prefix="/api/offensive/web3", tags=["offensive_web3"])

_engine: Web3OffensiveEngine | None = None


class Web3AnalyzeRequest(BaseModel):
    address: str
    chain: str = "ethereum"
    name: str | None = None
    abi: list | None = None
    functions: list[str] | None = None


def _get_engine() -> Web3OffensiveEngine:
    global _engine
    if _engine is None:
        _engine = Web3OffensiveEngine()
    return _engine


@router.post("/analyze")
def analyze_contract(req: Web3AnalyzeRequest):
    engine = _get_engine()
    contract = SmartContractInfo(
        address=req.address,
        chain=req.chain,
        name=req.name,
        abi=req.abi,
        functions=req.functions,
    )
    hypotheses = engine.analyze_contract(contract)
    return {
        "contract": req.address,
        "chain": req.chain,
        "total_hypotheses": len(hypotheses),
        "hypotheses": [
            {
                "vulnerability_type": h.vulnerability_type,
                "confidence": round(h.confidence, 2),
                "severity": h.severity,
                "summary": h.summary,
                "description": h.description,
                "signals": h.signals,
                "test_instructions": h.test_instructions,
                "remediation": h.remediation,
            }
            for h in hypotheses
        ],
    }


@router.post("/analyze/batch")
def analyze_batch(contracts: list[Web3AnalyzeRequest]):
    engine = _get_engine()
    results = {}
    for req in contracts:
        contract = SmartContractInfo(
            address=req.address,
            chain=req.chain,
            name=req.name,
            abi=req.abi,
            functions=req.functions,
        )
        hypotheses = engine.analyze_contract(contract)
        results[req.address] = [
            {
                "vulnerability_type": h.vulnerability_type,
                "confidence": round(h.confidence, 2),
                "severity": h.severity,
                "summary": h.summary,
                "signals": h.signals,
            }
            for h in hypotheses
        ]
    return {"total": len(contracts), "results": results}


@router.get("/reasoners")
def list_reasoners():
    engine = _get_engine()
    return {"reasoners": engine.list_reasoners(), "stats": engine.get_stats()}
