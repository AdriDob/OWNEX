# OWNEX Desktop — Guía de Instalación y Primer Uso (Windows)

> Esta guía te lleva de la mano: instalación → primer arranque → verificación de
> datos reales → estado óptimo. Sigue los pasos en orden; cada uno indica qué
> deberías ver antes de avanzar.

---

## 1. Requisitos

| Requisito | Detalle |
|---|---|
| Windows | 10 u 11 (64 bits) |
| Disco libre | ~1,5 GB |
| RAM | 4 GB recomendado (mínimo 2 GB) |
| Internet | Necesario solo para descubrimiento de targets/oportunidades |

No necesitas instalar Python, Node ni nada más: **todo viene dentro del instalador**.

---

## 2. Instalación

1. Copiá `OWNEX-Desktop-Alpha-Setup.exe` desde el escritorio/OneDrive a donde quieras guardar el instalador (o ejecutalo directo).
2. Ejecutalo con doble clic.
   - Si Windows SmartScreen muestra advertencia: el build no está firmado (debug alpha). Clic en **"More info" → "Run anyway"**.
3. Seguí el asistente de instalación (directorio por defecto: `%LOCALAPPDATA%\Programs\OWNEX\`).
4. Al terminar, ejecutá **OWNEX Desktop** desde el acceso del escritorio o el menú Inicio.

**✅ Deberías ver:** la ventana OWNEX (fondo oscuro, sidebar con 8 secciones:
MISSION, INTELLIGENCE, SURFACE, FINDINGS, REPORTS, OPERATIONS, TERMINAL, SYSTEM).

---

## 3. Primer arranque — qué está pasando (importantísimo)

La app es **autocontenida**: al abrirla, el backend (API + pipeline + scheduler)
arranca **dentro del mismo proceso** en segundo plano, en `http://127.0.0.1:8000`.

1. La ventana aparece **al instante** (~3 s).
2. Durante los primeros **30-60 s** el backend inicia: crea la base de datos
   (`database/catseye.db` junto a la app), corre el boot y arranca los servicios.
   - La vista MISSION Control puede mostrar `Source: local` o valores `--` en
     ese lapso. Es normal: **la vista se refresca sola cada 10 segundos** y
     pasa a `Source: api` con datos reales cuando el backend queda listo.
3. Cuando MISSION muestre `Source: api` con conteos de targets/findings/ops,
   el sistema está operativo.

**✅ Deberías ver (1-2 min después de abrir):**
- `Backend API: online` en la sección SYSTEM.
- KPIs con números reales (targets, findings, activity).
- La sección TERMINAL funcionando (shell real vía WebSocket).

---

## 4. Verificación de datos reales (opcional, pero recomendada)

Para confirmar que el sistema produce datos:

1. Abrí la sección **SYSTEM** → deben verse `Backend API: online`, `Scheduler: running`.
2. Con el navegador (o `curl`), entrá a `http://127.0.0.1:8000/api/health`
   → debe responder `200` con `{"status": "ok", ...}`.
3. Esperá unos minutos: el scheduler descubre y escanea targets automáticamente
   (pipeline completo: discover → recon → hipótesis → validación → reporte).
   La sección **SURFACE** lista los targets con su cantidad de endpoints.

---

## 5. Migrar tus datos desde otra PC (opcional, solo si ya usaste OWNEX antes)

Si ya tenés targets/recon en otra máquina, NO los copies a mano: usá la
migración oficial (export/import con verificación de integridad).

**En la PC de origen (Linux/desktop):**
```bash
python run.py --migrate-export ~/OWNEX_MIGRATE.zip
# Si el archivo queda muy grande (>1 GB): python run.py --migrate-export --no-targets
```

**En la PC destino (Windows):** el bundle incluye la herramienta de migración.
Ubicá el zip, y desde una terminal en la carpeta de la app:

```bash
# dentro de la carpeta instalada
OWNEX-Desktop-Alpha.exe --migrate C:\ruta\OWNEX_MIGRATE.zip
```

La importación verifica checksums, restaura datos y preserva la clave de
IdentityVault. La licencia queda ligada al hardware (reactivala si el HWID
cambió — la guía se imprime al final de la migración).

> **Sin migración, no hay problema:** el sistema arranca con una base vacía
> y comienza a descubrir targets por sí solo.

---

## 6. Estado óptimo — checklist del día 1

| Check | Cómo | Esperado |
|---|---|---|
| App abierta y estable | Ejecutá la app | Ventana viva, sin diálogos de error |
| Backend online | SYSTEM → Backend API | `online` |
| Pipeline corriendo | SYSTEM → Scheduler | `running` |
| Datos reales visibles | MISSION | `Source: api` + KPIs con números |
| Terminal OK | TERMINAL | Shell interactivo (escribí `help` o `dir`) |
| Primeros targets | SURFACE (tras 5-10 min) | Targets con endpoint_count ≥ 1 |

Si algún check no pasa, mirá la sección de troubleshooting abajo.

---

## 7. Troubleshooting rápido

| Síntoma | Causa probable | Solución |
|---|---|---|
| SmartScreen warning | Build sin firma | "More info" → "Run anyway" |
| La app se cierra sola al arrancar | Antivirus/Defender bloqueando | Excluir la carpeta de instalación |
| MISSION siempre `Source: local` | El backend tarda en bootear | Esperá 2 min (auto-refresh cada 10 s). Si persiste, cerrá y reabrí la app |
| `database is locked` al migrar | La app ya abrió la DB | Cerrá la app antes de importar |
| Puerto 8000 ocupado | Otro backend dev corriendo | Cerrá el otro proceso; la app usa el que esté vivo |
| Terminal no conecta | Backend aún iniciando | Esperá a que SYSTEM diga `online` |

---

## 8. Notas de seguridad

- **100% local**: la app escucha solo en `127.0.0.1` (loopback). Nada se expone a la red.
- Los datos viven en la carpeta de instalación (`database/`, `data/`).
- Sin telemetría ni cloud: el descubrimiento de targets usa APIs públicas de
  plataformas de bug bounty (HackerOne, Bugcrowd, etc.).

---

*Generado automáticamente con el pipeline de release OWNEX — revisar junto a
`ownexinstalador/docs/WINDOWS_INSTALL.md` para detalles técnicos.*
