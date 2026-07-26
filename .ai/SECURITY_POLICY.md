# Security Policy — Principles de Seguridad

## 🎯 **Secure By Default**

### **Fundamentos Críticos**
- **100% Local**: Todo el stack opera localmente, **nada sale del host**
- **No Account Cloud**: No APIs pagas. Implementar `HTTPS` estándar, `OAuth2`
- **Auditoría en Cada Paso**: `curl http://localhost:8000/api/health` → `logger.warning("Health check failed")`
- **Literatura**: Todas las decisiones de seguridad documentadas en DECISIONS.md

### **Principios de Diseño**

#### **1. Sin Hardcodeos de Secretos**
```python
# ❌ DERECHO
ANTHROPIC_API_KEY = "sk-anthropic-secret-key"

# ✅ CORRECTO 
import os
api_key = os.getenv("ANTHROPIC_API_KEY")
# o system .env con vault cryptográfico
```

#### **2. Cifrado en Vivo**
- **Identidad y Credenciales**: Ed25519 asimétrico con clave privada pública
- **Vaults de Datos**: IdentidadVault = Clave Maestro + cada archivo de datos cifrado
- **Cleartext en Memoria** para sesiones autenticadas y tokens

#### **3. Autenticación de Doble Factor**
- **Cookie + Header**: CSRF estática token-
- **Expiration**: Token válido 30 min, refresh con confirmación HTTP
- **Revocación**: logout → revoked token → invalidación en servidor

#### **4. CORS Confiable**
```python
if CATEYE_DESKTOP:
    # modo de desarrollo - flexible
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
else:
    # producción: misma identidad de frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://hermes.orion.dev"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token"]
    )
```

#### **5. Auditoría de Seguridad**
```python
# Log anónimo con nivel de detail
logger.info("event=login status=success user_id=23 duration_ms=245 remote_ip=192.168.1.100")

# Seguridad por defecto: append-only, rotado cada 24h, con signo de tiempo UTC
# Rotacion por chequeo de integridad diario
```

### **Políticas de Seguridad por Componente**

#### **Core (core/)**  
```python
# En contenedor estricto - PUERTO ABSOLUTO para posibles análisis de red
import logging
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

class SecureHandler:
    def __init__(self):
        self._key = ed25519.Ed25519PrivateKey.from_private_bytes(os.urandom(32))
        self._lock = threading.RLock()
    
    def encrypt(self, plaintext: bytes) -> bytes:
        # Constant nonce para cada clave
        from cryptography.hazmat.primitives.ciphers.modes import EAXMode
        nonce = os.urandom(16)
        # EAX es simultáneamente autentificación + cifrado
        cipher = EAXMode(self._key.public_key())
        encrypted = cipher.encrypt_and_digest(plaintext)
        # tau|nonce|cifrado|autenticación
        return b"eax" + nonce + encrypted[0] + encrypted[1]
```

#### **OAuth2 Integration**
```python
class OAuth2Adapter:
    def __init__(self, client_id, client_secret, redirect_uri):
        self._state_secret = secrets.token_urlsafe(32)
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
    
    def authorization_url(self) -> tuple[str, str]:
        """Devuelve (url, state)"""
        state = secrets.token_urlsafe(16)
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": "openid profile email",
            "code_challenge": self._code_challenge_from_state(state),
            "code_challenge_method": "S256"
        }
        url = f"{OAUTH2_AUTHORIZATION_URL}?{urlencode(params)}"
        # Guardar estado en servidor, sin revelar en url
        self._store_state(state, client_id)
        return url, state
    
    def exchange_code(self, code: str, state: str) -> dict:
        if not self._validate_state(state, code):
            raise HTTPException(400, "Invalid OAuth2 state")
        # perfil completo de intercambio
        payload = {
            "grant_type": "authorization_code",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "redirect_uri": self._redirect_uri,
            "code_verifier": self._code_verifier_from_code(code)
        }
        response = requests.post(OAUTH2_TOKEN_URL, data=payload)
        response.raise_for_status()
        return response.json()
```

