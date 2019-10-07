from types import SimpleNamespace

import glob
import os

from bakauditor.plugins.file import check as check_file

def check(**kwargs):
    result = SimpleNamespace(ok=False, time=0, size=None, err=None)
    path = kwargs['path']
    if os.path.isdir(path):
        path += '/*'
    fls = [x for x in glob.glob(path) if os.path.isfile(x)]
    if not fls:
        return result
    kw = kwargs.copy()
    kw['path'] = max(fls, key=os.path.getmtime)
    return check_file(**kw)
