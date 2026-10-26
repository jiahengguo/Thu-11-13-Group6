"""Start the integrated authenticated portal after explicit provider preflights."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description='Check and start the TripMate integrated demo')
    parser.add_argument('--port', type=int, default=8780)
    parser.add_argument('--skip-model-probe', action='store_true', help='Skip the live probe; does not imply model success')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    check = [sys.executable, '-m', 'tripmate.portal.doctor', '--env-file', str(root / '.env'),
             '--demo-pricing', '--check-cloud']
    if not args.skip_model_probe:
        check.append('--check-model')
    result = subprocess.run(check, cwd=root)
    if result.returncode:
        parser.exit(result.returncode, 'Startup checks failed. Correct the reported configuration; no reset was performed.\n')
    return subprocess.call([sys.executable, '-m', 'tripmate.portal.server', '--env-file', str(root / '.env'),
                            '--port', str(args.port), '--demo-pricing', '--model-planning'], cwd=root)


if __name__ == '__main__':
    raise SystemExit(main())
