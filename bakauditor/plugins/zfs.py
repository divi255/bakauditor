import os

from functools import lru_cache
from datetime import datetime

from types import SimpleNamespace


@lru_cache(maxsize=4096)
def get_zfs_snapshots(ssh=None):
    ssh_cmd = '' if not ssh else 'ssh {} '.format(ssh)
    result = []
    with os.popen('{}zfs list -p -t snapshot'.format(ssh_cmd)) as p:
        for s in p.readlines()[1:]:
            try:
                path, size = s.split()[:2]
                result.append((path, size))
            except:
                pass
    return result


def check(**kwargs):
    fs = kwargs['fs']
    t = 0
    size = None
    for snap in get_zfs_snapshots(kwargs.get('ssh')):
        s = snap[0]
        if s.startswith(fs + '@'):
            try:
                t = max(
                    t,
                    datetime.strptime(s.split('@')[1],
                                      kwargs.get('time-fmt')).timestamp())
                try:
                    size = int(snap[1])
                except:
                    pass
            except:
                pass
    return SimpleNamespace(ok=t > 0, time=t, size=size, err=None)
