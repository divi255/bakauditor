import os

from types import SimpleNamespace

import dateutil.parser
import json

from bakauditor.tools import iso_to_bytes


def get_borg(ssh=None, pw=None, repo=None):
    ssh_cmd = '' if not ssh else 'ssh {} '.format(ssh)
    with os.popen(
            '{}env BORG_PASSPHRASE={} borg info --last 1 --json {} 2>&1'.format(
                ssh_cmd, '' if pw is None else pw, repo)) as p:
        return p.read()


def check(**kwargs):
    result = SimpleNamespace(ok=False, time=0, size=None, err=None)
    r = get_borg(kwargs.get('ssh'), kwargs.get('password'), kwargs['repo'])
    try:
        j = json.loads(r)
        t = j['repository']['last_modified']
        result.time = dateutil.parser.parse(t).timestamp()
        result.size = j['archives'][0]['stats']['original_size']
        if 'min-size' in kwargs:
            result.ok = result.size >= iso_to_bytes(kwargs['min-size'])
            if not result.ok:
                result.err = 'Too small'
        else:
            result.ok = True
    except json.decoder.JSONDecodeError:
        if r.startswith('passphrase supplied in '):
            result.err = 'Invalid passphrase'
        else:
            result.err = 'Command failed'
    return result
