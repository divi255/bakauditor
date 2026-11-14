from datetime import datetime
from types import SimpleNamespace
from bakauditor.command import run


def check(**kwargs):
    output = run(['zfs', 'list', '-H', '-p', '-t', 'snapshot',
                  '-o', 'name,used,creation'], ssh=kwargs.get('ssh'),
                 timeout=kwargs.get('timeout', 60))
    snapshots = []
    for line in output.splitlines():
        name, used, created = line.split()
        if name.startswith(kwargs['fs'] + '@'):
            # Retain explicit name-based timestamps for old configurations.
            fmt = kwargs.get('time-fmt')
            try:
                timestamp = (datetime.strptime(name.split('@', 1)[1], fmt).timestamp()
                             if fmt else float(created))
            except ValueError:
                continue
            snapshots.append((timestamp, int(used)))
    timestamp, size = max(snapshots, default=(0, None))
    return SimpleNamespace(ok=timestamp > 0, time=timestamp, size=size,
                           err=None if timestamp > 0 else 'No matching snapshots')
