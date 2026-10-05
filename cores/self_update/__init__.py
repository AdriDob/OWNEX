"""Self-update subsystem (canonical public surface).

`cores/self_update/engine.py` and `cores/self_update/models.py` were deleted in
commit 50abfd1c (desktop / core→cores migration), but this package kept
re-exporting `SelfUpdateEngine`, `UpdateStatus`, `UpdateInfo` and
`UpdateResult` from them. Importing ANY name from `cores.self_update` therefore
raised ModuleNotFoundError — which silently killed every consumer of
`ProcessManager`:

  - `cores/recovery/engine.py::_action_restart_api` (the `restart_api_server`
    healing action could never run)
  - `api/routers/system.py` (the manual restart endpoint)

The real, working implementation is `system.py`
(`SelfUpdateSystem` / `get_self_update_system` / `ProcessManager` /
`GitUpdater` / `DependencyInstaller`). This package now re-exports it, so there
is exactly one self-update SSOT and the import path keeps working.
"""

from cores.self_update.system import (
    DependencyInstaller,
    GitUpdater,
    ProcessManager,
    SelfUpdateError,
    SelfUpdateSystem,
    get_self_update_system,
)

__all__ = [
    "SelfUpdateError",
    "SelfUpdateSystem",
    "get_self_update_system",
    "GitUpdater",
    "DependencyInstaller",
    "ProcessManager",
]
