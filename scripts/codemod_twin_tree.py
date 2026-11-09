#!/usr/bin/env python3
"""Twin-tree consolidation codemod — Phase 1: identical-file absorption.

Rewrites ``core.<mod>`` → ``cores.<mod>`` imports ONLY for modules whose
``core/`` and ``cores/`` copies are byte-identical. For those modules the
rewrite is behavior-neutral: after ``core/<path>`` is deleted, every
import must resolve to ``cores/<path>`` anyway.

Divergent files (115) and core-only files (287) are NOT touched — they
require per-file adjudication (see docs/architecture/TWIN_TREE_AUDIT.md).

Usage:
    python scripts/codemod_twin_tree.py --dry-run     # report only
    python scripts/codemod_twin_tree.py --apply       # rewrite files
    python scripts/codemod_twin_tree.py --delete-core # also delete absorbed core/ copies

Run inside a dedicated worktree on branch agent/twin-tree-consolidation.
Never run --apply in the shared main worktree.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Directories never scanned for imports or rewritten.
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".quarantine",
    "work",
    "graft",
    ".ai",
    "docs",
    "frontend",
    "desktop",
    "mobile",
    ".agents",
    "cognee",
    ".playwright-browsers",
}

# String-literal dynamic imports: importlib.import_module("core.x.y") etc.
DYNAMIC_RE = re.compile(r"""(["'])core\.([\w.]+)\1""")


def _iter_py_files(root: Path):
    for p in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def identical_modules() -> set[str]:
    """Dotted module paths present in both trees with identical bytes."""
    core, cores = REPO / "core", REPO / "cores"
    identical: set[str] = set()
    for cp in core.rglob("*.py"):
        rel = cp.relative_to(core)
        sp = cores / rel
        if not sp.exists():
            continue
        if cp.read_bytes() == sp.read_bytes():
            mod = ".".join(rel.with_suffix("").parts)
            if mod == "__init__":
                mod = ".".join(rel.parent.parts)
            if mod:
                identical.add(mod)
    return identical


# Module-level mutable state makes a module unsafe to split across trees:
# `import core.db.manager` and `import cores.db.manager` would yield TWO
# singleton instances (registries, sessions, buses diverge silently).
STATEFUL_RE = re.compile(
    r"^\s*global\s|^_\w+\s*=\s*(?:None|[A-Z]\w+\()|"
    r"^_\w*(?:manager|instance|singleton|registry|bus|client|pool|cache)\w*\s*=",
    re.MULTILINE,
)


def stateful_modules(mods: set[str]) -> set[str]:
    """Identical modules holding module-level mutable state — exclude them."""
    out: set[str] = set()
    for mod in mods:
        rel = Path(*mod.split("."))
        for cand in (REPO / "core" / rel.with_suffix(".py"), REPO / "core" / rel / "__init__.py"):
            if cand.exists():
                try:
                    if STATEFUL_RE.search(cand.read_text(encoding="utf-8", errors="replace")):
                        out.add(mod)
                except OSError:
                    pass
                break
    return out


def importable_cores_modules() -> set[str]:
    """Dotted module names under cores/ that Python can actually resolve.

    A directory without ``__init__.py`` is only a namespace package, and a
    sibling ``<name>.py`` module shadows it entirely (regular module beats
    namespace package). Modules under such shadowed dirs are NOT importable
    as ``cores.<path>`` and must never be rewrite/delete targets.
    """
    cores = REPO / "cores"
    mods: set[str] = set()
    for cp in cores.rglob("*.py"):
        rel = cp.relative_to(cores)
        mod = ".".join(rel.with_suffix("").parts)
        if mod == "__init__":
            continue
        pkg = mod[: -len(".__init__")] if mod.endswith(".__init__") else mod
        parts = pkg.split(".")
        ok = True
        for i in range(1, len(parts)):
            d = cores.joinpath(*parts[:i])
            if not (d / "__init__.py").exists() and d.with_suffix(".py").exists():
                ok = False
                break
        if ok:
            mods.add(mod)
    return mods


def all_core_modules() -> set[str]:
    """Every dotted module path under core/ (for divergence checks)."""
    mods: set[str] = set()
    for cp in (REPO / "core").rglob("*.py"):
        rel = cp.relative_to(REPO / "core")
        mod = ".".join(rel.with_suffix("").parts)
        if mod == "__init__":
            mod = ".".join(rel.parent.parts)
        mods.add(mod)
    return mods


def _exact_target(module: str, identical: set[str]) -> str | None:
    """cores.* replacement iff the FULL module path is identical.

    Prefix matching is unsafe: `core.a.b.c` must not collapse to `cores.a.b`.
    """
    if module == "core":
        return None
    rest = module[len("core.") :]
    if rest in identical or f"{rest}.__init__" in identical:
        return "cores." + rest
    return None


def _is_package(module: str, identical: set[str]) -> bool:
    """True if `module` resolves via an identical __init__ (package), not a .py."""
    if module == "core":
        return False
    rest = module[len("core.") :]
    return f"{rest}.__init__" in identical and rest not in identical


CORE_REF_RE = re.compile(r"core\.[\w.]+")


def core_internal_refs(identical: set[str]) -> set[str]:
    """Identical modules still referenced by surviving core/ files.

    core/ files are NOT rewritten (their internal graph must stay intact —
    cores/*/__init__.py eagerly imports core.*, so rewriting inside core/
    can create circular imports). Any identical module referenced via a
    ``core.<mod>`` token (import, string, dynamic) must keep its core/ copy.
    """
    refs: set[str] = set()
    core_dir = REPO / "core"
    for p in _iter_py_files(core_dir):
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for m in CORE_REF_RE.finditer(text):
            parts = m.group(0)[len("core.") :].split(".")
            for i in range(len(parts), 0, -1):
                cand = ".".join(parts[:i])
                if cand in identical:
                    refs.add(cand)
                    break
                if f"{cand}.__init__" in identical:
                    refs.add(f"{cand}.__init__")
                    break
    return refs


def tainted_packages(all_core: set[str], identical: set[str]) -> set[str]:
    """Package paths containing any divergent/core-only descendant module.

    Rewriting `from core.PKG import attr` is unsafe when PKG's subtree has
    non-identical files: the identical __init__ may re-export names that
    resolve to different implementations under cores/.
    """
    tainted: set[str] = set()
    for m in all_core:
        if m in identical or f"{m}.__init__" in identical:
            continue
        parts = m.split(".")
        for i in range(1, len(parts)):
            tainted.add(".".join(parts[:i]))
    return tainted


def _prefix_tainted(dotted: str, tainted: set[str]) -> bool:
    """True if any PROPER ancestor package of `dotted` is tainted.

    A divergent package __init__ means the subtree is pending adjudication:
    rewriting core.PKG.sub → cores.PKG.sub would activate cores' divergent
    __init__ (which may import cores.*) while other consumers still use
    core.* — mixing two implementations of the same models/contracts.
    """
    parts = dotted.split(".")
    return any(".".join(parts[:i]) in tainted for i in range(1, len(parts)))


def _from_import_safe(mod: str, names: list[str], identical: set[str], all_core: set[str]) -> bool:
    """True if rewriting `from core.<mod> import <names>` can't change semantics.

    Unsafe when an imported name is itself a DIVERGENT or core-only submodule
    (cores.<mod>.<name> would load a different implementation).
    """
    rest = mod[len("core.") :] if mod.startswith("core.") else ""
    if not rest:
        return True
    for name in names:
        name = name.strip().split(" as ")[0].strip()
        if not re.match(r"^\w+$", name):
            continue
        sub = f"{rest}.{name}"
        if sub in all_core and sub not in identical and f"{sub}.__init__" not in identical:
            return False
    return True


def rewrite_source(text: str, identical: set[str], all_core: set[str], tainted: set[str], stats: dict) -> str:
    # Handle 'import core.x' lines and 'from core.x import y' lines.
    out_lines = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        if stripped.startswith("from core") or stripped.startswith("import core"):
            newline = "\n" if line.endswith("\n") else ""
            body = line.rstrip("\n")
            code = body[len(indent) :] if indent else body
            m = re.match(r"(from\s+)(core(?:\.[\w.]+)?)(\s+import\s+)(.+)", code)
            if m:
                mod = m.group(2)
                target = _exact_target(mod, identical)
                names = [n.strip() for n in m.group(4).split(",") if n.strip()]
                if target is not None:
                    rest = mod[len("core.") :]
                    # Package with divergent descendants, or any tainted
                    # ancestor package: subtree pending adjudication.
                    if (
                        (_is_package(mod, identical) and rest in tainted)
                        or _prefix_tainted(rest, tainted)
                        or not _from_import_safe(mod, names, identical, all_core)
                    ):
                        target = None
                if target is None:
                    # `from core.PKG import SUB` where SUB is an identical
                    # submodule absorbed into cores/: rewrite only if EVERY
                    # imported name is such an identical submodule AND the
                    # package chain is untainted.
                    rel = Path(*mod[len("core.") :].split(".")) if mod != "core" else None
                    rel_dotted = ".".join(rel.parts) if rel is not None else ""
                    pkg_safe = rel_dotted and rel_dotted not in tainted and not _prefix_tainted(rel_dotted, tainted)
                    if rel is not None and pkg_safe:
                        names = [n.strip().split(" as ")[0].strip() for n in m.group(4).split(",")]
                        if names and all(re.match(r"^\w+$", n) and f"{rel_dotted}.{n}" in identical for n in names):
                            target = "cores." + rel_dotted
                if target:
                    stats["imports_rewritten"] += 1
                    line = f"{indent}{m.group(1)}{target}{m.group(3)}{m.group(4)}{newline}"
                    out_lines.append(line)
                    continue
            m = re.match(r"(import\s+)(core(?:\.[\w.]+)?)(\s+as\s+\w+)?(\s*(?:#.*)?)$", code)
            if m:
                mod = m.group(2)
                rest = mod[len("core.") :] if mod != "core" else ""
                # Plain `import a.b.c` must match the FULL module path —
                # prefix-matching would silently drop trailing parts.
                target = "cores." + rest if rest and (rest in identical or f"{rest}.__init__" in identical) else None
                if target is not None and ((_is_package(mod, identical) and rest in tainted) or _prefix_tainted(rest, tainted)):
                    target = None
                if target:
                    stats["imports_rewritten"] += 1
                    line = f"{indent}{m.group(1)}{target}{m.group(3) or ''}{m.group(4)}{newline}"
                    out_lines.append(line)
                    continue
        out_lines.append(line)
    text = "".join(out_lines)

    def _sub_dyn(m: re.Match) -> str:
        parts = m.group(2).split(".")
        # Longest identical-module prefix wins; attribute/submodule suffix preserved.
        for i in range(len(parts), 0, -1):
            cand = ".".join(parts[:i])
            if cand in identical or f"{cand}.__init__" in identical:
                # Tainted package or tainted ancestor: attr may resolve to a
                # different impl under cores/ — subtree pending adjudication.
                if _prefix_tainted(cand, tainted):
                    return m.group(0)
                if f"{cand}.__init__" in identical and cand not in identical and cand in tainted:
                    return m.group(0)
                suffix = ".".join(parts[i:])
                new = "cores." + cand + (f".{suffix}" if suffix else "")
                stats["dynamic_rewritten"] += 1
                return f"{m.group(1)}{new}{m.group(1)}"
        return m.group(0)

    text = DYNAMIC_RE.sub(_sub_dyn, text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report only (default)")
    ap.add_argument("--apply", action="store_true", help="rewrite import statements")
    ap.add_argument("--delete-core", action="store_true", help="delete absorbed core/ copies (requires --apply)")
    args = ap.parse_args()

    identical = identical_modules() & importable_cores_modules()
    stateful = stateful_modules(identical)
    identical -= stateful
    all_core = all_core_modules()
    tainted = tainted_packages(all_core, identical)
    print(f"[codemod] identical+importable: {len(identical) + len(stateful)}, stateful excluded: {len(stateful)}, tainted packages: {len(tainted)}")

    stats = {"files_changed": 0, "imports_rewritten": 0, "dynamic_rewritten": 0}
    changed: list[Path] = []
    core_dir = REPO / "core"
    for p in _iter_py_files(REPO):
        if core_dir in p.parents or p == core_dir:
            continue  # core/ internals stay untouched (see core_internal_refs)
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "core." not in text:
            continue
        new = rewrite_source(text, identical, all_core, tainted, stats)
        if new != text:
            stats["files_changed"] += 1
            changed.append(p)
            if args.apply:
                p.write_text(new, encoding="utf-8")

    print(
        f"[codemod] files changed: {stats['files_changed']}, "
        f"imports rewritten: {stats['imports_rewritten']}, "
        f"dynamic refs rewritten: {stats['dynamic_rewritten']}"
    )
    for p in changed[:50]:
        print(f"  ~ {p.relative_to(REPO)}")
    if len(changed) > 50:
        print(f"  ... and {len(changed) - 50} more")

    if args.delete_core:
        if not args.apply:
            print("[codemod] --delete-core requires --apply", file=sys.stderr)
            return 2
        kept = core_internal_refs(identical)
        # Modules under tainted packages keep their core/ copy too: their
        # imports were NOT rewritten, so un-migrated consumers still need it.
        tainted_mods = {m for m in identical if _prefix_tainted(m, tainted)}
        removed = 0
        for mod in sorted(identical - kept - tainted_mods):
            rel = Path(*mod.split("."))
            for cand in (REPO / "core" / rel.with_suffix(".py"), REPO / "core" / rel / "__init__.py"):
                if cand.exists():
                    cand.unlink()
                    removed += 1
                    break
        print(f"[codemod] deleted {removed} absorbed core/ copies ({len(kept) + len(tainted_mods)} kept — core/-internal refs or tainted subtree)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
