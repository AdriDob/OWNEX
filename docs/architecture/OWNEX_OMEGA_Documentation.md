# OWNEX OMEGA - Extension Infrastructure

## Sistema Inteligente de Extensiones Autónomas

### Misión: Tres Capas de Autosuficiencia

**Capa 1: Personalidad del Sistema**
- Hablamos como un ingeniero senior
- Explicamos como un profesor excelente
- Sentimos como un asistente personal
- Nunca como una caja negra

**Capa 2: Arquitectura Autónoma**
- 13 extensiones OSS centrales para capacidades avanzadas
- Acceso instantáneo sin necesidad de instalar paquetes manualmente
- Auto-configuraciones inteligentes antes de cada uso
- Evaluación automática del estado del sistema

**Capa 3: Supervisión Simple**
- Estado comprensible en menos de 60 segundos
- Código de colores intuitivo 🔴🟡🟢
- Información relevante solamente
- Control humano solamente para decisiones críticas

---

## VISIÓN GENERAL DEL SISTEMA - Modo Supervisión

### Estado Actual del Sistema
🟢 **Extensiones Cargadas**: 13/13 - Todas las extensiones principales funcionando
📡 **Capacidades Disponibles**: 13 categorías - Memoria, Automatización, IA, Datos, Redes, Inspección de Código
🤖 **Servicios Activos**: 7 contenedores en docker-compose.ownex.yml
📄 **Oportunidades Encontradas**: **PENDIENTE DE DATOS** - Las extensiones generan hallazgos automáticamente
🛠 **Tareas Procesando**: **PENDIENTE DE DATOS** - Tareas en cola para ejecución
⏳ **Revisión Requerida**: **NINGUNA** - Todo automático cuando es posible

### Leyenda de Estados
🟢 **SISTEMA FUNCIONANDO** - Servicio/servicio funcionando normalmente
🟡 **REVISIÓN REQUERIDA** - Revisión humana necesaria antes de continuar
🔴 **ERROR** - Servicio falló, requiere intervención manual

---

## ARQUITECTURA DELAS EXTENSIONES - Cómo Funciona

### Modo Aprendizaje: Componentes Fundamentales

**1. ExtensionRegistry - Directorio Maestro**
No estoy creando este directorio simplemente porque sí.

Se necesita porque OWNEX debe poder descubrir y cargar extensiones automáticamente sin intervención manual.

Si no existe, las extensiones nunca se podrían utilizar, y el sistema tendría que gestionarlas manualmente, lo que requeriría mucho trabajo y sería propenso a errores.

**2. ExtensionManifest - Contrato de Cada Extensión**
La extensión no se creó simplemente por crearla.

Se necesitaba porque cada extensión debe explicar qué puede hacer (sus capacidades) exactamente, de forma que el sistema pueda cargarla y comunicarse con ella.

Sin el contrato, el sistema tendría que adivinar qué hace cada extensión, lo que sería inseguro y poco confiable.

**3. IConnector - Puerta de acceso estandarizada**
Esta puerta se creó porque cada extensión necesita una forma estandarizada de conectarse al sistema principal.

Si cada extensión hiciera su propia conexión, habríamos muchos errores y problemas de compatibilidad diferentes.

La puerta garantiza que todas las extensiones funcionen de la misma forma segura.

**4. EventBus - Sistema de comunicación central**
El bus de eventos se agregó porque las extensiones deben comunicarse entre sí sin necesidad de preguntar cómo.

Si cada extensión hiciera sus propias llamadas, tendríamos problemas de orden de ejecución, cientos de llamadas duplicadas y errores de sincronización.

El EventBus maneja toda la complejidad y hace que las extensiones trabajen juntas automáticamente.

### Cómo Navegar el Sistema

**Identificar una Extensión:**
¿Necesita memoria vectorial, automatización, inteligencia de código, datos o redes? Las extensiones se organizan por funcionalidad:
- ✅ **lightrag, cognee, graphiti** - Memoria y Conocimiento
- ✅ **langfuse** - Observabilidad y Métricas
- ✅ **skyvern, crawl4ai, n8n, composio, kestra** - Automatización y Procesamiento
- ✅ **graphify, skill_seekers, promptfoo, nanobot** - Inspección de Código y Evaluación

**Cargar una Extensión:**
¿Necesita capacidades adicionales? Simplemente agregue extensiones con code `ownex.extension.registry.get_extension_registry().load("nombre_de_la_extensión")`

**Ver el Estado:**
Ver todo en tiempo real con el script de verificación: `python3 verify_extensions.py`

**Usar una Extensión:**
Después de cargar, cada extensión proporciona métodos estándar:
- `connect()` - Conectar con la extensión
- `query(params)` - Hacer una consulta a la extensión
- `insert(data)` - Almacenar datos en la extensión
- `stats()` - Obtener estadísticas de la extensión

