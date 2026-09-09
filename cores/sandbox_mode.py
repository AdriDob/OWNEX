"""Sandbox Mode - bounty ficticio para operar día 1 sin cuenta real ni API keys."""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SANDBOX_DIR = Path.home() / ".rastro" / "sandbox"
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SandboxBounty:
    id: str
    title: str
    description: str
    repo: str
    platform: str
    reward_usd: int
    difficulty: str
    tags: list[str]
    files_to_edit: list[str]
    solution_template: str
    test_instructions: str
    created_at: str
    status: str = "available"
    submitted_at: str | None = None
    validated_at: str | None = None
    payout_tx: str | None = None


SANDBOX_BOUNTIES: list[SandboxBounty] = [
    SandboxBounty(
        id="sbx-hello-world",
        title="🎯 Hello World - Tu primera bounty",
        description="Corrige el archivo `main.py` para que imprima 'Hello, OWNEX!' y pasa el test.",
        repo="ownex/sandbox-hello",
        platform="sandbox",
        reward_usd=5,
        difficulty="trivial",
        tags=["python", "good-first-issue", "sandbox"],
        files_to_edit=["main.py"],
        solution_template='print("Hello, OWNEX!")',
        test_instructions="Ejecuta `python main.py` y verifica que salga 'Hello, OWNEX!'",
        created_at=datetime.now(UTC).isoformat(),
    ),
    SandboxBounty(
        id="sbx-fix-bug",
        title="🐛 Fix: Suma incorrecta en calculator.py",
        description="La función `add(a, b)` retorna `a - b` en lugar de `a + b`. Corrige y pasa los tests.",
        repo="ownex/sandbox-calc",
        platform="sandbox",
        reward_usd=10,
        difficulty="easy",
        tags=["python", "bug", "sandbox"],
        files_to_edit=["calculator.py", "test_calculator.py"],
        solution_template="def add(a, b):\n    return a + b",
        test_instructions="Ejecuta `python test_calculator.py` - todos los tests deben pasar.",
        created_at=datetime.now(UTC).isoformat(),
    ),
    SandboxBounty(
        id="sbx-api-endpoint",
        title="🌐 Añade endpoint /health a FastAPI app",
        description='Crea un endpoint GET `/health` que retorne `{"status": "ok", "service": "sandbox"}`.',
        repo="ownex/sandbox-api",
        platform="sandbox",
        reward_usd=15,
        difficulty="easy",
        tags=["python", "fastapi", "backend", "sandbox"],
        files_to_edit=["main.py"],
        solution_template='@app.get("/health")\ndef health():\n    return {"status": "ok", "service": "sandbox"}',
        test_instructions="Ejecuta `uvicorn main:app --reload` y haz curl a http://localhost:8000/health",
        created_at=datetime.now(UTC).isoformat(),
    ),
    SandboxBounty(
        id="sbx-frontend-fix",
        title="⚛️ Fix: Botón no dispara evento en Vue",
        description="El botón 'Guardar' no llama a `save()`. Añade `@click=\"save\"` al template.",
        repo="ownex/sandbox-vue",
        platform="sandbox",
        reward_usd=10,
        difficulty="easy",
        tags=["vue", "frontend", "sandbox"],
        files_to_edit=["App.vue"],
        solution_template='<button @click="save">Guardar</button>',
        test_instructions="Abre en browser, click 'Guardar', verifica console.log('saved')",
        created_at=datetime.now(UTC).isoformat(),
    ),
    SandboxBounty(
        id="sbx-write-readme",
        title="📝 Escribe README.md para proyecto sandbox",
        description="Crea un README.md con: título, descripción, cómo instalar, cómo testear, licencia MIT.",
        repo="ownex/sandbox-docs",
        platform="sandbox",
        reward_usd=8,
        difficulty="trivial",
        tags=["docs", "markdown", "sandbox"],
        files_to_edit=["README.md"],
        solution_template="# Sandbox Project\n\nDescripción...\n\n## Instalar\n```bash\npip install -r requirements.txt\n```\n\n## Test\n```bash\npytest\n```\n\nLicencia: MIT",
        test_instructions="Verifica que README.md exista y tenga secciones: título, instalar, test, licencia.",
        created_at=datetime.now(UTC).isoformat(),
    ),
]


