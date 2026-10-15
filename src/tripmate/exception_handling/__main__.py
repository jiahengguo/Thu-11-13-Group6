import argparse
import json
from .repository import ExceptionRepository
from .fixtures import demo_runtime, SCENARIOS
from tripmate.agents.exception import CustomerExceptionAgent

def main():
    parser = argparse.ArgumentParser(description='TripMate Customer Exception simulation; no external actions.')
    parser.add_argument('--case', choices=['disruption', 'complaint'], default='disruption')
    parser.add_argument('--scenario', choices=SCENARIOS, default='normal')
    parser.add_argument('--database', default='data/exception-demo.sqlite3')
    args = parser.parse_args()
    repo = ExceptionRepository(args.database)
    case, runtime = demo_runtime(repo, args.case.upper(), args.scenario)
    result = CustomerExceptionAgent(runtime).handle_case(case)
    print(json.dumps(repo.get(result['runId']) or {'result': result, 'saved': False}, indent=2, ensure_ascii=False))
    if result['status'] == 'FAILURE':
        raise SystemExit(1)

if __name__ == '__main__':
    main()
