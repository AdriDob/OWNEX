"""Guard: sin claves duplicadas en los data-objects de `ownexData.ts`.

Por qué existe (2026-10-05). `fetchMilestoneTracker` declaraba
`total_earned_usd` **dos veces** en el literal de return y **dos veces** en la
interface `MilestoneTrackerResponse`. En JS la segunda clave **pisa** la
primera en silencio: no es error de runtime, es código muerto. Y el warning
`[plugin vite:esbuild] Duplicate key` **enmascara** cualquier otro error real
del mismo archivo.

El daño real no es el bug: es el ruido. *Un warning que nadie va a arreglar no
es un warning: es ruido que tapa señales.*

Por qué este guard es más difícil de lo que parece: un `return { ... }`
contiene objetos anidados (`{ close_engine: { engine: ... } }`) donde el mismo
nombre de clave aparece legítimamente a distinta profundidad. La primera
versión del guard contou todos y dio 23 falsos positivos. Sólo cuentan las
claves **al mismo nivel de llaves** dentro del **mismo** literal.
"""

from __future__ import annotations

import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
OWNEX_DATA = FRONTEND / "src" / "services" / "ownexData.ts"

_KEY = re.compile(r"^([A-Za-z_$][\w$]*)\s*[?]?\s*:")
_BLOCK_START = re.compile(r"^(?:export\s+)?(?:interface|type)\s+\w+\s*(?:=\s*)?\{$")
_RETURN_START = re.compile(r"^\s*return\s*\{")


def _scan_pairs(text: str, start_re: re.Pattern[str]) -> list[tuple[int, list[tuple[str, int]]]]:
    """Devuelve (offset, [(clave, linea_relativa)]) por bloque de primer nivel.

    Solo cuenta claves del bloque EXTERNO: al abrir `{` o `(` se incrementa
    la profundidad y las claves internas se ignoran.
    """
    lines = text.splitlines()
    results: list[tuple[int, list[tuple[str, int]]]] = []
    i = 0
    while i < len(lines):
        if not start_re.match(lines[i]):
            i += 1
            continue

        offset = i
        pairs: list[tuple[str, int]] = []
        # profundidad de LLAVES solamente: una interface termina en su `}`.
        # Contar tambien paréntesis hacía que "} | null" no cerrara el bloque y
        # se comiera la interface siguiente (falsos positivos).
        depth = 1
        i += 1
        while i < len(lines) and depth > 0:
            line = lines[i]
            stripped = line.strip()
            if not stripped.startswith(("//", "/*", "*")):
                m = _KEY.match(stripped)
                # Una linea `foo: Record<string, {` abre DOS llaves (tipo
                # objeto + Record). Countar el balance ANTES de registrar la
                # clave hace que esa clave cuente como "interna". Por eso el
                # balance va primero y la clave se registra con el depth
                # resultante.
                delta = line.count("{") - line.count("}")
                if m:
                    next_depth = depth + delta
                    if next_depth == 1:
                        pairs.append((m.group(1), i - offset))
                depth += delta
            i += 1
        results.append((offset, pairs))
    return results


def _duplicates(pairs: list[tuple[str, int]]) -> list[tuple[str, int, int]]:
    seen: dict[str, int] = {}
    dups: list[tuple[str, int, int]] = []
    for name, rel in pairs:
        if name in seen:
            dups.append((name, seen[name], rel))
        else:
            seen[name] = rel
    return dups


def test_no_duplicate_keys_in_object_literals() -> None:
    """Object literals: la segunda clave pisa la primera EN SILENCIO."""
    text = OWNEX_DATA.read_text(encoding="utf-8")
    offenders: list[str] = []

    for offset, pairs in _scan_pairs(text, _RETURN_START):
        base = offset + 1
        for name, first, _second in _duplicates(pairs):
            offenders.append(f"línea ~{base + first}: '{name}' repetido")

    assert not offenders, "claves duplicadas en object literals (la 2da pisa la 1ra en silencio):\n  " + "\n  ".join(
        offenders
    )


def test_no_duplicate_members_in_interfaces() -> None:
    """Interfaces TS: un miembro repetido es error de tipos, no cosmetics."""
    text = OWNEX_DATA.read_text(encoding="utf-8")
    offenders: list[str] = []

    for offset, pairs in _scan_pairs(text, _BLOCK_START):
        base = offset + 1
        for name, first, _second in _duplicates(pairs):
            offenders.append(f"línea ~{base + first}: '{name}' repetido en la interface")

    assert not offenders, "miembros duplicados en interfaces:\n  " + "\n  ".join(offenders)


def test_el_incidente_concreto_no_vuelve() -> None:
    """Guard del incidente: `total_earned_usd` como VALOR sólo puede estar 1 vez."""
    text = OWNEX_DATA.read_text(encoding="utf-8")
    as_value = [ln for ln in text.splitlines() if ln.strip().startswith("total_earned_usd: data.")]
    assert len(as_value) == 1, f"total_earned_usd como valor debe aparecer 1 vez, no {len(as_value)}: {as_value}"
