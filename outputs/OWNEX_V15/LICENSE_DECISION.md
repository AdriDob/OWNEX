# OWNEX V15 — LICENSE DECISION

Estado: **BLOQUEADO POR DECISIÓN DEL PROPIETARIO** · no se modificó `LICENSE` ni `README.md`

## Hechos verificados

| Hecho | Evidencia |
|---|---|
| `LICENSE` contiene texto MIT completo | `MIT License` / `Copyright (c) 2026 Rastro` |
| Se agregó una sola vez y nunca cambió | `git log --follow -- LICENSE` → único commit `5ae7280e` (2026-06-28) "ui: add product screenshots and MIT license" |
| `README.md` declara lo contrario | sección `## License`: `**Proprietary.** All rights reserved.` |
| El repo se distribuyó desde entonces | 82 tags, releases v7.x publicados, repositorio público |

## Por qué no lo cambié

La especificación prohíbe modificar la licencia automáticamente, y con razón: **cambiar el
archivo hoy no revoca los permisos MIT ya concedidos** sobre las copias distribuidas hasta hoy.
Cualquier persona que obtuvo el código bajo MIT conserva esos derechos para esa versión,
indefinidamente. Reescribir `LICENSE` a propietario y dejar el README como está produciría un
repositorio con una afirmación legal que el propio archivo desmiente.

## Opciones (elegir una)

### Opción A — Seguir en MIT (consistente, coste cero)

- Dejar `LICENSE` como está.
- Corregir el README: `## License` → MIT, con la aclaración de que es un proyecto personal.
- Ventaja: cero riesgo legal, cero trabajo. El código sigue disponible, y el valor competitivo
  de OWNEX nunca estuvo en el código publicado sino en los datos y las cuentas.
- Coste: cualquiera puede reutilizar el código.

### Opción B — Propietario desde una versión nueva (requiere trabajo legal)

- Crear `LICENSE` propietario **a partir de** el próximo tag (p. ej. `v8.0.0`), no retroactivo.
- Documentar en el README: "versiones hasta `<tag>` bajo MIT; desde `<tag>` propietario".
- Opcional: `NOTICE` con el texto de la concesión anterior.
- Ventaja: cierra el código hacia adelante sin mentir sobre el pasado.
- Coste: hay que asumir que las versiones ya publicadas siguen siendo MIT para siempre.

### Opción C — Propietario y repo privado (la más simple si el objetivo es cierre real)

- Cambiar la visibilidad del repositorio a privado.
- Ventaja: el problema de qué dice el archivo deja de tener consecuencias prácticas.
- Coste: se pierde el "portfolio público" del proyecto; hay que decidir si eso importa.

## Recomendación

**Opción A ahora, Opción B cuando exista una versión que valga la pena cerrar.** Motivo: hoy la
contradicción no protege nada (el código ya es MIT y público) y sí cuesta credibilidad: cualquiera
que lea `LICENSE` y después el README concluye que el proyecto no se toma en serio sus propios
términos. Corregir la afirmación es trabajo de un minuto; el cierre legal es una decisión de
negocio que corresponde al propietario.

## Qué NO se hará

- No se cambiará `LICENSE` sin la decisión explícita del propietario.
- No se pondrá un badge de licencia que contradiga el archivo.
- No se afirmará "proprietary, all rights reserved" en el README mientras `LICENSE` diga MIT.
