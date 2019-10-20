import os

from types import SimpleNamespace

import dateutil.parser
import json


def get_borg(ssh=None, pw=None, repo=None):
    ssh_cmd = '' if not ssh else 'ssh {} '.format(ssh)
    result = []
    with os.popen('{}env BORG_PASSPHRASE={} borg list --json {} 2>&1'.format(
            ssh_cmd, pw, repo)) as p:
        return p.read()


def check(**kwargs):
    result = SimpleNamespace(ok=False, time=0, size=None, err=None)
    r = get_borg(kwargs.get('ssh'), kwargs.get('password'),
                     kwargs['repo'])
    try:
        t = json.loads(r)['repository']['last_modified']
        result.time = dateutil.parser.parse(t).timestamp()
        result.ok = True
    except json.decoder.JSONDecodeError:
        if r.startswith('passphrase supplied in '):
            result.err = 'Invalid passphrase'
        else:
            result.err = 'Command failed'
    return result
