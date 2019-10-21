import os

from types import SimpleNamespace

import dateutil.parser
import json

from bakauditor.tools import iso_to_bytes


def get_borg(ssh=None, pw=None, repo=None):
    ssh_cmd = '' if not ssh else 'ssh {} '.format(ssh)
    with os.popen('{}env BORG_PASSPHRASE={} borg list {} 2>&1'.format(
            ssh_cmd, '' if pw is None else pw, repo)) as p:
        return p.readlines()


def check(**kwargs):
    result = SimpleNamespace(ok=False, time=0, size=None, err=None)
    for r in get_borg(kwargs.get('ssh'), kwargs.get('password'),
                      kwargs['repo']):
        try:
            result.time = max(
                result.time,
                dateutil.parser.parse(r.split(maxsplit=1)[1]).timestamp())
            result.ok = True
        except:
            result.err = 'Command failed'
    return result
