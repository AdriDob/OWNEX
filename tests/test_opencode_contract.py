"""OpenCode harness contract guard.

Hallazgo 2026-09-30 (audit de subagents): los 5 agentes del proyecto vivían en
`.opencode/agents/*.txt` — sin frontmatter YAML, sin `description`, sin
`mode: subagent` y con extensión equivocada. OpenCode (docs/agents) sólo carga
markdown con frontmatter donde `description` es **required**. Consecuencia
medida: 0 subagents propios cargados (sólo el `explore` built-in), y los
commands `/plan` y `/security` con `agent: planner` / `agent: security-reviewer`
en su frontmatter quedaban como referencias colgantes.

Este guard pinea el contrato para que la clase de bug no vuelva. Los tests son
puros: leen archivos, no tocan DB ni red.

Regla de este archivo (regla permanente del proyecto): un test que no puede
fallar es peor que no tener test. Por eso cada test afirma el ROSTER canónico
antes de verificar atributos — sin eso, "todo .md tiene frontmatter" sería
verdad vacía con cero archivos.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / ".opencode" / "agents"
COMMANDS_DIR = ROOT / ".opencode" / "commands"

# Roster canónico de subagents del proyecto. Fuente: la tabla de agentes en
# .opencode/rules/ECC-INTEGRATION.md (líneas 52-56). Si un agente nuevo entra,
# se agrega acá explícitamente — no se permite que aparezca por sorpresa.
EXPECTED_SUBAGENTS = frozenset(
    {
        "planner",
        "code-reviewer",
        "python-reviewer",
        "rust-reviewer",
        "security-reviewer",
    }
)

# Todo agente cuyo nombre matchea esto debe ser read-only. Los prompts
# originales decían "never write or edit", pero el config global tiene
# edit: allow — disciplina de prompt NO es enforcement. Estos tests lo suenan.
REVIEWER_GLOB = re.compile(r"review")

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<yaml>.*?)\n---\s*\n", re.DOTALL)


def _parse(path: Path) -> tuple[dict, str] | None:
    """Devuelve (frontmatter_dict, body) o None si no hay frontmatter."""
    match = _FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    if not match:
        return None
    parsed = yaml.safe_load(match.group("yaml"))
    if not isinstance(parsed, dict):
        return None
    return parsed, path.read_text(encoding="utf-8")[match.end() :]


def _agent_files() -> list[Path]:
    return sorted(AGENTS_DIR.glob("*.md")) if AGENTS_DIR.is_dir() else []


def _reviewers() -> list[Path]:
    """Revisores presentes. Afirma el mínimo para no ser verdad vacía."""
    reviewers = [p for p in _agent_files() if REVIEWER_GLOB.search(p.stem)]
    assert len(reviewers) >= 4, f"se esperaban ≥4 revisores en {AGENTS_DIR.relative_to(ROOT)}, hay {len(reviewers)}"
    return reviewers


def test_agent_roster_is_complete() -> None:
    """El roster canónico existe como .md. Evita que el resto sea verdad vacía."""
    present = {p.stem for p in _agent_files()}
    missing = EXPECTED_SUBAGENTS - present
    assert not missing, (
        f"subagents faltantes como .md en {AGENTS_DIR.relative_to(ROOT)}: {sorted(missing)} "
        "(OpenCode no carga .txt — ver docs/agents)"
    )


def test_every_agent_is_markdown_with_required_frontmatter() -> None:
    """Cada agente: frontmatter parseable + `description` no vacía (required)."""
    files = _agent_files()
    assert files, "no se encontró ningún agente .md — el roster está vacío"
    for path in files:
        parsed = _parse(path)
        assert parsed is not None, f"{path.name} sin frontmatter YAML (---\\n...\\n---)"
        frontmatter, body = parsed
        description = str(frontmatter.get("description") or "").strip()
        assert description, f"{path.name} sin `description` (campo required en OpenCode)"
        assert body.strip(), f"{path.name} tiene frontmatter pero el prompt está vacío"


def test_no_orphan_non_markdown_agents() -> None:
    """Cero archivos no-markdown en agents/ — esos NUNCA se cargan."""
    if not AGENTS_DIR.is_dir():
        return
    strays = [p.name for p in AGENTS_DIR.iterdir() if p.is_file() and p.suffix != ".md"]
    assert not strays, (
        f"archivos no-markdown en {AGENTS_DIR.relative_to(ROOT)}: {strays} — OpenCode sólo carga .md con frontmatter"
    )


def test_every_command_agent_reference_resolves() -> None:
    """Cada `agent:` en un command resuelve a un subagent real (no colgante)."""
    if not COMMANDS_DIR.is_dir():
        return
    available = {p.stem for p in _agent_files()}
    for command in sorted(COMMANDS_DIR.glob("*.md")):
        parsed = _parse(command)
        if parsed is None:
            continue
        frontmatter, _ = parsed
        referenced = frontmatter.get("agent")
        if not referenced:
            continue
        assert referenced in available, (
            f"{command.name} referencia `agent: {referenced}` que no existe "
            f"como {AGENTS_DIR.relative_to(ROOT)}/{referenced}.md — referencia colgante"
        )


def test_reviewers_are_read_only() -> None:
    """Los revisores declaran `permission.edit: deny` en el frontmatter.

    El config global declara `edit: allow`; un revisor sin deny explícito
    PODRÍA escribir. El prompt dice "never edit" — esto lo vuelve enforcement.
    """
    for path in _reviewers():
        parsed = _parse(path)
        assert parsed is not None, f"{path.name} sin frontmatter"
        frontmatter, _ = parsed
        permission = frontmatter.get("permission") or {}
        assert isinstance(permission, dict), f"{path.name}: `permission` debe ser un mapa"
        assert str(permission.get("edit", "")).lower() == "deny", (
            f"{path.name} es un revisor y debe declarar `permission.edit: deny` (tiene: {permission.get('edit')!r})"
        )
        assert str(permission.get("write", "deny")).lower() == "deny", (
            f"{path.name}: un revisor no debe tener `write` permitido"
        )


def test_reviewers_declare_scoped_bash() -> None:
    """Los revisores corren ruff/pytest/git, pero con bash en `ask` por default.

    `bash: allow` en un revisor = puede ejecutar cualquier cosa. La política
    correcta es `"*": "ask"` primero (última regla gana) + allow explícitos.

    Se exige poder leer diffs y código, y un allow-list no vacío, sin fijar
    qué toolchain usa cada uno (python vs rust vs security).
    """
    for path in _reviewers():
        parsed = _parse(path)
        assert parsed is not None, f"{path.name} sin frontmatter"
        frontmatter, _ = parsed
        permission = frontmatter.get("permission") or {}
        bash = permission.get("bash")
        assert isinstance(bash, dict), f"{path.name}: `permission.bash` debe ser un mapa de globs, no {bash!r}"
        assert str(bash.get("*", "")).lower() == "ask", (
            f"{path.name}: falta el catch-all `bash['*']: ask` — sin él el revisor puede ejecutar cualquier comando"
        )
        for needed in ("git diff*", "rg*"):
            assert needed in bash, f"{path.name}: falta el allow de `{needed}`"
        explicit = [k for k in bash if k != "*"]
        assert len(explicit) >= 4, (
            f"{path.name}: sólo {len(explicit)} allow(s) explícito(s) en bash — "
            "una lista tan corta indica que el revisor no puede trabajar"
        )


def test_graft_mcp_is_wired_in_opencode_config() -> None:
    """El MCP de graft debe estar en `opencode.json["mcp"]`.

    Hallazgo 2026-09-30: el repo tenía `.mcp.json` en la raíz, que es el
    formato de **Claude Code**. OpenCode lee MCP exclusivamente de
    `opencode.json["mcp"]` (docs/mcp-servers), así que el servidor de graft
    nunca quedó alcanzable: 0 herramientas graft en la sesión, pese a que el
    skill promete `graft_find_code`, `graft_trace_calls`, etc. y el índice
    `graft/` (2460 tarjetas + grafo de 30 MB) estaba inaprovechado.

    `.mcp.json` NO se borró: Claude Code (y Hermes) sí lo leen, y el proyecto
    usa ambos.
    """
    import json

    config = json.loads((ROOT / "opencode.json").read_text(encoding="utf-8"))
    mcp = config.get("mcp")
    assert isinstance(mcp, dict) and mcp, "opencode.json no declara bloque `mcp`"
    graft = mcp.get("graft")
    assert isinstance(graft, dict), "falta la entrada `mcp.graft`"
    assert graft.get("type") == "local", f"mcp.graft.type debe ser 'local', es {graft.get('type')!r}"
    assert graft.get("enabled") is not False, "mcp.graft está deshabilitado"
    cmd = graft.get("command")
    assert isinstance(cmd, list) and "graft" in " ".join(cmd), (
        f"mcp.graft.command debe invocar el binario graft, es {cmd!r}"
    )


def test_instructions_block_within_budget() -> None:
    """El bloque `instructions` de opencode.json no debe crecer sin techo.

    Hallazgo 2026-09-30: `instructions` declaraba 17 ficheros = **995.177 B
    (~250k tokens) de system prompt FIJO en cada sesión**, con
    `compaction.auto: false`. `.ai/CURRENT_STATE.md` (452 KB) y
    `.ai/DECISIONS.md` (376 KB) eran narratives sesión-por-sesión: 207k tokens
    de bitácora cargados como si fueran reglas. Con un modelo free chico eso
    es la definición operativa de "quilombo".

    Presupuesto: 64 KB (~16k tokens). Los documentos grandes van como skill o
    como archivo bajo demanda desde la tabla de `.ai/` en AGENTS.md; el bloque
    fijo es sólo lo que un agente necesita SIEMPRE (constitución, reglas,
    no-tocar, estándares, anti-patrones).

    Este test es el guard de feature-creep del §54 del megaprompt: si alguien
    agrega un documento al bloque, el costo de contexto queda visible.
    """
    import json

    budget = 64 * 1024
    config = json.loads((ROOT / "opencode.json").read_text(encoding="utf-8"))
    instructions = config.get("instructions") or []
    assert instructions, "el bloque instructions está vacío — ¿se borró por error?"

    missing: list[str] = []
    total = 0
    offenders: list[tuple[str, int]] = []
    for rel in instructions:
        path = ROOT / rel
        if not path.exists():
            missing.append(rel)
            continue
        size = path.stat().st_size
        total += size
        if size > budget // 4:
            offenders.append((rel, size))

    assert not missing, f"instructions referencia ficheros inexistentes: {missing}"
    assert total <= budget, (
        f"bloque instructions = {total} B (~{total // 4} tokens), presupuesto {budget} B. "
        f"mayores: {sorted(offenders, key=lambda p: -p[1])}"
    )


def test_instructions_does_not_dupe_autoloaded_rules_files() -> None:
    """AGENTS.md se descubre SOLO como rule file — no hace falta en instructions.

    docs/rules: OpenCode lee `AGENTS.md` (local) y luego "All instruction files
    are combined with your AGENTS.md files". Listarlo además en `instructions`
    lo declara dos veces por el mismo mecanismo.
    """
    import json

    config = json.loads((ROOT / "opencode.json").read_text(encoding="utf-8"))
    for rel in config.get("instructions") or []:
        assert Path(rel).name != "AGENTS.md", (
            f"AGENTS.md está en instructions ({rel}) pero ya se auto-carga como rule file"
        )


def test_agents_md_exists_and_routes_the_on_demand_docs() -> None:
    """AGENTS.md se.auto-carga como rule file — debe existir y enrutar el resto.

    Se quitó de `instructions` porque docs/rules dice que OpenCode lo descubre
    por sí solo ("All instruction files are combined with your AGENTS.md files"),
    pero eso hace que su contenido sea invisible para un test. Este test lo
    vuelve observable: si alguien lo borra o deja de enrutar los documentos
    bajo demanda, la Regla de Oro del charter se queda sin camino de entrada.
    """
    agents = ROOT / "AGENTS.md"
    assert agents.is_file(), "AGENTS.md no existe — OpenCode perdería las instrucciones del proyecto"
    text = agents.read_text(encoding="utf-8")
    assert len(text) > 8_000, f"AGENTS.md sospechosamente corto ({len(text)} B)"

    # Todo .ai/ que NO está en instructions debe estar enrutado desde AGENTS.md
    import json

    config = json.loads((ROOT / "opencode.json").read_text(encoding="utf-8"))
    fixed = {Path(p).name for p in config.get("instructions") or []}
    for name in ("CURRENT_STATE.md", "DECISIONS.md", "KNOWN_DEBT.md", "TASK_QUEUE.md"):
        if name in fixed:
            continue
        assert name in text, f"{name} no está en instructions ni referenciado en AGENTS.md — inalcanzable"
