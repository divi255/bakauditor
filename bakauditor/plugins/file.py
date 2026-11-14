import os
from pathlib import Path
from types import SimpleNamespace
from bakauditor.tools import iso_to_bytes


def check(**kwargs):
    path = Path(kwargs['path'])
    stat = path.stat()
    if path.is_file():
        size = stat.st_size
    elif path.is_dir():
        size = 0
        def onerror(error):
            raise error
        for parent, _, files in os.walk(path, onerror=onerror):
            for name in files:
                child = Path(parent) / name
                if not child.is_symlink():
                    size += child.stat().st_size
    else:
        raise ValueError('Not a regular file or directory')
    ok = 'min-size' not in kwargs or size >= iso_to_bytes(kwargs['min-size'])
    return SimpleNamespace(ok=ok, time=stat.st_mtime, size=size,
                           err=None if ok else 'Too small')
