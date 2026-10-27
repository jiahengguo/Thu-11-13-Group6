"""Cross-platform setup entry; leaves existing credentials and data untouched."""
import argparse
from pathlib import Path
import subprocess
import sys
import venv


def main():
    parser = argparse.ArgumentParser(description='Install TripMate and prepare its local configuration template')
    parser.add_argument('--venv', default='.venv', help='Virtual environment directory, relative to the source root')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    environment = root / args.venv
    python = environment / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    if sys.version_info < (3, 9):
        parser.exit(1, 'Python 3.9 or later is required.\n')
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(environment)
    subprocess.run([str(python), '-m', 'pip', 'install', '-e', str(root)], cwd=root, check=True)
    config = root / '.env'
    if not config.exists():
        # Exclusive create: never overwrite credentials even if another setup is running.
        try:
            with config.open('x') as stream:
                stream.write((root / '.env.example').read_text())
            config.chmod(0o600)
        except FileExistsError:
            pass
    print('Dependencies installed. Existing accounts, records and configuration were preserved.')
    print('Configure .env locally. Supabase requires existing migrations; no cloud users were created.')
    print('Next: run this environment Python with scripts/start_demo.py.')


if __name__ == '__main__':
    main()
