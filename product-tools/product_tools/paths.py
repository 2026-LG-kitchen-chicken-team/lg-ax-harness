"""Existing-path resolution that also works inside Windows AppContainer sandboxes."""
import os
from pathlib import Path


def real_path(path):
    """Path.resolve(strict=True), or an exact fallback where volume names are hidden.

    Codex's Windows MXC sandbox can deny the mount-manager lookup behind
    GetFinalPathNameByHandle (WinError 5) for every path while reads still work.
    The lexical absolute path is then used only if it exists and none of its
    components is a symlink or junction, so containment checks stay exact.
    """
    path = Path(path)
    try:
        return path.resolve(strict=True)
    except PermissionError as exc:
        if getattr(exc, "winerror", None) != 5:
            raise
        candidate = Path(os.path.abspath(path))
        candidate.stat()
        if any(part.is_symlink() or part.is_junction() for part in (candidate, *candidate.parents)):
            raise
        return candidate
