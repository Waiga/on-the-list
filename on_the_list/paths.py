"""Where a downloaded register is kept.

One small module so that the rest of the package never has to know which
operating system it is on, and so the offline test has a single place to look
when it checks that nothing here reaches outside the filesystem.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP = "on-the-list"


def data_dir() -> Path:
    """The per-user directory a downloaded register is cached in.

    Follows each platform's own convention rather than inventing a dotfile:
    ``~/Library/Application Support`` on macOS, ``%LOCALAPPDATA%`` on Windows,
    and ``$XDG_DATA_HOME`` (falling back to ``~/.local/share``) elsewhere.

    ``ON_THE_LIST_HOME`` overrides all of it. That exists for the tests, and
    for anyone who wants the register on a shared volume.
    """
    override = os.environ.get("ON_THE_LIST_HOME")
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / APP
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP


def register_dir() -> Path:
    """Where the downloaded annex CSVs live, if any have been downloaded."""
    return data_dir() / "register"
