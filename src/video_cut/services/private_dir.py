"""Per-user private directories under the system temporary directory."""

import os
import stat
import tempfile
from pathlib import Path


def private_dir(name: str) -> Path:
    """Return a directory under the temp dir that only the current user can access.

    The name carries the uid so users of a shared host never collide. When the
    path already exists but is not a directory owned by the current user, for
    example a symlink or directory planted by another account, a fresh private
    directory is created instead, so nothing is ever written through the
    planted path.
    """
    uid = os.getuid()
    path = Path(tempfile.gettempdir()) / f"{name}-{uid}"
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    except OSError:
        return Path(tempfile.mkdtemp(prefix=f"{name}-"))

    try:
        st = path.lstat()
    except OSError:
        return Path(tempfile.mkdtemp(prefix=f"{name}-"))
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != uid:
        return Path(tempfile.mkdtemp(prefix=f"{name}-"))
    if st.st_mode & 0o077:
        path.chmod(0o700)
    return path
