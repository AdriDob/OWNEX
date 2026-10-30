import subprocess
import sys

args = ["pytest", "-q", "--maxfail=1", "-vv"]
print("Running:", " ".join(args))
proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
open("/tmp/pytest_full.txt", "wb").write(proc.stdout)
print("Wrote /tmp/pytest_full.txt, exit", proc.returncode)
sys.exit(proc.returncode)
