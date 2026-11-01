"""Optional Git provenance for verification run from a checkout or source ZIP."""
from pathlib import Path
import subprocess


def git_metadata(root):
    root = Path(root).resolve()
    unavailable = dict(baseCommit=None, workingTreeDirty=None, sourceControl='UNAVAILABLE')
    # Do not accidentally attribute an extracted ZIP to a containing repository.
    if not (root / '.git').exists():
        return unavailable

    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    try:
        if Path(git('rev-parse', '--show-toplevel')).resolve() != root:
            return unavailable
        commit = git('rev-parse', 'HEAD')
        dirty = bool(git('status', '--porcelain'))
    except (OSError, subprocess.CalledProcessError):
        return unavailable
    return dict(baseCommit=commit, workingTreeDirty=dirty, sourceControl='GIT')