def get_sandbox_bounties() -> list[dict[str, Any]]:
    """Returns all sandbox bounties as dicts."""
    return [asdict(b) for b in SANDBOX_BOUNTIES]


def get_sandbox_bounty(bounty_id: str) -> dict[str, Any] | None:
    """Get single sandbox bounty by ID."""
    for b in SANDBOX_BOUNTIES:
        if b.id == bounty_id:
            return asdict(b)
    return None


def submit_sandbox_bounty(bounty_id: str, solution: str, files: dict[str, str]) -> dict[str, Any]:
    """Validate sandbox submission (auto-approval for learning)."""
    bounty = get_sandbox_bounty(bounty_id)
    if not bounty:
        return {"success": False, "error": "Bounty not found"}

    # Simple validation: check if key parts of solution_template are in solution
    template = bounty["solution_template"]
    key_parts = [p.strip() for p in template.split("\n") if p.strip() and not p.strip().startswith("#")]
    matches = sum(1 for part in key_parts if part in solution)

    # Auto-approve if >50% match (learning mode)
    approved = matches >= max(1, len(key_parts) // 2)

    # Save submission record
    record = {
        "bounty_id": bounty_id,
        "solution": solution,
        "files": files,
        "matches": matches,
        "total_parts": len(key_parts),
        "approved": approved,
        "submitted_at": datetime.now(UTC).isoformat(),
        "payout_tx": f"sbx_{uuid.uuid4().hex[:12]}" if approved else None,
    }
    (SANDBOX_DIR / f"submission_{bounty_id}.json").write_text(json.dumps(record, indent=2))

    # Update bounty status
    for b in SANDBOX_BOUNTIES:
        if b.id == bounty_id:
            b.status = "submitted"
            b.submitted_at = record["submitted_at"]
            if approved:
                b.status = "validated"
                b.validated_at = record["submitted_at"]
                b.payout_tx = record["payout_tx"]
            break

    return {
        "success": True,
        "approved": approved,
        "matches": matches,
        "total_parts": len(key_parts),
        "payout_tx": record["payout_tx"],
        "message": "🎉 ¡Validado! Has completado tu primera bounty sandbox."
        if approved
        else "⚠️ Intenta de nuevo. Revisa la solución esperada vs tu código.",
    }


def get_sandbox_progress() -> dict[str, Any]:
    """Get user's sandbox progress stats."""
    submissions = list(SANDBOX_DIR.glob("submission_*.json"))
    completed = 0
    total_reward = 0
    for s in submissions:
        try:
            data = json.loads(s.read_text())
            if data.get("approved"):
                completed += 1
                b = get_sandbox_bounty(data["bounty_id"])
                if b:
                    total_reward += b["reward_usd"]
        except Exception:
            pass

    return {
        "total_bounties": len(SANDBOX_BOUNTIES),
        "completed": completed,
        "total_reward_usd": total_reward,
        "completion_rate": round(completed / len(SANDBOX_BOUNTIES) * 100, 1),
        "submissions": len(submissions),
    }


def reset_sandbox() -> dict[str, Any]:
    """Reset all sandbox progress (for fresh start)."""
    for f in SANDBOX_DIR.glob("submission_*.json"):
        f.unlink()
    for b in SANDBOX_BOUNTIES:
        b.status = "available"
        b.submitted_at = None
        b.validated_at = None
        b.payout_tx = None
    return {"success": True, "message": "Sandbox reiniciado. ¡A empezar de nuevo!"}
