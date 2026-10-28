import os
import sys

sys.path.insert(0, str(__file__).replace("/scripts/security_run.py", ""))

from cores.cycles.security import get_security_cycle
from cores.cycles.stages.attack_surface_executor import AttackSurfaceExecutor
from cores.cycles.stages.evidence_executor import EvidenceExecutor
from cores.cycles.stages.hypothesis_executor import HypothesisExecutor
from cores.cycles.stages.learning_executor import LearningExecutor
from cores.cycles.stages.recon_executor import ReconExecutor
from cores.cycles.stages.report_executor import ReportExecutor
from cores.cycles.stages.validation_executor import ValidationExecutor


def main():
    security = get_security_cycle()
    security.ensure_cycle()

    # Priority: 1. CLI arg, 2. env var, 3. interactive (if TTY)
    if len(sys.argv) > 1:
        target = sys.argv[1]
    elif os.environ.get("SECURITY_TARGET"):
        target = os.environ["SECURITY_TARGET"]
    elif sys.stdin.isatty():
        target = input("Target domain (e.g. example.com): ") or "example.com"
    else:
        target = "example.com"

    ctx = {"target": target}
    executors = [
        ("Recon", ReconExecutor()),
        ("Attack Surface", AttackSurfaceExecutor()),
        ("Hypothesis", HypothesisExecutor()),
        ("Validation", ValidationExecutor()),
        ("Evidence", EvidenceExecutor()),
        ("Report", ReportExecutor()),
        ("Learning", LearningExecutor()),
    ]

    for name, exe in executors:
        r = exe.execute(ctx)
        ctx.update(r.get("details", {}))
        print(f"{name}: {r['status']} - {r['summary']}")

    print("Done")


if __name__ == "__main__":
    main()