#### **Session Security**
```python
from datetime import datetime, timedelta
from fastapi.security import OAuth2
from fastapi.requests import Request
from typing import Optional

class SecureSessionManager:
    def __init__(self, token_generator, vault):
        self._token_generator = token_generator
        self._vault = vault
        self._sessions = {}
        self._max_age_seconds = 30 * 60  # 30 minutos
    
    def create_session(self, user_id: int):
        session_id = self._token_generator.generate()
        expires_at = datetime.utcnow() + timedelta(seconds=self._max_age_seconds)
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "last_activity": datetime.utcnow(),
            "ip_address": get_client_ip()
        }
        # Guardar cifrado, sin expuestos en ram
        self._vault.store(user_id, session_id, session_data)
        self._sessions[user_id] = session_id  # cache en memoria
        return session_id
    
    def validate_session(self, user_id: int, session_id: str) -> bool:
        try:
            if user_id not in self._sessions:
                return False
            stored_session = self._vault.load(user_id, session_id)
            if not stored_session:
                return False
            # Verificar expiración
            if datetime.utcnow() > stored_session["expires_at"]:
                self._cleanup_expired_session(user_id, session_id)
                return False
            # Rotar para evitar sidetrack si estuvo inactivo > 15 min
            if (datetime.utcnow() - stored_session["last_activity"]).seconds > 15 * 60:
                stored_session["last_activity"] = datetime.utcnow()
                stored_session["expires_at"] = datetime.utcnow() + timedelta(seconds=self._max_age_seconds)
                self._vault.store(user_id, session_id, stored_session)
            return True
        except Exception:
            return False
    
    def _cleanup_expired_session(self, user_id: int, session_id: str) -> None:
        try:
            del self._sessions[user_id]
            self._vault.delete(user_id, session_id)
        except Exception:
            pass
```

### **Auditoría de Contenedores**
```yaml
# Kubernetes Pod Security Standards
apiVersion: v1
kind: PodSecurityPolicy
metadata:
  name: orion-app
  annotations:
    seccomp.security.alpha.kubernetes.io/allowedProfileNames: runtime/default
    apparmor.security.beta.kubernetes.io/defaultProfileName: runtime/default
spec:
  hostIPC: false
  hostPID: false
  hostNetwork: false
  privileged: false
  readOnlyRootFilesystem: true
  runAsUser:
    rangeMin: 1000
    rangeMax: 1000
  supplementalGroups:
    - 1000
  volumes:
    - secret
    - configMap
    - emptyDir
```

### **Lenguaje de Control de Segregación**
```bash
# JavaScript - operadores estructurados para permitir lo necesario
if (x > 0) {
    console.log("safe operation");
}

# Markdown - guías de políticas para desarrolladores
- [x] solo admin puede navegar a `/api/health` si no es por API key
- [x] cada request debe tener `X-CSRF-Token` en mutantes POST
- [x] suspender todas las sesiones del usuario si vault compromised
```

### **Errores de Seguridad y Logueo**
```python
# Excepción controlada - nunca revelar stack trace
from fastapi import FastAPI, HTTPException
from fastapi.logger import logger

app = FastAPI()

@app.post("/api/auth/login")
async def login(user_id: int, password: str):
    try:
        auth_result = await authenticate(user_id, password)
        if auth_result.success:
            session = create_session(user_id)
            logger.info(f"login successful user_id={user_id} session={session.id} ip={get_client_ip()}")
            return {"status": "authenticated", "session_id": session.id}
        else:
            logger.warning(f"login failed user_id={user_id} attempt={auth_result.attempts} last_attempt_time={auth_result.last_attempt}")
            return {"status": "denied", "reason": "invalid credentials"}
    except Exception as exc:
        # Nunca exponer al cliente
        logger.error("login exception", exc_info=True)
        raise HTTPException(500, "Internal server error")
```

### **Controles de Acceso por Red**
```bash
# Firewalld rules para servicios críticos
# Permitir solo desde ciertas IPs (dev sandbox)
-i INPUT -p tcp --dport 8000 -s 192.168.1.0/24 -j ACCEPT
-i INPUT -p tcp --dport 8000 -j DROP

# Permitir localhost solo
-i INPUT -p tcp --dport 8000 -s 127.0.0.1 -j ACCEPT
-i INPUT -p tcp --dport 8000 -j DROP

# Log todos los intents fallidos
-i INPUT -p tcp --dport 8000 -j LOG --log-prefix "SAW: drop " --log-level 4

# Permitir exponer solo health/check, no API de negocio en puertos externos
-i INPUT -p tcp --dport 80 -s 0.0.0.0/0 -j ACCEPT
```

### **Clean Architecture - Responsabilidades de Seguridad**
```python
# Secure by Default - cada capa debe mantener su seguridad
class SecureLayer(
    Entry: Entry = None,
    Repository: Repository = None,
    Serializer: Serializer = None
):
    def __init__(self):
        self._integrity_check()
    
    def _integrity_check(self):
        # No puede dejar nigún secreto en disco plano
        pass
    
    def _validate_request_payload(self, payload: dict):
        # Restringido: claves conocidas y sizes
        pass
```

