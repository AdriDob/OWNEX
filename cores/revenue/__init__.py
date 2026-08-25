"""OWNEX Revenue package — orquestación de ingresos (spec BACKEND ALPHA 1.0 §3).

Los componentes viven aquí SOLO cuando no existe una responsabilidad
equivalente reutilizable (Regla de Oro). El EV vive en
``cores/direct_work_engine/economics.py`` (SSOT); el estado canónico de
ejecución en ``core/execution_queue.py``; la proyección económica en
``cores/revenue_tracker``. Este paquete agrega piezas faltantes verificadas
por auditoría: Availability Intelligence (P0-4).
"""
