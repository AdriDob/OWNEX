from core.database.manager import get_db_manager
from core.cycles.models import Cycle

mgr = get_db_manager()
mgr.register("cycles", "cycles.db")
db = mgr.get_session("cycles")
cycles = db.query(Cycle).filter(Cycle.slug == "security").all()
print(f"Found {len(cycles)} security cycles")
for c in cycles:
    print(f"  Before: id={c.id}, category={c.category}")
    c.category = "security"
    db.commit()
    print(f"  After:  id={c.id}, category={c.category}")