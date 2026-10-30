"""
Components usados en el template pero NO importados.

Por qué este guard: Vue resuelve un componente no registrado como
"custom element" en runtime — **el build pasa, `vue-tsc` da 0 errores, y
la página se renderiza vacía en el navegador**. Pasa cuando dos flujos
editan el mismo `.vue` a la vez y uno pisa el import del otro
(medido 2026-08-08: `SystemStatePanel` y `AlignerrPanel` quedaron usados
sin importar y el build Follow en verde).

Este guard se corre como test: lee cada `.vue` y falla si usa un tag
PascalCase que no está importado ni registrado localmente.
"""

from __future__ import annotations

import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1] / "frontend" / "src"

#: Tags que son elementos HTML nativos, no componentes Vue.
_NATIVE_TAGS = {
    "template",
    "component",
    "slot",
    "transition",
    "keep-alive",
    "teleport",
    "suspense",
    "div",
    "span",
    "p",
    "a",
    "ul",
    "ol",
    "li",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "button",
    "input",
    "label",
    "form",
    "section",
    "header",
    "footer",
    "nav",
    "main",
    "aside",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "img",
    "svg",
    "path",
    "code",
    "pre",
    "strong",
    "em",
    "small",
    "hr",
    "br",
    "iframe",
    "canvas",
    "details",
    "summary",
    "dialog",
    "select",
    "option",
    "textarea",
    "fieldset",
    "legend",
    "figure",
    "figcaption",
    # Built-ins de Vue: se usan en el template sin importarse.
    "Teleport",
    "Transition",
    "TransitionGroup",
    "KeepAlive",
    "Suspense",
    "Component",
    "Slot",
    "Template",
}

_TAG_RE = re.compile(r"<(/?)([A-Z][A-Za-z0-9]*)\b")
# Soporta `import X from`, `import X, { a, b } from` e `import { a as c } from`.
_IMPORT_RE = re.compile(r"import\s+(.*?)\s+from\s+['\"]", re.S)
_DEFAULT_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(,|$)")


def _strip_comments(source: str) -> str:
    """Sin comentarios: un docstring que menciona un import lo confunde."""
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"^\s*//.*$", "", source, flags=re.M)


def _registered_names(source: str) -> set[str]:
    source = _strip_comments(source)
    names: set[str] = set()
    for clause in _IMPORT_RE.findall(source):
        clause = clause.strip().rstrip(",")
        if clause.startswith("{"):
            inner = clause.strip("{}")
        else:
            # `X, { a, b }` -> default + nombrados
            head, sep, tail = clause.partition("{")
            dm = _DEFAULT_RE.match(head)
            if dm:
                names.add(dm.group(1))
            inner = tail.strip("{}") if sep else ""
        for part in inner.split(","):
            part = part.strip().replace("type ", "")
            if not part:
                continue
            # `A as B` -> el nombre local es B
            names.add(part.split(" as ")[-1].strip())
    # `const X = defineAsyncComponent(...)` también registra el nombre
    for block in re.findall(r"(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*define(?:Async)?Component", source):
        names.add(block)
    # `components: { X }` en defineOptions / script setup object
    for block in re.findall(r"components\s*:\s*\{([^}]*)\}", source, re.S):
        for part in block.split(","):
            part = part.strip().split(":")[-1].strip()
            if part:
                names.add(part)
    return names


def _template_only(source: str) -> str:
    """Sólo el bloque `<template>`.

    Escanear el archivo entero daba falsos positivos: `<Props>` en el
    `<script>` es un genérico de TypeScript, no un componente.
    """
    m = re.search(r"<template>(.*)</template>", source, re.S)
    return m.group(1) if m else ""


def test_no_componentes_usados_sin_importar() -> None:
    """Ningún `<MiComponente>` del template puede quedar sin registrar."""
    rotos: list[str] = []
    for vue in FRONTEND.rglob("*.vue"):
        source = _strip_comments(vue.read_text(encoding="utf-8", errors="ignore"))
        used = {tag for _, tag in _TAG_RE.findall(_template_only(source)) if tag not in _NATIVE_TAGS}
        if not used:
            continue
        registered = _registered_names(source)
        missing = sorted(used - registered)
        if missing:
            rel = vue.relative_to(FRONTEND)
            rotos.append(f"{rel}: {missing}")
    assert not rotos, (
        "Componentes usados en el template SIN importar (Vue los resuelve como "
        "custom element en runtime: el build y vue-tsc pasan, la página sale vacía):\n  " + "\n  ".join(rotos)
    )


def test_la_comprobacion_detecta_un_import_roto() -> None:
    """El guard tiene que fallar ante el caso real, no ser decorativo."""
    sample = (
        "<template><Panel /><Widget /></template>\n<script setup lang='ts'>\nimport Panel from './Panel.vue'\n</script>"
    )
    registered = _registered_names(sample)
    used = {t for _, t in _TAG_RE.findall(sample) if t not in _NATIVE_TAGS}
    assert used - registered == {"Widget"}, "el detector debe ver el componente faltante"
