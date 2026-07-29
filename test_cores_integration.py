"""
Test de integración: Knowledge + Operations + Decision + Observability
"""

from datetime import datetime, timedelta

from cores.decision_core import BayesianBandit, DecisionEngine, DecisionPolicy, RiskProfile, default_decision_context
from cores.knowledge_core import KnowledgeGraph, OutcomeType, TaskOutcome, TaskType
from cores.observability_core import ExecutionTracker, MetricsCollector
from cores.operations_core import OperationsResearchEngine, TaskPriority, create_candidate, create_default_budget


def test_knowledge_core():
    print("=== Testing Knowledge Core ===")
    kg = KnowledgeGraph("~/.ownex/test_knowledge.db")

    # Simular algunas ejecuciones
    outcomes = [
        TaskOutcome(
            task_id="task_001",
            task_type=TaskType.SCAN,
            platform="hackerone",
            agent="opencode",
            started_at=datetime.utcnow() - timedelta(hours=2),
            completed_at=datetime.utcnow() - timedelta(hours=1.5),
            duration_seconds=1800,
            cost_usd=2.50,
            outcome=OutcomeType.SUCCESS,
            result_data={"vulns_found": 3},
            reward_usd=500.0,
            confidence=0.8,
        ),
        TaskOutcome(
            task_id="task_002",
            task_type=TaskType.EXPLOIT,
            platform="hackerone",
            agent="hermes",
            started_at=datetime.utcnow() - timedelta(hours=1),
            completed_at=datetime.utcnow() - timedelta(minutes=30),
            duration_seconds=1800,
            cost_usd=5.00,
            outcome=OutcomeType.SUCCESS,
            result_data={"vulns_found": 1, "critical": True},
            reward_usd=2000.0,
            confidence=0.6,
        ),
        TaskOutcome(
            task_id="task_003",
            task_type=TaskType.RECON,
            platform="bugcrowd",
            agent="fcc",
            started_at=datetime.utcnow() - timedelta(minutes=45),
            completed_at=datetime.utcnow() - timedelta(minutes=15),
            duration_seconds=1800,
            cost_usd=1.00,
            outcome=OutcomeType.FAILURE,
            result_data={},
            reward_usd=0.0,
            confidence=0.7,
            failure_reason="rate_limited",
        ),
    ]

    for o in outcomes:
        kg.record_outcome(o)

    # Verificar aprendizaje
    plat = kg.get_platform_expertise("hackerone")
    print(f"HackerOne expertise: {plat.total_tasks} tasks, ${plat.total_reward:.2f} reward, ROI: {plat.roi:.2f}")

    agent = kg.get_agent_profile("opencode")
    print(f"OpenCode profile: {agent.total_tasks} tasks, efficiency: {agent.efficiency:.2f}")

    best_agent = kg.get_best_agent_for("hackerone", TaskType.SCAN)
    print(f"Best agent for hackerone/scan: {best_agent}")

    ev = kg.get_expected_value("hackerone", "opencode", TaskType.SCAN)
    print(f"Expected value: ${ev:.2f}/hr")

    print("✓ Knowledge Core working\n")
    return kg


def test_operations_core(kg):
    print("=== Testing Operations Core ===")
    engine = OperationsResearchEngine(kg)

    # Crear candidatos
    candidates = [
        create_candidate(
            "scan_001", TaskType.SCAN, "hackerone", "Scan new program", 30, 2.0, 500, 0.8, TaskPriority.HIGH
        ),
        create_candidate(
            "exploit_001",
            TaskType.EXPLOIT,
            "hackerone",
            "Exploit found vuln",
            60,
            5.0,
            2000,
            0.6,
            TaskPriority.CRITICAL,
        ),
        create_candidate(
            "recon_001", TaskType.RECON, "bugcrowd", "Recon new target", 20, 1.0, 100, 0.7, TaskPriority.MEDIUM
        ),
        create_candidate("report_001", TaskType.REPORT, "hackerone", "Write report", 45, 0.5, 0, 0.9, TaskPriority.LOW),
    ]

    budget = create_default_budget(max_hours=4, max_cost=20, max_parallel=2)
    schedule = engine.plan(budget, candidates)

    print(f"Scheduled {len(schedule)} tasks:")
    for s in schedule:
        print(
            f"  {s.candidate.task_id} -> {s.assigned_agent} @ {s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')} (EV: ${s.expected_value:.2f})"
        )

    # Simular ejecución
    outcomes = engine.execute_plan(schedule)
    print(f"Executed {len(outcomes)} tasks")

    stats = engine.get_utilization_stats()
    print(f"Stats: {stats}")

    print("✓ Operations Core working\n")
    return engine


