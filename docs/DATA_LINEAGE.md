# OWNEX — Las dos historias de datos: `~/.orion` vs base instalada

> Medido el 2026-10-05 contra las dos bases reales. Sin backlog de datos: lo que
> no está aquí, no existe en ninguna parte.
> Respaldos en `~/ownex_backup_20261005_165907/`, los tres con `integrity=ok`.

---

## 1. El resultado simplifica el problema

La pregunta era "qué historia conservar". La medición dice otra cosa:

```
~/.orion    57 tablas      ← historia de `python run.py`
~/.ownex    76 tablas      ← instalada (repo migrado)

comunes           57
sólo en ~/.orion   0     ← ninguna tabla exclusive
sólo en ~/.ownex  19     ← esquema más nuevo
```

**`~/.orion` no tiene ninguna tabla que la base instalada no tenga.** Es
estrictamente un subconjunto de esquema. Y en todas las tablas con datos, la base
instalada ya tiene MÁS, salvo una.

### La única tabla con valor exclusivo: `endpoints`

| tabla | `~/.orion` | `~/.ownex` | |
|---|---:|---:|---|
| **`endpoints`** | **32.271** | 9.922 | **+22.349 sólo en `.orion`** |
| `memory_records` | 5 | 7.711 | ya cubierta |
| `pipeline_runs` | 21 | 1.621 | ya cubierta |
| `scan_runs` | 80 | 378 | ya cubierta |
| `notifications` | 566 | 5.090 | ya cubierta |
| `system_state_records` | 5.747 | 43.486 | ya cubierta |

**Todo lo demás de `.orion` está obsoleto.** No hay nada que rescatar ahí.

---

## 2. Los endpoints de las dos bases casi no se tocan

Con la clave natural `(target_id, path, method)`:

```
claves únicas  ~/.orion : 32.271   (0 duplicados internos)
claves únicas  ~/.ownex :  9.544   (4 grupos duplicados internos)

intersección            :     10   ← casi disjuntas
sólo en ~/.orion        : 32.261
sólo en ~/.ownex        :  9.534
```

`~/.orion` es **profundo**: 32.261 endpoints sólo suyos, concentrados en **20
targets**. La base instalada es **amplia**: 208 targets distintos.

---

## 3. Por qué NO se pueden copiar tal cual

`endpoints.target_id` apunta a `targets.id`, y **los ids no coinciden**:

```
targets                    ~/.orion: 686    ~/.ownex: 722
target_ids usados por endpoints  ~/.orion: 20      ~/.ownex: 208

target_id de ~/.orion que NO existen en ~/.ownex.targets : 20  (los 20)
→ endpoints de ~/.orion que quedarían huérfanos          : 32.271 de 32.271  (100%)
```

**Copiar las filas sin remapear rompe el 100% de la FK.** Es unfk yaLatente
(la base instalada arrastra 3.299 violaciones preexistentes; añadir 32.271 más
sería otra categoría).

### Pero los targets SÍ se reconocen por nombre

```
targets por nombre   comunes: 664   sólo en ~/.orion: 22   sólo en ~/.ownex: 49
```

Los mismos targets existen en ambas bases con **ids distintos**. Eso hace la
remapeo posible:

```
PARA CADA endpoint de ~/.orion:
    target_nombre ← ~/.orion.targets[target_id].name
    nuevo_target_id ← ~/.ownex.targets[target_nombre].id     (664 de 686 resueltos)
    si (nuevo_target_id, path, method) NO existe en ~/.ownex.endpoints:
        insertar
```

Resultado esperado: ~32.261 endpoints añadidos, 22 huérfanos por nombre (los 22
targets exclusivos de `.orion`).

---

## 3.1 RESULTADO — MERGE APLICADO (2026-10-04 17:22)



Ejecutado sobre una copia, nunca directo. Traza completa:



**Los 32.182 insertados tienen target válido.** Las 1.434 huérfanas y las 3.299
violaciones FK son **preexistentes**, medidas antes y después: la fusión no
agregó ninguna.

Ninguno de los 22 targets exclusivos de  se perdió: los 686 nombres de
 se resolvieron todos contra .

Verificado con la app real arrancada:
  GET /api/health              200
  targets 722 · endpoints 42.104 · pipeline_runs 1.621 · memory_records 7.711

Rollback:  (9.922 endpoints) y
.

---

## 4. Recomendación

**Fusionar sólo `endpoints`, remapeando `target_id` por nombre de target.**
El resto de `.orion` no aporta nada.

Requisitos previos, en orden:

1. **Snapshot fresco de la base instalada** (ya hay uno, pero la base cambió al
   migrar — rehacerlo justo antes).
2. **Probar el remapeo sobre una copia**, nunca sobre `~/.ownex` directamente.
3. Verificar después: `foreign_key_check` no debe crecer, y el conteo de
   `endpoints` debe quedar en ~42.183.
4. Los **22 targets exclusivos de `.orion`** requieren decisión aparte: se
   pierden, o se importan también.

### Riesgos declarados

| riesgo | probabilidad | mitigación |
|---|---|---|
| Remapeo erróneo → endpoints colgados del target equivocado | baja | el nombre es la única clave compartida; verificar con una muestra |
| Los 22 targets exclusivos se pierden | **cierta** | es una decisión, no un bug |
| La base instalada ya tiene 3.299 FK huérfanas | cierta | **preexistente, no de esta fusión**; medirlas antes y después para no atribuir mal |
| Duplicados: 4 grupos ya duplicados en `~/.ownex` | baja | no los toco; el `insert if not exists` los deja como están |

---

## 5. Lo que NO hay que fusionar

`~/.orion` tiene además `aegis.db`, `atlas/`, `memory.db`, `orion.db` y
`orion_core.db` en su directorio `database/`. Ninguno lo referencian
`api/main.py` ni `run.py` tras el commit `8209e02d`. No se fusionan.

---

## 6. Lo que queda después

Con esta fusión, la fragmentación de datos queda:

```
una sola base     ~/.ownex/database/catseye.db
respaldo           ~/ownex_backup_*/            (verificable)
cuarentenas        /tmp/ownex_fixture_quarantine_*/ , /tmp/ownex_testdb_quarantine_*/
```

Las dos bases huérfanas (`~/.ownex/…/cateye.db`, `~/.local/share/OWNEX/…`) están
respaldadas y sin uso desde el 25/08 y el 30/09 respectivamente. Se pueden mover
a cuarentena cuando decidas; no hacen falta para nada.
