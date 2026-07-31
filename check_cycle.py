from core.cycles.models import Cycle
from core.database.manager import get_db_manager

mgr = get_db_manager()
mgr.register("cycles", "cycles.db")
db = mgr.get_session("cycles")
cycles = db.query(Cycle).filter(Cycle.slug == "security").all()
print(f"Found {len(cycles)} security cycles")
for c in cycles:
    print(f"  id={c.id}, name={c.name}, slug={c.slug}, category={c.category}, status={c.status}")