def test_decision_core(kg):
    print("=== Testing Decision Core ===")
    engine = DecisionEngine(kg)

    candidates = [
        create_candidate("task_a", TaskType.SCAN, "hackerone", "High value scan", 30, 2.0, 500, 0.8, TaskPriority.HIGH),
        create_candidate(
            "task_b", TaskType.EXPLOIT, "hackerone", "Critical exploit", 60, 10.0, 5000, 0.4, TaskPriority.CRITICAL
        ),
        create_candidate("task_c", TaskType.RECON, "bugcrowd", "Routine recon", 20, 1.0, 50, 0.9, TaskPriority.LOW),
    ]

    context = default_decision_context(candidates, budget=15.0, hours=2.0)
    context.policy = DecisionPolicy.MAX_EXPECTED_UTILITY
    context.risk_profile = RiskProfile.BALANCED

    decision = engine.decide(context)

    print(f"Decision: {decision.selected_task.task_id if decision.selected_task else 'None'}")
    print(f"Agent: {decision.selected_agent}")
    print(f"Expected Value: ${decision.expected_value:.2f}")
    print(f"Confidence: {decision.confidence:.1%}")
    print(f"Rationale: {decision.rationale}")
    print(f"Alternatives: {[(a.task_id, ag, f'${ev:.2f}') for a, ag, ev in decision.alternatives]}")

    # Test bandit
    bandit = BayesianBandit(kg)
    arms = [
        ("hackerone", TaskType.SCAN, "opencode"),
        ("hackerone", TaskType.EXPLOIT, "hermes"),
        ("bugcrowd", TaskType.RECON, "fcc"),
    ]
    chosen = bandit.thompson_sample(arms)
    print(f"Thompson sample chose: {chosen}")

    print("✓ Decision Core working\n")
    return engine


def test_observability_core():
    print("=== Testing Observability Core ===")
    collector = MetricsCollector("~/.ownex/test_obs.db")
    tracker = ExecutionTracker(collector)

    # Test context manager tracking
    with tracker.track("opencode", "test_task_001", "scan", "hackerone") as exec:
        exec.cost_usd = 1.50
        exec.tokens_used = 5000
        exec.api_calls = 10
        exec.findings_count = 2
        exec.findings_validated = 2
        exec.evidence_quality_score = 0.9
        # Simular trabajo
        import time

        time.sleep(0.1)

    # Test manual tracking
    exec2 = tracker.start_execution("hermes", "test_task_002", "exploit", "hackerone")
    exec2.cost_usd = 3.00
    exec2.tokens_used = 15000
    exec2.api_calls = 25
    time.sleep(0.05)
    tracker.complete_execution(exec2, "success", reward=1500.0)

    # Test failure tracking
    exec3 = tracker.start_execution("fcc", "test_task_003", "recon", "bugcrowd")
    exec3.cost_usd = 0.50
    time.sleep(0.02)
    tracker.complete_execution(exec3, "failure", error="rate_limited", category="api_error")

    # Ver stats
    stats = collector.get_execution_stats(hours=1)
    print(f"Execution stats: {stats}")

    comparison = collector.get_agent_comparison(hours=1)
    print(f"Agent comparison: {list(comparison.keys())}")

    errors = collector.get_error_analysis(hours=24)
    print(f"Error analysis: {errors['total_errors']} errors")

    print("✓ Observability Core working\n")
    return collector


