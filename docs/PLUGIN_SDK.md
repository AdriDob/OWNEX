# ORION Plugin SDK — Creating Apps

> **API version**: `PLUGIN_API = "1.0"`

An **app** (also called a plugin) is a self-contained module under `apps/<name>/`
that extends ORION with new functionality: API routes, scheduler jobs,
EventBus handlers, widgets, and frontend views.

Apps are auto-discovered at boot via `AppRegistry.discover_extensions()`.

---

## 1. Minimal app structure

```
apps/hello/
├── __init__.py        # Package init
├── manifest.py        # App declaration
├── engine.py          # Business logic
└── api/
    └── routers.py     # Optional API endpoints
```

---

## 2. Manifest (`manifest.py`)

Every app needs a manifest declaring its identity and capabilities:

```python
from core.interfaces import IAppPlugin
from core.extension.manifest import AppManifest

class HelloApp(IAppPlugin):
    @property
    def manifest(self) -> AppManifest:
        return AppManifest(
            app_id="hello",
            name="Hello World",
            version="1.0.0",
            description="Example app",
            routers=["apps.hello.api.routers.router"],    # FastAPI routers (optional)
            scheduler_jobs=[],                             # Periodic jobs (optional)
            widgets=[],                                    # Dashboard widgets (optional)
            db_path="",                                    # SQLite path (optional, relative to ~/.orion/database/)
        )

registry.register(HelloApp())
```

### Manifest fields

| Field | Type | Required | Description |
|---|---|---|---|
| `app_id` | `str` | ✅ | Unique identifier. Used as namespace for events, settings, DB |
| `name` | `str` | ✅ | Human-readable name |
| `version` | `str` | ✅ | Semver |
| `description` | `str` | ✅ | Brief description |
| `routers` | `list[str]` | ❌ | Dot-path to FastAPI `APIRouter` instances |
| `scheduler_jobs` | `list[dict]` | ❌ | Periodic job definitions (see below) |
| `widgets` | `list[dict]` | ❌ | Dashboard KPI widgets (see below) |
| `db_path` | `str` | ❌ | SQLite filename. Stored in `~/.orion/database/<name>.db`. Table creation is app responsibility |

---

## 3. Scheduler jobs

A job is a periodic task that runs at a fixed interval:

```python
scheduler_jobs=[{
    "id": "hello_ping",
    "name": "Ping health check",
    "handler": "apps.hello.engine:ping_health",
    "interval": 3600,  # seconds
    "app_id": "hello",
}]
```

The handler is a dot-path to a callable: `"module.path:function_name"`.
Jobs are registered with `CoreScheduler` which fires `scheduler:job_due` events.

---

## 4. Widgets

A widget is a KPI card shown on the ORION Home dashboard:

```python
widgets=[{
    "id": "hello-greetings",
    "label": "Greetings Today",
    "value_endpoint": "/api/hello/stats",
    "value_path": "greetings_today",   # JSONPath to extract value
    "icon": "Bell",
    "category": "general",
}]
```

---

## 5. API routers

Create a `FastAPI APIRouter` and reference it in the manifest:

```python
# apps/hello/api/routers.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/hello", tags=["hello"])

@router.get("/greet")
async def greet(name: str = "world"):
    return {"message": f"Hello {name}!"}
```

Routers are auto-mounted at boot. Auth is inherited from the global
`AuthMiddleware` (CSRF + session).

---

## 6. EventBus integration

Apps communicate via `core/events/event_bus.py`:

```python
from core.events.event_bus import get_core_event_bus

bus = get_core_event_bus()

# Publish an event
bus.publish("hello:greeted", name="user")

# Subscribe to events
bus.subscribe("finding:created", my_handler)
```

### Event naming convention

Use `app_id:event_name` (e.g., `atlas:price:updated`, `odyssey:bet:settled`).

Events from ORION Core:
| Event | Payload | When |
|---|---|---|
| `system:startup` | `{}` | After full boot |
| `system:shutdown` | `{}` | Before shutdown |
| `scheduler:job_due` | `job_id`, `app_id` | When a scheduled job is due |
| `backup:created` | `backup_path`, `size` | After successful backup |
| `maintenance:completed` | `operation`, `dbs` | After maintenance cycle |

Events from CATEYE (legacy):
| Event | Payload | When |
|---|---|---|
| `finding:created` | `id`, `title`, `severity` | New finding detected |
| `finding:status_changed` | `id`, `old_status`, `new_status` | Finding confirmed/rejected |
| `report:generated` | `id`, `title`, `findings_count` | Report created |
| `opportunity:found` | `id`, `program`, `priority` | New opportunity |

---

## 7. Database

Each app gets its own SQLite database at `~/.orion/database/<app_id>.db`:

```python
# apps/hello/models.py
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Greeting(Base):
    __tablename__ = "greetings"
    id = Column(Integer, primary_key=True)
    name = Column(String)

# Create tables on startup
from core.database.manager import get_db_manager
dbm = get_db_manager()
engine = dbm.register("hello", f"hello.db")
Base.metadata.create_all(engine)
```

---

## 8. Hooks (Extension SDK)

For advanced use cases, apps can register lifecycle hooks:

```python
from core.extension.hooks import register_hook

def before_backup(context):
    """Called before every backup operation."""
    logger.info("App hello: preparing for backup")

register_hook("before", "backup:create", before_backup)
```

Available hook points:
- `before:backup:create`, `after:backup:create`
- `before:maintenance:full`, `after:maintenance:full`
- `before:system:startup`, `after:system:startup`
- `before:system:shutdown`, `after:system:shutdown`

---

## 9. Settings

Apps can expose settings via the unified settings system:

```python
# apps/hello/api/routers.py
from cores.settings.service import get_setting, set_setting

@router.get("/settings")
async def get_hello_settings():
    return {
        "greeting": get_setting("hello_greeting", "Hello"),
    }

@router.post("/settings")
async def update_hello_settings(greeting: str):
    set_setting("hello_greeting", greeting)
    return {"status": "ok"}
```

Settings are namespaced by `app_id` prefix.

---

## 10. Frontend integration

Add your Vue components under `frontend/src/apps/<name>/`:

```typescript
// frontend/src/router/index.ts
const routes = [
  {
    path: '/hello',
    name: 'hello-dashboard',
    component: () => import('@/apps/hello/HelloDashboard.vue'),
    meta: { title: 'Hello', icon: 'Bell' },
  },
]
```

Add a nav link in `AppSidebar.vue`:

```vue
<SidebarItem to="/hello" icon="Bell" label="Hello" />
```

---

## 11. Error isolation

If an app crashes at boot, ORION logs the error and continues:

```
[WARNING] App hello failed to load: module 'apps.hello.engine' not found
```

Apps never block system startup. An invalid app manifest logs a warning
and skips the app.

---

## 12. Complete example

See `extensions/hello/` for a minimal working extension with:
- Manifest with settings and hooks
- API endpoint
- EventBus integration

```bash
python run.py  # Auto-discovers extensions/hello/
curl http://localhost:8000/api/hello/greet?name=ORION
# {"message": "Hello ORION!"}
```

---

## 13. Version compatibility

| Plugin API | ORION version | Changes |
|---|---|---|
| `1.0` | `4.0.0+` | Initial |

Check compatibility at runtime:

```python
from core.version import PLUGIN_API
assert PLUGIN_API == "1.0", "Incompatible plugin API version"
```
