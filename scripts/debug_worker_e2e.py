import asyncio
import logging

from cores.worker_core.orchestrator import WorkerCore
from cores.worker_core.models import WorkerConfig, WorkGoal, AutonomyLevel
from unittest.mock import AsyncMock, MagicMock

logging.basicConfig(level=logging.DEBUG)

async def run():
    config = WorkerConfig(autonomy_level=AutonomyLevel.FULL, test_mode=True, checkpoint_interval_seconds=3600, human_approval_required=False)
    goal = WorkGoal(description="Test goal", target_monthly_usd=10000, min_reward_usd=10, max_risk_score=0.9, active=True)

    # mock discovery
    mock_discovery = AsyncMock()
    opp = MagicMock()
    opp.id = "test_opp_001"
    opp.title = "Fix API endpoint bug"
    opp.platform = MagicMock(value="opire")
    opp.category = MagicMock(value="software_engineering")
    opp.payment = 100.0
    opp.estimated_time_hours = 2.0
    opp.risk_score = 0.2
    opp.acceptance_probability = 0.8
    opp.expected_value_usd_per_hour = 50.0
    opp.description = "Fix a bug in the API endpoint"
    mock_discovery.discover_all = AsyncMock(return_value=[opp])

    mock_evaluation = MagicMock()
    mock_evaluation.evaluate = MagicMock(return_value={
        "passed": True,
        "score": 0.85,
        "reasons": ["High EV", "Low risk"],
        "barrier_score": 15.0,
        "expected_value_usd_per_hour": 50.0,
        "acceptance_probability": 0.8,
        "compatibility_score": 0.9,
        "speed_score": 0.7,
        "reputation_score": 0.6,
        "risk_score": 0.2,
        "strict_filter_rejected": False,
        "strict_filter_reasons": [],
        "quality_gate_result": {"passed": True, "reason": "Evidence present"},
    })

    mock_execution = MagicMock()
    mock_execution.execute = MagicMock(return_value={
        "success": True,
        "artifacts": ["fix.py", "test_fix.py"],
        "evidence": ["Screenshot of fix", "Test output"],
        "output": "Bug fixed successfully",
        "error": None,
        "execution_time_s": 45.0,
    })

    mock_delivery = MagicMock()
    mock_delivery.deliver = MagicMock(return_value={
        "success": True,
        "submission_id": "sub_001",
        "submission_url": "https://opire.com/sub/001",
        "platform_response": {"status": "submitted"},
        "error": None,
    })

    mock_learning = MagicMock()
    mock_learning.learn = MagicMock(return_value={
        "success": True,
        "lessons": ["High EV opportunities work well"],
        "skill_updates": {"python": 0.1},
        "platform_updates": {"opire": 0.5},
        "category_updates": {"software_engineering": 0.3},
        "error": None,
    })

    wc = WorkerCore(config)
    wc.set_discovery_engine(mock_discovery)
    wc.set_evaluation_engine(mock_evaluation)
    wc.set_execution_engine(mock_execution)
    wc.set_delivery_engine(mock_delivery)
    wc.set_learning_engine(mock_learning)
    wc.set_goal(goal)

    try:
        await wc._run_cycle()
    except Exception as e:
        logging.exception('Run cycle failed')

    print('Work items:', list(wc.work_items.keys()))
    for wid, item in wc.work_items.items():
        print('WORK ITEM', wid)
        print('  phase:', item.phase)
        print('  state:', item.state)
        print('  checkpoints:')
        for cp in item.checkpoints:
            print('   -', cp)
        print('  artifacts:', item.artifacts)
        print('  evidence:', item.evidence)

if __name__ == '__main__':
    asyncio.run(run())
