"""Package committed, allowlisted sources; never read local secrets or edited docs."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import tarfile
import zipfile

ROOT_FILES = {'README.md', 'README.zh-CN.md', 'pyproject.toml', '.env.example'}
CONFIG_FILES = {'.github/workflows/ci.yml'}
SOURCE_PREFIXES = ('src/', 'scripts/', 'supabase/migrations/', 'docs/', 'web/', 'tests/')
FORBIDDEN_PARTS = {'.git', '.venv', 'node_modules', '__pycache__', '.vscode',
                   '.aws', '.codex', '.agents', '.DS_Store', 'dist', 'build'}
REQUIRED = ROOT_FILES | CONFIG_FILES | {
    'scripts/setup_demo.py', 'scripts/start_demo.py', 'scripts/package_release.py',
    'scripts/verify_release.py', 'src/tripmate/portal/server.py',
    'src/tripmate/portal/static/portal-queue.js',
    'src/tripmate/portal/static/portal-queue.LICENSE.txt',
    'web/package.json', 'web/package-lock.json', 'web/src/RequestQueue.jsx',
    'tests/test_portals.py',
}


def safe_path(name):
    path = PurePosixPath(name)
    return (bool(name) and not path.is_absolute() and '\\' not in name
            and all(part not in ('', '.', '..') for part in name.split('/')))


def allowed(name):
    if not safe_path(name):
        return False
    parts = PurePosixPath(name).parts
    leaf = parts[-1]
    if any(part in FORBIDDEN_PARTS for part in parts):
        return False
    if leaf == '.env.example':
        return name == '.env.example'
    if (leaf.startswith(('.env', '.demo-accounts')) or '.local.' in leaf
            or leaf.endswith(('.sqlite3', '.sqlite3-shm', '.sqlite3-wal', '.db', '.pyc', '.log', '.zip', '.whl'))
            or leaf == 'LOCAL_ACCEPTANCE_PATCH.json'):
        return False
    return name in ROOT_FILES | CONFIG_FILES or name.startswith(SOURCE_PREFIXES)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def package(root, output, expected_commit=None):
    commit = git(root, 'rev-parse', 'HEAD').decode().strip()
    if expected_commit and commit != expected_commit:
        raise ValueError('Checkout differs from the commit whose checks triggered delivery.')
    tree = git(root, 'rev-parse', 'HEAD^{tree}').decode().strip()
    stamp = int(git(root, 'show', '-s', '--format=%ct', 'HEAD').decode().strip())
    # git archive uses committed blobs. Worktree changes, including the user's
    # newer DEMO_SCENARIOS document, cannot enter the archive.
    sources = {}
    # Windows runners may globally enable autocrlf. An archive must not depend
    # on the maintainer's checkout newline preferences.
    raw = git(root, '-c', 'core.autocrlf=false', '-c', 'core.eol=lf',
              'archive', '--format=tar', commit)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive:
            if member.isdir() or not allowed(member.name):
                continue
            if not member.isfile():
                raise ValueError('Release source must be a regular file: ' + member.name)
            sources[member.name] = archive.extractfile(member).read()
    missing = REQUIRED - sources.keys()
    if missing:
        raise ValueError('Required committed release files missing: ' + ', '.join(sorted(missing)))
    frontend = json.loads(sources['web/package.json'])
    run = os.environ.get('GITHUB_RUN_ID', '')
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    server = os.environ.get('GITHUB_SERVER_URL', 'https://github.com')
    metadata = {
        'formatVersion': 1, 'commit': commit, 'tree': tree,
        'ref': os.environ.get('GITHUB_REF', ''),
        'workflowUrl': server + '/' + repo + '/actions/runs/' + run if run and repo else None,
        'buildPython': platform.python_version(),
        'buildNode': os.environ.get('BUILD_NODE_VERSION', 'not-recorded-local-build'),
        'frontendDependencies': frontend['dependencies'],
        'frontendBuildTools': frontend['devDependencies'],
        'files': {name: {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                  for name, data in sorted(sources.items())},
    }
    manifest = (json.dumps(metadata, indent=2, sort_keys=True) + '\n').encode()
    folder = 'TripMate-' + commit[:12]
    output.mkdir(parents=True, exist_ok=True)
    target = output / (folder + '.zip')
    if target.exists():
        raise FileExistsError('Choose a fresh output directory; release ZIP already exists.')
    date = datetime.fromtimestamp(max(stamp, 315532800), timezone.utc).timetuple()[:6]
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(dict(sources, **{'RELEASE.json': manifest}).items()):
            info = zipfile.ZipInfo(folder + '/' + name, date_time=date)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / (target.name + '.sha256')).write_text(digest + '  ' + target.name + '\n')
    (output / 'release-metadata.json').write_bytes(manifest)
    print(json.dumps({'archive': str(target), 'commit': commit, 'sha256': digest,
                      'files': len(sources)}, indent=2))
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dist/releases'))
    args = parser.parse_args()
    package(Path(__file__).resolve().parents[1], args.output.resolve(), os.environ.get('GITHUB_SHA'))


if __name__ == '__main__':
    main()