def test_integrated_flow():
    print("=== Testing Integrated Flow ===")

    # 1. Knowledge acumula experiencia
    kg = KnowledgeGraph("~/.ownex/integrated_test.db")

    # 2. Decision engine usa knowledge para elegir
    decision_engine = DecisionEngine(kg)

    # 3. Operations engine planifica
    ops_engine = OperationsResearchEngine(kg)

    # 4. Observability registra todo
    collector = MetricsCollector("~/.ownex/integrated_obs.db")
    tracker = ExecutionTracker(collector)

    # Simular ciclo completo
    for cycle in range(3):
        print(f"\n--- Cycle {cycle + 1} ---")

        # Generar candidatos basados en oportunidades detectadas
        candidates = [
            create_candidate(f"scan_{cycle}_a", TaskType.SCAN, "hackerone", f"Scan cycle {cycle}", 30, 2.0, 300, 0.7),
            create_candidate(
                f"exploit_{cycle}_a",
                TaskType.EXPLOIT,
                "hackerone",
                f"Exploit cycle {cycle}",
                45,
                5.0,
                1000,
                0.5,
                TaskPriority.HIGH,
            ),
            create_candidate(f"recon_{cycle}_a", TaskType.RECON, "bugcrowd", f"Recon cycle {cycle}", 20, 1.0, 50, 0.8),
        ]

        # Decision engine elige
        context = default_decision_context(candidates, budget=20, hours=2)
        decision = decision_engine.decide(context)
        print(
            f"Decision: {decision.selected_task.task_id} with {decision.selected_agent} (EV: ${decision.expected_value:.2f})"
        )

        # Operations planifica (solo la elegida + otras factibles)
        budget = create_default_budget(max_hours=2, max_cost=20, max_parallel=2)
        schedule = ops_engine.plan(budget, candidates)
        print(f"Scheduled: {[s.candidate.task_id for s in schedule]}")

        # Ejecutar con observabilidad
        for scheduled in schedule:
            with tracker.track(
                scheduled.assigned_agent,
                scheduled.candidate.task_id,
                scheduled.candidate.task_type.value,
                scheduled.candidate.platform,
            ) as exec:
                exec.cost_usd = scheduled.candidate.estimated_cost
                # Simular resultado
                import random

                success = random.random() < scheduled.candidate.confidence
                reward = scheduled.candidate.estimated_reward if success else 0
                exec.reward_usd = reward
                if success:
                    exec.findings_count = random.randint(1, 3)
                    exec.findings_validated = exec.findings_count
                exec.complete("success" if success else "failure", reward=reward)

                # Actualizar knowledge y decision engines con resultado real
                from cores.knowledge_core import OutcomeType, TaskOutcome

                outcome = TaskOutcome(
                    task_id=exec.task_id,
                    task_type=TaskType(exec.task_type),
                    platform=exec.platform,
                    agent=exec.agent,
                    started_at=exec.started_at,
                    completed_at=exec.completed_at,
                    duration_seconds=exec.duration_seconds,
                    cost_usd=exec.cost_usd,
                    outcome=OutcomeType.SUCCESS if success else OutcomeType.FAILURE,
                    result_data={},
                    reward_usd=reward,
                    confidence=scheduled.candidate.confidence,
                )
                kg.record_outcome(outcome)
                decision_engine.update_belief(outcome)

        # Stats del ciclo
        stats = collector.get_execution_stats(hours=1)
        print(f"Cycle stats: {stats['total']} tasks, ${stats['net_profit']:.2f} profit, ROI: {stats['roi']:.2f}")

    # Verificar aprendizaje acumulado
    print("\n--- Accumulated Knowledge ---")
    plat = kg.get_platform_expertise("hackerone")
    print(f"HackerOne: {plat.total_tasks} tasks, ${plat.total_reward:.2f} reward, {plat.success_rate:.1%} success")

    agent = kg.get_agent_profile("opencode")
    print(f"OpenCode: {agent.total_tasks} tasks, efficiency: {agent.efficiency:.2f}")

    decision_stats = decision_engine.get_decision_stats()
    print(f"Decisions: {decision_stats}")

    print("✓ Integrated flow working\n")


if __name__ == "__main__":
    # Test individual cores
    kg = test_knowledge_core()
    test_operations_core(kg)
    test_decision_core(kg)
    test_observability_core()

    # Test flujo integrado
    test_integrated_flow()

    print("=== ALL TESTS PASSED ===")