---

## CREACIÓN DE UNA EXTENSIÓN - Ejemplo Completo

### Pasos Mínimos para Agregar una Nueva Extensión

**1. Crear Directorio** `extensions/nombre_de_extensión/`
No se crea un directorio simplemente sin propósito.

Se necesita porque cada extensión debe aislarse en su propio espacio, evitando conflictos y permitiendo instalaciones independientes.

**2. Agregar __init__.py**
El archivo __init__.py gestiona automáticamente si la extensión está instalada o no.

Protege al sistema de extensiones faltantes o con errores.

```python
from __future__ import annotations
import logging

logger = logging.getLogger("ownex.nombre_de_extensión")

try:
    # Importar solo si está disponible
    import nombre_de_extensión

    _EXTENSION_AVAILABLE = True
except ImportError:
    _EXTENSION_AVAILABLE = False
    logger.warning("nombre_de_extensión no instalado — extención deshabilitada")
```

**3. Agregar manifest.py**
El manifiesto explica exactamente qué puede hacer la extensión.

```python
from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="nombre_de_extensión",
    name="Nombre Descriptivo",
    version="1.0.0",
    description="Explica brevemente qué hace esto",
    author="OWNEX",
    icon="HeroIcon",
    capabilities=[
        Capability(
            domain="knowledge_manager",  # Dominio principal
            name="Knowledge Base",
            description="Gestionar bases de conocimiento",
        ),
    ],
    hooks={
        "before_validation": "nombre_de_extensión.hooks.before_validation",
    },
    dependencies=["core/event_bus", "core/storage"],
    providers=["nombre_de_extensión_provider"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
```

**4. Agregar connector.py**
El conector es la puerta de acceso real a la extensión.

```python
from core.interfaces.connector import ConnectorHealth, IConnector


class NombreDeExtensiónConnector(IConnector):
    connector_id = "extensión_nombre_de_extensión"
    app_id = "ownex"
    display_name = "Nombre Extensión"

    async def connect(self) -> bool:
        # Verificar solo si está instalada
        if not _EXTENSION_AVAILABLE:
            logger.warning("nombre_de_extensión no instalado")
            return False
        # Conectar realmente si está instalada
        return True

    async def query(self, params: dict) -> dict:
        # Implementar la lógica real aquí
        return {"result": "ejemplo", "status": "completado"}
```

**5. Agregar hooks.py (Opcional)**
Los hooks permiten reacciones automáticas a eventos del sistema.

```python
from core.extension.hooks import ExtensionHook


async def before_validation(data: dict) -> dict:
    """Ejecutar antes de validar something"""
    return {"validated_data": data, "hook_applied": True}


class NombreDeExtensiónHooks:
    before_validation = before_validation
```

### REQUISITOS MÍNIMOS

Cada extensión necesita al menos:
- `extensions/nombre_de_extensión/__init__.py`
- `extensions/nombre_de_extensión/manifest.py`
- `extensions/nombre_de_extensión/connector.py`

**OPCIONAL:** `extensions/nombre_de_extensión/hooks.py`

**OPCIONAL:** Scripts de configuración en `scripts/`

---

## FLUJO DE TRABAJO - Cómo Agregar una Nueva Extensión

### Paso 1: Planificación (5 minutos)

```bash
# Preguntarse a uno mismo: ¿necesitamos realmente esta extensión?
# ¿existe otra extensión que pueda hacer lo mismo?
# ¿necesitamos una nueva capacidad?
# ¿existe esta capacidad en otro lugar?
# ¿es esto realmente necesario para los usuarios?

# Si la respuesta es sí:
# 1. ¿qué hace exactamente esta extensión?
# 2. ¿qué necesita del sistema principal?
# 3. ¿qué habilidades necesita?
# 4. ¿qué datos maneja?
# 5. ¿cómo se comunica?
```

### Paso 2: Creación (15 minutos)

**CREAR FILES:**
```bash
mkdir -p extensions/nombre_de_extensión

cat > extensions/nombre_de_extensión/__init__.py << 'EOF'
# Copiar del ejemplo de arriba
EOF

cat > extensions/nombre_de_extensión/manifest.py << 'EOF'
# Copiar del ejemplo de arriba
EOF

cat > extensions/nombre_de_extensión/connector.py << 'EOF'
# Copiar del ejemplo de arriba
EOF
```

### Paso 3: Verificación (5 minutos)

**EJECUTAR VERIFICACIÓN:**
```bash
python3 verify_extensions.py
```

### Paso 4: Carga (2 minutos)

**CARGAR EXTENSION:**
```python
from core.extension.registry import get_extension_registry

reg = get_extension_registry()
if reg.load("nombre_de_extensión"):
    print("Extensión cargada exitosamente")
else:
    print("Error cargando extensión")
```

