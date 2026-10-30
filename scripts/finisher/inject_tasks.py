#!/usr/bin/env python3
"""Inject real OWNEX completion tasks into the Finisher."""

import sys
from collections import Counter

sys.path.insert(0, "/home/adriel/projects/Rastro")

from scripts.finisher.state import AcceptanceCriteria, Task, state_manager

state = state_manager.get_state()

# Clear existing demo tasks
state.tasks.clear()

real_tasks = [
    # PHASE 1: AUDIT & BASELINE (already verified)
    Task(
        id="AUDIT-001",
        title="Verify test-fast baseline 103/1",
        description="Confirm test-fast gate passes (scoring, opportunity, scheduler jobs)",
        phase="audit",
        priority=1,
        area="testing",
        weight=2.0,
        verification_commands=[
            "python scripts/dev test-fast",
        ],
        acceptance_criteria=[],
    ),
    Task(
        id="AUDIT-002",
        title="Check current blockers from KNOWN_DEBT",
        description="Review KNOWN_DEBT.md for P0/P1 items blocking OWNEX completion",
        phase="audit",
        priority=1,
        area="architecture",
        weight=1.5,
        verification_commands=[
            "grep -c 'P0\\|P1' .ai/KNOWN_DEBT.md",
        ],
        acceptance_criteria=[],
    ),
    # PHASE 2: CRITICAL FIXES (P0 from KNOWN_DEBT)
    Task(
        id="FIX-001",
        title="Fix auth bypass on root-mounted routes (KNOWN_DEBT #32)",
        description="Extend auth middleware to cover 28 root-mounted namespaces with 264 routes (148 mutating)",
        phase="fix",
        priority=1,
        area="security",
        weight=3.0,
        dependencies=["AUDIT-001", "AUDIT-002"],
        verification_commands=[
            "grep -n 'PUBLIC_ROOT_PREFIXES' api/middleware/auth_middleware.py",
            "python -c \"from api.middleware.auth_middleware import *; print('auth middleware loads')\"",
        ],
        acceptance_criteria=[
            AcceptanceCriteria(
                "Auth middleware allows configured root-mounted public prefixes",
                "grep -c 'PUBLIC_ROOT_PREFIXES' api/middleware/auth_middleware.py",
            ),
        ],
    ),
    Task(
        id="FIX-002",
        title="Fix 38 frontend calls to non-existent endpoints (KNOWN_DEBT #33)",
        description="Mount missing routers (aegis, odyssey) or remove dead frontend calls",
        phase="fix",
        priority=1,
        area="frontend",
        weight=3.0,
        dependencies=["AUDIT-001", "AUDIT-002"],
        verification_commands=[
            "grep -r 'aegis\\|odyssey' frontend/src/lib/backend.ts",
            "grep -r 'aegis\\|odyssey' api/main.py",
        ],
        acceptance_criteria=[],
    ),
    Task(
        id="FIX-003",
        title="Fix UNKNOWN rendered as $0 in Command Center (KNOWN_DEBT #34)",
        description="Change IncomeHome.vue and Capital.vue to render '—' / 'UNKNOWN' instead of 0 for failed fetches",
        phase="fix",
        priority=1,
        area="frontend",
        weight=2.0,
        dependencies=["AUDIT-001", "AUDIT-002"],
        verification_commands=[
            "grep -n '|| 0' frontend/src/pages/IncomeHome.vue",
            "grep -n '\\$0' frontend/src/pages/IncomeHome.vue",
        ],
        acceptance_criteria=[
            AcceptanceCriteria(
                "No '|| 0' patterns converting UNKNOWN to 0", "grep -c '|| 0' frontend/src/pages/IncomeHome.vue"
            ),
        ],
    ),
    Task(
        id="FIX-004",
        title="Fix WebSocket handshake 403 (KNOWN_DEBT #35)",
        description="Fix /api/ws upgrade failing with 403 - auth middleware allows WS but endpoint rejects",
        phase="fix",
        priority=1,
        area="backend",
        weight=2.0,
        dependencies=["AUDIT-001", "AUDIT-002"],
        verification_commands=[
            "curl -i -N -H 'Connection: Upgrade' -H 'Upgrade: websocket' http://localhost:8000/api/ws 2>&1 | head -5",
        ],
        acceptance_criteria=[],
    ),
    Task(
        id="FIX-005",
        title="Resolve dual ApprovalGate classes (KNOWN_DEBT #49)",
        description="Merge or remove conflicting ApprovalGate in cores/approval/gate.py vs gates.py",
        phase="fix",
        priority=1,
        area="core_functionality",
        weight=3.0,
        dependencies=["AUDIT-001", "AUDIT-002"],
        verification_commands=[
            "grep -r 'class ApprovalGate' cores/approval/",
        ],
        acceptance_criteria=[],
    ),
    # PHASE 3: REVENUE ENABLERS (P0 Revenue)
    Task(
        id="REV-001",
        title="Configure GitHub token for bounty submission (KNOWN_DEBT #28)",
        description="Add GITHUB_TOKEN to ~/.config/ownex/opportunity.env to enable 8 READY GitHub bounties ($5,087)",
        phase="revenue",
        priority=1,
        area="core_functionality",
        weight=5.0,
        dependencies=["FIX-001", "FIX-002", "FIX-003", "FIX-004", "FIX-005"],
        verification_commands=[
            "grep GITHUB_TOKEN ~/.config/ownex/opportunity.env",
        ],
        acceptance_criteria=[],
    ),
    Task(
        id="REV-002",
        title="Configure payment rails for FIRST PAID",
        description="Set up at least one payment method (POST /api/payment-compat/configured)",
        phase="revenue",
        priority=1,
        area="core_functionality",
        weight=5.0,
        dependencies=["REV-001"],
        verification_commands=[
            "curl -s http://localhost:8000/api/payment-compat/configured | grep -c true",
        ],
        acceptance_criteria=[],
    ),
    Task(
        id="REV-003",
        title="Add HackerOne/Bugcrowd/Intigriti/YesWeHack API keys",
        description="Configure bug bounty platform credentials in opportunity.env",
        phase="revenue",
        priority=1,
        area="core_functionality",
        weight=3.0,
        dependencies=["REV-001"],
        verification_commands=[
            "grep -c 'HACKERONE_API_KEY\\|BUGERROW_API_KEY\\|INTIGRITI_API_KEY\\|YESWEHACK_API_KEY' ~/.config/ownex/opportunity.env",
        ],
        acceptance_criteria=[],
    ),
    # PHASE 4: PLATFORM COMPLETION
    Task(
        id="PLAT-001",
        title="Complete Tauri desktop release build",
        description="Run full desktop build and verify installer works",
        phase="release",
        priority=2,
        area="desktop",
        weight=3.0,
        dependencies=["FIX-001", "FIX-002", "FIX-003", "FIX-004", "FIX-005"],
        verification_commands=[
            "cd /home/adriel/projects/Rastro && python run.py --backup",
        ],
        acceptance_criteria=[],
    ),
    Task(
        id="PLAT-002",
        title="Verify Android companion builds",
        description="Verify Android app compiles and connects to backend",
        phase="release",
        priority=2,
        area="desktop",
        weight=2.0,
        dependencies=["PLAT-001"],
        verification_commands=[
            "cd /home/adriel/projects/Rastro/android && ./gradlew assembleDebug 2>&1 | tail -10",
        ],
        acceptance_criteria=[],
    ),
    Task(
        id="PLAT-003",
        title="Complete Wear OS integration",
        description="Verify Wear OS module builds and syncs with companion",
        phase="release",
        priority=2,
        area="desktop",
        weight=2.0,
        dependencies=["PLAT-002"],
        verification_commands=[
            "ls /home/adriel/projects/Rastro/android/wear/",
        ],
        acceptance_criteria=[],
    ),
    # PHASE 5: FINAL VERIFICATION & RELEASE
    Task(
        id="REL-001",
        title="Run full regression suite",
        description="Execute make check (ruff + mypy + test-fast) and full test suite",
        phase="release",
        priority=2,
        area="testing",
        weight=4.0,
        dependencies=["PLAT-001", "PLAT-002", "PLAT-003"],
        verification_commands=[
            "cd /home/adriel/projects/Rastro && python scripts/dev check",
        ],
        acceptance_criteria=[],
    ),
    Task(
        id="REL-002",
        title="Run installation simulation",
        description="Test clean install from scratch on fresh environment",
        phase="release",
        priority=2,
        area="testing",
        weight=3.0,
        dependencies=["REL-001"],
        verification_commands=[
            "cd /home/adriel/projects/Rastro && python run.py --migrate-export /tmp/test_backup.zip --no-targets 2>&1 | tail -20",
        ],
        acceptance_criteria=[],
    ),
    Task(
        id="REL-003",
        title="Verify Definition of Done 100%",
        description="All categories: Product, Architecture, Backend, Frontend, Database, AI, Security, Testing, Desktop, Data, Documentation, Release, Economic Loop",
        phase="release",
        priority=2,
        area="testing",
        weight=5.0,
        dependencies=["REL-001", "REL-002"],
        verification_commands=[
            'python -c "from scripts.finisher.task_queue import TaskQueue; from scripts.finisher.state import state_manager; q=TaskQueue(state_manager.get_state()); p=q.calculate_progress(); print(f\'Overall: {p["overall"]:.1f}%\')"',
        ],
        acceptance_criteria=[],
    ),
]

for task in real_tasks:
    state.tasks[task.id] = task

state_manager.save()
print(f"Injected {len(real_tasks)} real OWNEX completion tasks")
print("Tasks by phase:")
phases = Counter(t.phase for t in real_tasks)
for phase, count in phases.items():
    print(f"  {phase}: {count}")
