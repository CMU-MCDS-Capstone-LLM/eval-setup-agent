"""Filesystem utilities."""

import tempfile
import shutil
from pathlib import Path
from typing import Union


def atomic_write(path: Path, content: Union[str, bytes]) -> None:
    """
    Write content to file atomically.

    Args:
        path: Destination path
        content: Content to write (str or bytes)
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first
    mode = "w" if isinstance(content, str) else "wb"
    with tempfile.NamedTemporaryFile(
        mode=mode,
        dir=path.parent,
        delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    # Atomic rename
    shutil.move(str(tmp_path), str(path))


def ensure_dirs(*paths: Path) -> None:
    """
    Ensure directories exist.

    Args:
        *paths: Paths to create
    """
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)