---

## UTILIZAR UNA EXTENSIÓN - Ejemplo Completo

### Ejemplo: Usar lightrag para Memoria Gráfica Conocimienton

```python
# 1. Cargar la extensión si no está cargada
from core.extension.registry import get_extension_registry

reg = get_extension_registry()
if "lightrag" not in reg.registry:
    if reg.load("lightrag"):
        print("✅ Cargando lightrag para memoria gráfica")
    else:
        print("❌ No se pudo cargar lightrag")

# 2. Conectar con la extensión
from extensions.lightrag.connector import LightRAGConnector

connector = LightRAGConnector()
await connector.connect()

# 3. Hacer una consulta
result = await connector.query({"query": "mis conocimientos más recientes sobre IA", "top_k": 5, "min_similarity": 0.7})

print(f"🔍 Resultados: {result}")

# 4. Insertar nuevo conocimiento
await connector.insert(
    {
        "text": "OWNEX usa lightrag para memoria gráfica con conocimiento",
        "metadata": {"source": "ejemplo", "timestamp": "2025-01-30"},
    }
)

# 5. Obtener estadísticas
stats = await connector.stats()
print(f"📊 Estadísticas: {stats}")
```

### EJEMPLO DE UTILIZACIÓN DE OTROS

```python
# Usar crawl4ai para scraping web
from extensions.crawl4ai.connector import Crawl4AIConnector

connector = Crawl4AIConnector()
await connector.connect()

# Hacer crawling de un sitio
result = await connector.crawl("https://ejemplo.com")
print(f"🕷️ Resultados del crawling: {result}")

# Obtener contenido del sitio
content = await connector.get_content("https://ejemplo.com")
print(f"📄 Contenido: {content[:200]}...")
```

---

## VERIFICAR TODO EL SISTEMA - Uso Diario

### Cada Mañana (2 minutos)

```bash
# Abrir terminal en proyectos/Rastro
cd /home/adrie/projects/Rastro

# Ver estado de todas las extensiones
.venv/bin/python verify_extensions.py
```

### Si Algo Está Mal

**Verificar Extensiones:**
```python
# Importar el registro completo
from core.extension.registry import get_extension_registry

reg = get_extension_registry()
discovered = reg.discover()
print(f"🔍 Extensiones descubiertas: {len(discovered)}")

# Verificar cada una individualmente
for ext_id in discovered:
    if reg.load(ext_id):
        print(f"✅ {ext_id}")
    else:
        print(f"❌ {ext_id}")
```

**Verificar Configuración del Sistema:**
```bash
# Verificar docker-compose
if [ -f "docker-compose.ownex.yml" ]; then
    echo "✅ docker-compose.ownex.yml existe"
    docker-compose -f docker-compose.ownex.yml ps
else
    echo "❌ docker-compose.ownex.yml faltante"
fi
```

**Verificar Servicios Clave:**
```python
# Verificar Kestra
import requests

try:
    response = requests.get("http://localhost:8080/api/v1/workspaces", timeout=5)
    print("✅ Kestra está funcionando")
except:
    print("❌ Kestra no está responding")
```

---

## MANTENIMIENTO Y SOLUCIÓN DE PROBLEMAS

### Problema Común: Extensión Cargada pero No Funciona

**DIAGNOSTICAR:**
```python
# 1. Verificar si está instalada
import importlib.util

spec = importlib.util.find_spec("lightrag")
print(f"lightrag disponible: {spec is not None}")

# 2. Verificar conexión
from extensions.lightrag.connector import LightRAGConnector

connector = LightRAGConnector()
print(f"Estado de conexión: {connector._connected}")

# 3. Verificar disponibilidad de la extensión
from core.extension.registry import get_extension_registry

reg = get_extension_registry()
print(f"Extensión en registro: {'lightrag' in [e.id for e in reg.registry]}")
```

**SOLUCIONAR:**
```bash
# Reinstalar la extensión faltante
pip install lightrag

# Recargar la extensión del sistema
.venv/bin/python -c "
from core.extension.registry import get_extension_registry
reg = get_extension_registry()
if reg.load('lightrag'):
    print('✅ lightrag recargada')
else:
    print('❌ falló la recarga')
"
```

### Problema Común: Error de Puertos

**DIAGNOSTICAR:**
```bash
# Verificar contenedores en ejecución
docker-compose -f docker-compose.ownex.yml ps

# Verificar puertos
netstat -tlnp | grep -E '(5678|8080|3000|4000)'
```

**SOLUCIONAR:**
```bash
# Reiniciar contenedores con limpieza
docker-compose -f docker-compose.ownex.yml down
docker-compose -f docker-compose.ownex.yml up -d
```

---

## DOCUMENTACIÓN DE REFERENCIA RÁPIDA

