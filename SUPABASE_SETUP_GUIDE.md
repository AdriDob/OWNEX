# Supabase Setup Guide — OWNEX OMEGA Cloud Sync

Guía paso a paso para configurar Supabase para sincronización en la nube de OWNEX OMEGA.

## ¿Qué es Supabase?

Supabase es una alternativa open source a Firebase que incluye:
- **PostgreSQL Database** — Base de datos relacional en la nube
- **Auth** — Sistema de autenticación completo
- **Realtime** — Sincronización en tiempo real vía WebSocket
- **Storage** — Almacenamiento de archivos
- **Edge Functions** — Funciones serverless

**Free Tier:** 100% gratis, sin límite de tiempo
- 500MB PostgreSQL
- 1GB Storage
- 2GB Bandwidth
- 2 Projects

---

## Paso 1: Crear Proyecto Supabase

1. Ve a https://supabase.com
2. Click en "Start your project"
3. Regístrate o login con GitHub
4. Click en "New Project"
5. Configura:
   - **Organization:** Crea una organización o usa la default
   - **Name:** `ownex-omega`
   - **Database Password:** Genera una contraseña segura (guárdala)
   - **Region:** Elige la región más cercana a ti
   - **Pricing Plan:** Free
6. Click en "Create new project"
7. Espera 1-2 minutos mientras se crea el proyecto

---

## Paso 2: Obtener Credenciales

1. Ve a tu proyecto en Supabase
2. Click en **Settings** (icono de engranaje)
3. Click en **API**
4. Copia:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_KEY`

---

## Paso 3: Configurar Environment Variables

1. Copia `.env.example` a `.env`:
```bash
cp .env.example .env
```

2. Edita `.env` y agrega tus credenciales de Supabase:
```env
# Supabase Configuration (Cloud Sync)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here
```

3. Guarda el archivo

---

## Paso 4: Ejecutar Schema SQL

1. Ve a tu proyecto en Supabase
2. Click en **SQL Editor** (icono de SQL)
3. Click en "New query"
4. Copia el contenido de `database/supabase_schema.sql`
5. Pega en el editor SQL
6. Click en "Run" (o Ctrl+Enter)
7. Verifica que todas las tablas se crearon exitosamente

---

## Paso 5: Verificar Tablas

1. Click en **Table Editor** (icono de tabla)
2. Verifica que estas tablas existen:
   - `tasks`
   - `goals`
   - `habits`
   - `habit_entries`
   - `daily_moods`
   - `pc_usage_sessions`

---

## Paso 6: Instalar Cliente Supabase

```bash
pip install supabase
```

---

## Paso 7: Probar Conexión

Crea un script de prueba `test_supabase.py`:

```python
from os import getenv
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = getenv("SUPABASE_URL")
supabase_key = getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("ERROR: Supabase credentials not configured in .env")
    exit(1)

try:
    client = create_client(supabase_url, supabase_key)
    print("✅ Supabase connection successful")

    # Test: Obtener lista de tablas
    response = client.table("tasks").select("*").limit(1).execute()
    print(f"✅ Can query 'tasks' table")

except Exception as e:
    print(f"❌ Error connecting to Supabase: {e}")
    exit(1)
```

Ejecuta:
```bash
python test_supabase.py
```

---

## Paso 8: Configurar Autenticación (Opcional)

Si quieres usar Supabase Auth en lugar del auth manual:

1. Ve a **Authentication** en Supabase
2. Click en **Providers**
3. Habilita **Email** provider
4. Configura:
   - **Confirm email:** Off (para desarrollo)
   - **Secure email change:** On
   - **Enable signup:** On

---

## Paso 9: Habilitar Realtime (Opcional)

Para sincronización en tiempo real:

1. Ve a **Database** en Supabase
2. Click en **Replication**
3. Habilita realtime para estas tablas:
   - `tasks`
   - `goals`
   - `habits`
   - `daily_moods`

---

## API Endpoints

Una vez configurado, OWNEX OMEGA expondrá estos endpoints:

### Sync Endpoints
- `POST /api/supabase/sync/task` — Sincronizar tarea
- `POST /api/supabase/sync/goal` — Sincronizar meta
- `POST /api/supabase/sync/habit` — Sincronizar hábito
- `POST /api/supabase/sync/daily_mood` — Sincronizar estado de ánimo

### Get Endpoints
- `GET /api/supabase/tasks/{user_id}` — Obtener tareas
- `GET /api/supabase/goals/{user_id}` — Obtener metas
- `GET /api/supabase/habits/{user_id}` — Obtener hábitos
- `GET /api/supabase/daily_moods/{user_id}` — Obtener estados de ánimo

---

## Uso desde Python

```python
from cores.supabase.sync_manager import get_supabase_sync_manager

# Obtener sync manager
sync_manager = get_supabase_sync_manager()

# Sincronizar tarea
task_data = {
    "task_id": "task-123",
    "title": "Complete project",
    "status": "in_progress",
    "priority": "high",
    "category": "work",
}
sync_manager.sync_task(user_id="user-123", task_data=task_data)

# Obtener tareas
tasks = sync_manager.get_user_tasks(user_id="user-123")
print(f"Tasks: {tasks}")
```

---

## Uso desde API

```bash
# Sincronizar tarea
curl -X POST http://localhost:8000/api/supabase/sync/task \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "task_data": {
      "task_id": "task-123",
      "title": "Complete project",
      "status": "in_progress"
    }
  }'

# Obtener tareas
curl http://localhost:8000/api/supabase/tasks/user-123
```

---

## Seguridad

**Row Level Security (RLS):**
- Las tablas tienen RLS habilitado
- Los usuarios solo pueden ver/editar sus propios datos
- `auth.uid()` se usa para validar ownership

**Environment Variables:**
- NUNCA commit `.env` a git
- `.env` está en `.gitignore`
- Usa `.env.example` como template

---

## Troubleshooting

### Error: "Supabase not configured"
**Solución:** Configura `SUPABASE_URL` y `SUPABASE_KEY` en `.env`

### Error: "Failed to sync task"
**Solución:** Verifica que la tabla `tasks` existe en Supabase

### Error: "Invalid credentials"
**Solución:** Verifica que `SUPABASE_URL` y `SUPABASE_KEY` son correctos

### Error: "Table does not exist"
**Solución:** Ejecuta el schema SQL en Supabase SQL Editor

---

## Costos

**Free Tier (Permanente):**
- 500MB PostgreSQL
- 1GB Storage
- 2GB Bandwidth
- 2 Projects
- 100% gratis

**Pro Tier (opcional):**
- $25/mes
- 8GB PostgreSQL
- 100GB Storage
- 50GB Bandwidth
- Para cuando necesites más

---

## Referencias

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Python Client](https://supabase.com/docs/reference/python)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Preguntas?** Revisa la documentación de Supabase o crea un issue en el repo.
