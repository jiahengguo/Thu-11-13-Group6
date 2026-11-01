"""Inspect and clean-install a source ZIP without cloud credentials or Node."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from package_release import REQUIRED, allowed, safe_path

MAX_RELEASE_BYTES = 256 * 1024 * 1024


def validate_archive(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP paths.')
        if sum(entry.file_size for entry in entries) > MAX_RELEASE_BYTES:
            raise ValueError('Release exceeds the inspection size limit.')
        roots = set()
        for entry in entries:
            if not safe_path(entry.filename) or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('Unsafe ZIP path or symlink.')
            roots.add(entry.filename.split('/')[0])
        if len(roots) != 1:
            raise ValueError('A release must have exactly one project folder.')
        folder = roots.pop()
        metadata = json.loads(archive.read(folder + '/RELEASE.json'))
        commit = metadata.get('commit', '')
        if (metadata.get('formatVersion') != 1 or not re.fullmatch(r'[0-9a-f]{40}', commit)
                or folder != 'TripMate-' + commit[:12]):
            raise ValueError('Invalid release identity.')
        files = metadata['files']
        if REQUIRED - files.keys():
            raise ValueError('Required release files missing.')
        expected = {folder + '/' + name for name in files} | {folder + '/RELEASE.json'}
        if set(names) != expected:
            raise ValueError('ZIP differs from its manifest.')
        for name, record in files.items():
            if not allowed(name):
                raise ValueError('Forbidden release file: ' + name)
            data = archive.read(folder + '/' + name)
            if len(data) != record['size'] or hashlib.sha256(data).hexdigest() != record['sha256']:
                raise ValueError('Release content hash mismatch: ' + name)
    checksum = path.with_name(path.name + '.sha256')
    if checksum.is_file():
        if checksum.read_text().strip() != hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name:
            raise ValueError('ZIP checksum mismatch.')
    return folder, metadata


SMOKE = r'''
import sys, threading
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'tests'))
from test_portals import FakeCloud, Browser
from tripmate.portal.server import make_server
cloud = FakeCloud()
server = make_server(cloud, port=0)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    root = 'http://127.0.0.1:' + str(server.server_port)
    status, script, headers = Browser(root).call('/portal-queue.js')
    assert status == 200 and 'TripMateQueue' in script
    assert 'text/javascript' in headers['Content-Type']
    assert "script-src 'self'" in headers['Content-Security-Policy']
    for role, route in [('TRAVELLER', '/app'), ('SUPPLIER', '/supplier'), ('OPERATOR', '/admin')]:
        actor, _ = cloud.add(role)
        browser = Browser(root)
        assert browser.login(actor)[0] == 200
        status, page, _ = browser.call(route)
        assert status == 200
        assert page.index('src="/portal-queue.js"') < page.index('src="/portal.js"')
        assert browser.call('/api/operations/cases')[1]['cases'] == []
    print('Installed ZIP: three role portals, local React bundle and CSP passed (provider doubles).')
finally:
    server.shutdown()
    server.server_close()
'''


def verify(path, install=True):
    folder, metadata = validate_archive(path)
    if install:
        with tempfile.TemporaryDirectory(prefix='tripmate-release-') as temp:
            with zipfile.ZipFile(path) as archive:
                archive.extractall(temp)  # Only after paths, types, size and hashes are validated.
            root = Path(temp) / folder
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(('SUPABASE_', 'ELEC5620_', 'TRIPMATE_', 'VITE_'))}
            # The shipped scripts and installed portal must work without Node/npm.
            env['PATH'] = str(root / '.venv' / ('Scripts' if os.name == 'nt' else 'bin'))
            setup = [sys.executable, str(root / 'scripts/setup_demo.py')]
            subprocess.run(setup, cwd=temp, env=env, check=True)
            config = root / '.env'
            config.write_text('RELEASE_INSTALL_REHEARSAL=preserve\n')
            subprocess.run(setup, cwd=temp, env=env, check=True)
            if config.read_text() != 'RELEASE_INSTALL_REHEARSAL=preserve\n':
                raise ValueError('Repeat setup changed existing configuration.')
            python = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            subprocess.run([str(python), '-c', SMOKE], cwd=root, env=env, check=True)
    print('Release verified: ' + metadata['commit'])
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--inspect-only', action='store_true')
    args = parser.parse_args()
    verify(args.archive.resolve(), install=not args.inspect_only)


if __name__ == '__main__':
    main()
