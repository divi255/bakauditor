import os

from functools import lru_cache
from datetime import datetime

from types import SimpleNamespace


@lru_cache(maxsize=4096)
def get_zfs_snapshots(ssh=None):
    ssh_cmd = '' if not ssh else 'ssh {} '.format(ssh)
    result = []
    with os.popen('{}zfs list -t snapshot'.format(ssh_cmd)) as p:
        for s in p.readlines():
            result.append(s.split()[0])
    return result


def check(**kwargs):
    fs = kwargs['fs']
    t = 0
    for s in get_zfs_snapshots(kwargs.get('ssh')):
        if s.startswith(fs + '@'):
            try:
                t = max(
                    t,
                    datetime.strptime(s.split('@')[1],
                                      kwargs.get('time-fmt')).timestamp())
            except:
                pass
    return SimpleNamespace(ok=t > 0, time=t, size=None, err=None)
