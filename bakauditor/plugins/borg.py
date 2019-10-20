import os

from types import SimpleNamespace

import dateutil.parser
import json

units = {"B": 1, "K": 10**3, "M": 10**6, "G": 10**9, "T": 10**12}
def parseSize(size):
    if not isinstance(size, int):
        import re
        p = re.compile("^([0-9]+)([a-zA-Z]+)$")
        result = p.search(size)
        number = result.group(1)
        unit = result.group(2).upper()[0]
        return int(float(number)*units[unit])
    else:
        return size

def get_borg(ssh=None, pw=None, repo=None):
    ssh_cmd = '' if not ssh else 'ssh {} '.format(ssh)
    result = []
    if pw == None:
        pw = ''
    with os.popen(
            '{}env BORG_PASSPHRASE={} borg info --last 1 --json {} 2>&1'.format(
                ssh_cmd, pw, repo)) as p:
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
            result.ok = result.size >= parseSize(kwargs.get('min-size'))
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