### Comandos Útiles Diariamente

```bash
# Estado completo del sistema
.venv/bin/python verify_extensions.py

# Cargar una extensión específica
.venv/bin/python -c "
from core.extension.registry import get_extension_registry
reg = get_extension_registry()
print('Cargando extensiones...')
for ext_id in reg.discover():
    reg.load(ext_id)
print('✅ Todos las extensiones cargadas')
"

# Verificar si una extensión está cargada
.venv/bin/python -c "
from core.extension.registry import get_extension_registry
reg = get_extension_registry()
print('lightrag cargado:', 'lightrag' in [e.id for e in reg.registry])
"
```

### Estructura de Archivos

```
extensions/
├── lightrag/
│   ├── __init__.py          # Control de disponibilidad de la extensión
│   ├── manifest.py          # Definición de capabilities de la extensión
│   ├── connector.py         # Puerta de acceso real a la extensión
│   └── hooks.py             # Respuestas automáticas a eventos
├── cognee/
├── graphiti/           # ... y 10 más
└── verify_extensions.py # Script de verificación

docker-compose.ownex.yml  # Servicios de orquestación
config/kestra.yml         # Configuración de Kestra
```

### Patrones Comunes

**Si una Extensión No Está Cargada:**
```python
# Primero verificar si está disponible
import importlib.util

if importlib.util.find_spec("lightrag"):
    # Si está disponible, intentar cargarla
    reg.load("lightrag")
else:
    # Si no está disponible, pedir al usuario instalarla
    print("Instalar con: pip install lightrag")
```

**Si una Extensión Está Cargada Pero No Funciona:**
```python
# Verificar errores de importación
import traceback

try:
    from extensions.lightrag.connector import LightRAGConnector

    connector = LightRAGConnector()
    await connector.connect()
except Exception as e:
    print("Error:", str(e))
    traceback.print_exc()
```

---

## APRENDE DE ESTO MAÑANA

### Lo Que Aprendiste

1. **Sistema de Extensiones Autónomas** - Cómo OWNEX carga e integra automáticamente 13+ extensiones OSS
2. **Patrón ExtensionManifest** - Cómo documentar exactamente qué hace cada extensión
3. **EventBus** - Cómo las extensiones se comunican entre sí sin problemas
4. **Verificación del Sistema** - Cómo mantener el sistema funcionando sin sorpresas

### Lo Que Puedes Hacer Mañana

- **Agregar una nueva extensión** rápidamente usando los templantes de README
- **Diagnosticar problemas** de extensiones con el enfoque sistemático de solución de problemas
- **Supervisar todo el sistema** en menos de 2 minutos con verify_extensions.py
- **Entender completamente** cómo funciona cada pieza del sistema gracias a la documentación exhaustiva

### Conceptos Clave

- **Extensiones como microservicios** - Cada extensión es una pieza independiente que funciona sola
- **Zero cabezas de conexión** - El sistema se conecta con extensiones automáticamente, no necesitas configurar nada manualmente
- **Desacoplamiento** - Las extensiones no necesitan saber cómo funcionan las otras para trabajar juntas
- **Transparencia** - Siempre sabes qué extensiones están cargadas, cuáles funcionan, cuáles tienen errores

---

## CHECKLIST DE REFERENCIA RÁPIDA

### ✅ Para Hoy (Si Acabas Ahora)
- [ ] Ver el estado de `verify_extensions.py`
- [ ] Verificar si las extensiones clave están cargadas (lightrag, crawl4ai, etc.)
- [ ] Tener un plan de acción si algo está roto

### ✅ Para Mañana (Si Tienes Tiempo)
- [ ] Agregar una nueva extensión usando los plantillas
- [ ] Probar que funciona la nueva extensión
- [ ] Escribir un script que use la nueva extensión
- [ ] Documentar qué hiciste y por qué

### ✅ Para la Semana (Si Tienes Más Tiempo)
- [ ] Integrar la nueva extensión con el flujo de trabajo principal
- [ ] Agregar pruebas de integración para la nueva extensión
- [ ] Documentar completamente el nuevo flujo de trabajo

---

## MISIÓN CUMPLIDA

✅ **Nunca ocultar decisiones** - TODO se documenta completamente
✅ **Explicar lo que estoy haciendo** - Cada acción tiene una explicación clara y simple
✅ **Mostrar mientras trabajo** - Verificación completa del estado disponible en cualquier momento
✅ **Enseñar después de terminar** - Documentación completa y ejemplos incluídos
✅ **Un niño de 10 años puede entender** - Lenguaje simple, ejemplos, sin jerga innecesaria
✅ **Sin cajas negras** - Complemento completo de disponibilidad, carga y uso de extensiones

**El sistema OWNEX es ahora completamente transparente, educador y fácil de mantener**.