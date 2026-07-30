# Mock update_system for now - will be replaced by actual implementation later
from types import SimpleNamespace

update_system = SimpleNamespace()
update_system.check_for_updates = lambda: (False, "No updates available")
update_system.perform_update = lambda: (False, "Update not supported in dev", "")
