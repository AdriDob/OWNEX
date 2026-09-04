from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db import Base
from cores.worker_core.persistence import save_checkpoint, get_latest_checkpoint, resume_from, get_active_work_items
from cores.worker_core.orchestrator import WorkerCore
from cores.worker_core.models import WorkPhase


def test_checkpoint_resume_and_rehydrate():
    # Setup in-memory SQLite and session
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    work_id = "resume-w1"

    # Save a checkpoint at 'evaluate' and mark completed -> resume should be 'select'
    save_checkpoint(work_id, "evaluate", {"estimated_reward_usd": 123.0}, work_item_title="T", work_item_platform="p", work_item_category="c", phase_completed=True, session=session)

    cp = get_latest_checkpoint(work_id, session=session)
    assert cp is not None

    next_phase = resume_from(cp)
    assert next_phase == "select"

    # Monkeypatch persistence accessors used by WorkerCore.resume_open_work_items/_rehydrate
    import cores.worker_core.persistence as persistence

    orig_get_active = persistence.get_active_work_items
    orig_get_latest = persistence.get_latest_checkpoint
    try:
        persistence.get_active_work_items = lambda session=None: [work_id]
        persistence.get_latest_checkpoint = lambda wid, session=None: cp

        core = WorkerCore()
        resumed = core.resume_open_work_items()
        assert resumed == [(work_id, "select")]

        # Rehydrate into WorkerCore and verify phase set
        core._rehydrate_work_item(work_id, "select")
        assert work_id in core.work_items
        item = core.work_items[work_id]
        assert item.phase.value == "select"
        # Check that persisted scalar was applied
        assert getattr(item, "estimated_reward_usd", None) == 123.0

    finally:
        persistence.get_active_work_items = orig_get_active
        persistence.get_latest_checkpoint = orig_get_latest
