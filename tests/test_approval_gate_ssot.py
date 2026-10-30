"""Guard de Single-Source-of-Truth en el Human Gate.

Hallazgo 2026-10-04 (`KNOWN_DEBT #49`): `cores/approval/gate.py` y
`cores/approval/gates.py` definen **ambos** `class ApprovalGate` **y** ambos
`get_approval_gate()`. Un import equivocado resuelve en silencio a la política
equivocada, y la diferencia es de seguridad: una autoriza automáticamente
donde la otra exige aprobación.

Este guard no arregla el conflicto — eso es decisión de producto. Fija lo que
SÍ es cierto hoy, medido, para que el conflicto no crezca en silencio:

1. `gates.py` es el canónico de producción (lo usa `api/routers/approvals.py`).
2. Los dos `ActionType` NO son el mismo enum (comparten 1 valor de 10/8).
3. La API re-valida los modos a mano, sin consultar `AutonomyPolicy`.

Cuando se resuelva el merge, este test se actualiza con la decisión — igual que
se actualizó `test_work_policy` cuando el enum pasó de 38 a 40.
"""

from __future__ import annotations

from pathlib import Path

import cores.approval.gate as gate_mod
import cores.approval.gates as gates_mod

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = gates_mod


def test_canonical_gate_is_the_one_the_api_uses() -> None:
    """`gates.py` es el canónico: debe ser el que `api/routers/approvals.py` importa."""
    approvals = (REPO_ROOT / "api" / "routers" / "approvals.py").read_text(encoding="utf-8")
    assert "cores.approval.gates" in approvals, "approvals.py ya no usa cores.approval.gates"
    assert "cores.approval.gate import" not in approvals and "cores.approval.gate\b" not in approvals.replace(
        "cores.approval.gates", ""
    ), "approvals.py empezó a importar el gate huérfano (ver KNOWN_DEBT #49)"


def test_both_gates_still_export_the_same_public_names() -> None:
    """Documenta la condición actual: dos módulos, mismos nombres públicos.

    Si este test falla, alguien renombró o borró uno de los dos — que es
    exactamente el primer paso del merge. Actualizar la decisión, no el test.
    """
    for name in ("ApprovalGate", "get_approval_gate"):
        assert hasattr(CANONICAL, name), f"gates.py perdió {name}"
        assert hasattr(gate_mod, name), (
            f"gate.py ya no exporta {name} — el huérfano fue resuelto. "
            "Actualizar KNOWN_DEBT #49 y este guard con la decisión de producto."
        )


def test_action_type_enums_are_not_the_same() -> None:
    """Los dos `ActionType` son enums DISTINTOS, no alias del mismo.

    Que fueran idénticos sería señal de que alguien unificó a medias.
    """
    mine = {e.value for e in gate_mod.ActionType}
    theirs = {e.value for e in gates_mod.ActionType}
    assert mine != theirs, "los ActionType se fusionaron — reverificar KNOWN_DEBT #49"
    assert mine & theirs == {"submit_report"}, (
        f"el overlap cambió: {sorted(mine & theirs)} — revisar si ya son la misma política"
    )


def test_mode_validation_is_not_the_enum_source_of_truth() -> None:
    """`settings_runtime.py` re-valida los modos a mano, no contra `AutonomyPolicy`.

    Esto es deuda conocida, no un bug de seguridad: el router acepta exactamente
    los 3 modos del enum. Pero si alguien añade un modo al enum, la API lo
    rechazará y nadie se enterará.
    """
    router = (REPO_ROOT / "api" / "routers" / "settings_runtime.py").read_text(encoding="utf-8")
    assert 'valid_modes = ["lite", "full", "capital"]' in router, (
        "settings_runtime.py cambió su validación manual — si ahora usa AutonomyPolicy, "
        "esta debt está resuelta (ver KNOWN_DEBT #49)."
    )
    # y el enum realmente tiene esos 3
    assert {e.value for e in gate_mod.AutonomyPolicy} == {"lite", "full", "capital"}
