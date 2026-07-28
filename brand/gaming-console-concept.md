# OWNEX Gaming Console — Centro de Control Inmersivo

## Concepto
Inspirado en Steam Big Picture, PS5 UI, y Xbox Dashboard.
Una experiencia de consola gaming para el command center autónomo.

## Características clave

### 1. Home Screen (Inicio Inmersivo)
- Fondo oscuro con partículas/constelaciones animadas
- Salud del sistema con círculo de progreso (95% animado)
- Revenue del mes con gráfico de barras en vivo
- Top 5 oportunidades con colores por prioridad (🥇 oro, 🥈 plata, 🥉 bronce)
- Actividad reciente en time-line estilo log de consola

### 2. Navigation (Barra Superior)
- Píldoras de ciclo: FORGE · PULSE · VAULT · ATLAS · SECURITY
- Indicador LIVE verde parpadeante
- Estado del sistema en tiempo real

### 3. Agent Fleet (Panel de Agentes)
- Tarjetas tipo "personaje" con:
  - Nombre + ícono
  - Estado (🟢 online / 🟡 idle / 🔴 offline)
  - Métricas en vivo (uptime, score, tareas activas)
- Animación de "respiración" en agentes activos

### 4. Activity Log (Feed tipo consola)
- Time-stamps precisos
- Íconos por tipo: ✅ éxito, ★ hallazgo, ⚠ alerta, ℹ info
- Scroll infinito con fade

### 5. Quick Actions (Botones de acción rápida)
- Run Forge · Run Pulse · Review Vault · Quick Scan
- Efecto hover con glow azul

## Diseño
- **Resolución:** 1920×1080 (full screen)
- **Colores:** #05060A fondo, #3B82F6 primary, #F59E0B gold, #34D399 success
- **Tipografía:** Space Grotesk (display), Inter (body), JetBrains Mono (logs)
- **Materiales:** Glassmorphism en cards, scanlines CRT sutiles, glow dinámico

## Archivos
- `brand/ownex/gaming-console-ui.svg` — Mockup completo 1920×1080
- Para implementar en Vue: usar los mismos componentes existentes con layout grid 4-columnas

## Próximos pasos de implementación (frontend)
1. Crear componente `GamingHome.vue` con el layout del mockup
2. Migrar `MissionControl.vue` a usar el nuevo diseño
3. Agregar animaciones CSS (fade-in, pulse, glow)
4. Integrar datos reales del dashboard API
