from __future__ import annotations

"""Validation Engine — transforma hipótesis en hallazgos validados experimentalmente.
No es un "HTTP probing engine". Es un motor de validación estratégico:
  1. Economic Score — ¿gastar una request vale la pena?
  2. Validation Plan — qué probar exactamente, cómo, con qué señal
  3. Minimal Probe — ejecutar la prueba más barata que da máxima señal
  4. Confidence — puntuar la evidencia recolectada
  5. Promote — si confianza > umbral, crear Finding en DB
Soporta múltiples protocolos via adaptadores (HTTP, GraphQL, WebSocket, gRPC...).
HTTP es solo el primero.
"""
