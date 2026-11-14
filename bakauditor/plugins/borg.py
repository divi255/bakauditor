import json
from types import SimpleNamespace
from dateutil.parser import isoparse
from bakauditor.command import run
from bakauditor.tools import iso_to_bytes


def get_borg(ssh=None, pw=None, repo=None, timeout=60):
    return run(['borg', 'info', '--last', '1', '--json', repo], ssh=ssh,
               password=pw, password_var='BORG_PASSPHRASE', timeout=timeout)


def check(**kwargs):
    data = json.loads(get_borg(kwargs.get('ssh'), kwargs.get('password'),
                               kwargs['repo'], kwargs.get('timeout', 60)))
    archives = data.get('archives') or []
    if not archives:
        return SimpleNamespace(ok=False, time=0, size=None, err='No archives')
    archive = archives[0]
    # Archive creation, not repository modification (e.g. prune/check).
    timestamp = isoparse(archive['start']).timestamp()
    size = archive['stats']['original_size']
    ok = 'min-size' not in kwargs or size >= iso_to_bytes(kwargs['min-size'])
    return SimpleNamespace(ok=ok, time=timestamp, size=size,
                           err=None if ok else 'Too small')
