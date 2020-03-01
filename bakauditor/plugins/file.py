import os

from types import SimpleNamespace

from bakauditor.tools import iso_to_bytes

def check(**kwargs):
    result = SimpleNamespace(ok=False, time=0, size=None, err=None)
    try:
        t = os.path.getmtime(kwargs['path'])
        if os.path.isfile(kwargs['path']):
            size = os.path.getsize(kwargs['path'])
        else:
            with os.popen('du -sB1 {}'.format(kwargs['path'])) as fp:
                size = int(fp.readline().split()[0])
    except:
        return result
    result.time = t
    result.size = size
    if 'min-size' in kwargs:
        result.ok = size >= iso_to_bytes(kwargs['min-size'])
        if not result.ok:
            result.err = 'Too small'
    else:
        result.ok = True
    return result