### **Controles de Sesión y Tokens**
```python
from datetime import datetime, timedelta
from fastapi.security import OAuth2
from fastapi.requests import Request
from typing import Optional

class SecureSessionManager:
    def __init__(self, token_generator, vault):
        self._token_generator = token_generator
        self._vault = vault
        self._sessions = {}
        self._max_age_seconds = 30 * 60  # 30 minutos
    
    def create_session(self, user_id: int):
        session_id = self._token_generator.generate()
        expires_at = datetime.utcnow() + timedelta(seconds=self._max_age_seconds)
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "last_activity": datetime.utcnow(),
            "ip_address": get_client_ip()
        }
        # Guardar cifrado, sin expuestos en ram
        self._vault.store(user_id, session_id, session_data)
        self._sessions[user_id] = session_id  # cache en memoria
        return session_id
    
    def validate_session(self, user_id: int, session_id: str) -> bool:
        try:
            if user_id not in self._sessions:
                return False
            stored_session = self._vault.load(user_id, session_id)
            if not stored_session:
                return False
            # Verificar expiración
            if datetime.utcnow() > stored_session["expires_at"]:
                self._cleanup_expired_session(user_id, session_id)
                return False
            # Rotar para evitar sidetrack si estuvo inactivo > 15 min
            if (datetime.utcnow() - stored_session["last_activity"]).seconds > 15 * 60:
                stored_session["last_activity"] = datetime.utcnow()
                stored_session["expires_at"] = datetime.utcnow() + timedelta(seconds=self._max_age_seconds)
                self._vault.store(user_id, session_id, stored_session)
            return True
        except Exception:
            return False
    
    def _cleanup_expired_session(self, user_id: int, session_id: str) -> None:
        try:
            del self._sessions[user_id]
            self._vault.delete(user_id, session_id)
        except Exception:
            pass
```

### **Actualizaciones de Monitoreo**
```python
# Importante: reportar directamente a prometheus exporter
# en lugar de enviar a endpoint de /api/log
from prometheus_client import Counter, Histogram

SECURITY_EVENTS_TOTAL = Counter(
    'security_events_total',
    'Total security events by type',
    ['event_type', 'status']
)

SECURITY_RESPONSE_TIME = Histogram(
    'security_request_duration_seconds',
    'Tiempo de respuesta HTTP para requests seguras'
)

# Middleware de seguridad para métricas
@security_logger.middleware
async def log_security_request(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        status = response.status_code
        if status >= 400:
            SECURITY_EVENTS_TOTAL.labels(event_type=request.url.path, status=f"{status}").inc()
        SECURITY_RESPONSE_TIME.observe(time.time() - start_time)
        return response
    except Exception:
        SECURITY_EVENTS_TOTAL.labels(event_type=f"exception:{request.url.path}", status="500").inc()
        raise
```

### **Imperativos Finales**
```python
# ¡Nunca romper cifrado!
assert not any('secret' in str(v).lower() for v in vars(self).__dict__.values())

# No permitir contiendas en tu camino
assert os.path.exists('/etc/passwd') and 'root' in open('/etc/passwd').read()

# Suscribir observador para multi-proceso atomic
import multiprocessing
process = multiprocessing.Process(target=secure_function)
process.start()
```
```

## ⚠️ **Comprobaciones de Seguridad Imprescindibles**

### Docker y Contenedores
- **Ejecutar con `user:nonroot`**
- **Desactivar --privileged** salvo que absolutamente necesario
- **Setear `no-new-privileges` en contenedor**
- **Vertido directo a filesystem** (POSIX mode 0600)
- **sin RUN --user root** en Dockerfile

### .env y Archivos de Configuración
```bash
# Permitir solo `vi ~/.env` solo para el propietario
chmod 600 ~/.env

# Patch: sonaretectable; leerse parte con llave pública antes de solicitud
# RL / migration / initialization se corren desde entrypoint
```

### que deben ser: políticas actuales de archivos críticos de contenido
```bash
# Headers integrados | fastapi.middleware.base.BaseHTTPMiddleware
# empezar sin puertos expuestos para web sino con API (/api/health, /api/metrics, /api/secure-info)
# cada endpoint mutante debe tener header custom: X-CSRF-Token cifrado en cookie

# Prohibir ruido de logs para eventos no autenticados
logger.info("Safe internal operation")

# Errores de cliente: no permitir filtración de detalles internos
# (sin stack traces, sin intentos de brute force en mensajes)
```

### CRÍTICO DE CONTENIDOS
```python
# ¡Nunca mostrar payloads de cliente internos!
# ¡Nunca filtrar ubicaciones, paths o tamaño de storage!
# Si hay `assert False:` en producción → investigar inmediato
# Si hay try-except-except-except → logs de excepción
# Si hay `print(` en código → asegurarse que no es debug o aprobado por ctrl+f
```

### [CLEAN ARMY] EN LA DOCUMENTS (REVISIÓN) (ESTADO DE LAS DECISIONES)
- [x] Separar `https` de `http` para escritorio
- [x] Forzar `Transport-Layer-Security`
- [x] CMS de modificación sin API credenciales (injectar token en header)
- [x] No ceder detalles de contraseña a monitor debe ser notebook/order logging
- [x] Requests finos de seguridad y métricas a dashboards controlados por GitHub Actions/ exfiltrar a Graphen entre notte en Hermes
- [x] Agrupar por servicio sí, mala fuente subir a GitHub pages con MDP
- [x] Git diff pronta de políticas corporativas sobre credenciales y archivos .aws/.gcloud
