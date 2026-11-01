"""Replay three isolated, simulated release scenario sets twice.

This records automated evidence only. It does not claim a live Supabase/model
demonstration, visual acceptance, or another team member's review.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "planning_membership": ("test_planning_portal.py", "test_operations.py"),
    "disruption_complaint": ("test_exception_portal.py", "test_complaint_portal.py"),
    "supplier_campaign": ("test_supplier_portal.py", "test_campaigns.py"),
}


def replay():
    digest = hashlib.sha256()
    for directory in ("src", "tests", "scripts"):
        for path in sorted((ROOT / directory).rglob("*.py")):
            digest.update(str(path.relative_to(ROOT)).encode())
            digest.update(path.read_bytes())
    result = {"recordedAt": datetime.now(timezone.utc).isoformat(),
              "mode": "ISOLATED_SIMULATION", "python": sys.version.split()[0],
              "baseCommit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                           capture_output=True, text=True, check=True).stdout.strip(),
              "pythonSourceSha256": digest.hexdigest(),
              "workingTreeDirty": bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                                   capture_output=True, text=True, check=True).stdout),
              "sets": []}
    for iteration in (1, 2):
        for name, patterns in SCENARIOS.items():
            for pattern in patterns:
                command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", pattern]
                run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                output = run.stdout + run.stderr
                count = re.search(r"Ran (\d+) tests?", output)
                row = {"iteration": iteration, "scenarioSet": name, "testModule": pattern,
                       "testCount": int(count.group(1)) if count else None,
                       "passed": run.returncode == 0,
                       "resultTail": output[-1200:]}
                result["sets"].append(row)
                print(f"{iteration}/2 {name} {pattern}: "
                      f"{'PASS' if row['passed'] else 'FAIL'} ({row['testCount']} tests)", flush=True)
    result["allPassed"] = all(row["passed"] for row in result["sets"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = replay()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["allPassed"] else 1


if __name__ == "__main__":
    sys.exit(main())
