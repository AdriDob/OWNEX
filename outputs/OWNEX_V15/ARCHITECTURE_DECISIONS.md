# OWNEX V15 — ARCHITECTURE DECISIONS

Estado: **ANÁLISIS ENTREGADO, MIGRACIÓN NO EJECUTADA** (bloqueada por trabajo concurrente)

## Evidencia medida (2026-11-09, sobre `14c6f7cb`)

```
core/   708 archivos python   133.978 LOC
cores/  1.105 archivos python  246.304 LOC
rutas idénticas en ambos árboles: 421
  byte-idénticas:  306  (59.760 LOC duplicados verbatim)
  divergentes:     115

archivos que importan el árbol opuesto:
  cores/ -> core.*    267
  core/  -> cores.*    49
  api/   -> cores.*   105
  api/   -> core.*     53
```

> Difiere de la auditoría del propietario (317 y 94). Mi conteo es por **archivo** con
> `git grep -l`, no por línea; tomo el mío como referencia porque es reproducible con el comando
> de arriba. La conclusión no cambia: la dependencia es **bidireccional**.

## Por qué ADR-0002 ("todo a `cores/`") no debe aprobarse tal cual

1. **El scheduler operativo vive en `core/`.** `api/lifespan.py:227` importa
   `core.scheduler.scheduler.get_core_scheduler` y `api/lifespan.py:442` importa
   `core.scheduler.jobs.get_all_jobs`. `cores/scheduler/` **no existe** hoy. Mover todo a `cores/`
   implica mover el scheduler primero, y el scheduler es lo que mantiene vivo el sistema.
2. **49 archivos de `core/` importan `cores/`, y 267 de `cores/` importan `core/`.** No hay un
   "árbol viejo" y un "árbol nuevo": hay dos árboles en un ciclo. Cualquier reemplazo global
   `core.` → `cores.` rompe el ciclo en ambos sentidos a la vez y no es revisable.
3. **306 archivos son byte-idénticos.** Para ésos no hace falta migración: se borra el duplicado
   y no se toca ningún import (así se hizo con `app_registry`, ver abajo). Los 115 divergentes sí
   necesitan adjudicación archivo por archivo, con tests.

### Estrategia recomendada

**Canónico por dominio, no por carpeta.** Tres pasos, en este orden:

1. **Borrar los gemelos sin importadores** (coste cero, riesgo cero). Muestra: `cores/app_registry.py`
   lo importaban cero archivos (los cinco consumidores usan `core.app_registry`) y era idéntico
   en estructura → borrado en `14c6f7cb`. Aplicable a un subconjunto de los 306.
2. **Adjudicar los 115 divergentes con matriz** (ruta, SHA256 de ambas, importadores, funciones
   exclusivas, tests, consumidor runtime, implementación elegida, migración, riesgo, estado).
   Regla: no gana la versión más nueva ni la más larga ni la que está en `cores/`; gana la que
   tiene consumidores runtime y tests.
3. **`core/` no se borra** hasta que: el scheduler tenga ubicación canónica, no queden imports
   al árbol retirado, la suite del dominio pase, y la API arranque cargando el canónico.

## ADR-0003 (bus de eventos dual)

Recomendación: **adoptar `cores.events.event_bus` como canónico, sí**, con estas condiciones
antes de migrar:

- Inventario de productores y consumidores de ambos buses.
- `core.events.event_bus` queda como fachada que delega, no como segundo bus.
- Diferencias a cubrir en el canónico: namespaces, wildcards, prioridades, seguridad
  async/threading, persistencia, historial que lee `api/routers/activity.py`.
- Garantía de **entrega única** (evitar doble dispatch durante la transición).
- Tests obligatorios: publicar en un subsistema y recibir en otro, wildcard, namespace,
  prioridad, persistencia/recuperación, eventos críticos, concurrencia, sin duplicados, sin
  pérdidas, compatibilidad de los imports viejos.

No ejecutado en V15: es un cambio de superficie alta y el árbol tiene dos escritores.

## Reconciliación de `release/win11-stable`

```
merge-base                    898dcc7f2
exclusivos de main            57
exclusivos de la rama estable 251
estado                        DIVERGED
```

Propuesta (no ejecutada): **no fusionar**. Pasos:

1. Identificar el último release realmente publicado y su tag.
2. Clasificar los 251 commits exclusivos de la rama estable: ¿son de producto, de instalador
   (PyInstaller/Tauri/firmas) o de configuración de release?
3. Clasificar los 57 de `main`: ¿parches de seguridad/estabilidad que deban viajar a la estable?
4. Matriz de compatibilidad Windows 11 sobre los candidatos.
5. Estrategia de actualización segura: cherry-pick de los parches de seguridad, dejando la
   estable como línea de release hasta que exista una build nueva verificada.

Nada de esto se hizo: implica modificar una rama de release y no hay build Windows verificable
en este entorno.
