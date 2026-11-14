"""Audit the newest matching snapshot; does not replace restic check/restore."""
import json
from types import SimpleNamespace
from dateutil.parser import isoparse
from bakauditor.command import run
from bakauditor.tools import iso_to_bytes


def check(**kwargs):
    args = ['restic', '--json', '--repo', kwargs['repo']]
    if kwargs.get('password-file'):
        args += ['--password-file', kwargs['password-file']]
    options = dict(ssh=kwargs.get('ssh'), password=kwargs.get('password'),
                   password_var='RESTIC_PASSWORD', timeout=kwargs.get('timeout', 60))
    filters = []
    for key in ('host', 'path', 'tag'):
        value = kwargs.get(key)
        if value is not None:
            for item in value if isinstance(value, list) else [value]:
                filters += ['--' + key, str(item)]
    snapshots = json.loads(run(args + ['snapshots', *filters], **options))
    if not snapshots:
        return SimpleNamespace(ok=False, time=0, size=None, err='No matching snapshots')
    latest = max(snapshots, key=lambda s: isoparse(s['time']).timestamp())
    timestamp = isoparse(latest['time']).timestamp()
    size = None
    if 'min-size' in kwargs:
        # Pin stats to the exact selected ID, not a second moving "latest" lookup.
        stats = json.loads(run(args + ['stats', '--mode', 'restore-size', latest['id']], **options))
        size = stats['total_size']
        if not isinstance(size, (int, float)) or size < 0:
            raise ValueError('Invalid snapshot size')
    ok = size is None or size >= iso_to_bytes(kwargs['min-size'])
    return SimpleNamespace(ok=ok, time=timestamp, size=size,
                           err=None if ok else 'Too small')
