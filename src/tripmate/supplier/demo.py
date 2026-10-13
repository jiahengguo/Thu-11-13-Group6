"""Run one explicitly simulated B08 scenario; never make a real commitment."""
import argparse
import json
from pathlib import Path

from .common import SupplierError
from .fixtures import fixture_runtime


def main():
    parser = argparse.ArgumentParser(description='B08 synthetic supplier assessment')
    parser.add_argument('--scenario', default='coach', help='B03 quote ID or negative candidate label')
    parser.add_argument('--database', type=Path, default=Path('data/supplier-demo.sqlite3'))
    args = parser.parse_args()
    try:
        case, runtime = fixture_runtime(args.database, args.scenario)
        result = runtime.handle_case(case)
        print(json.dumps(dict(result=result, modelExecution='FIXTURE_REPLAY',
                              snapshot=runtime.repository.current(runtime.load_input(case['caseId'])['offerId']),
                              selectableCount=len(runtime.find_selectable({}, runtime.clock()))), indent=2))
    except SupplierError as exc:
        print(json.dumps(dict(status='BLOCKED', code=exc.code, message=str(exc))))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
