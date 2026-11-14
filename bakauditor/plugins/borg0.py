from types import SimpleNamespace
from dateutil.parser import parse
from bakauditor.command import run


def get_borg(ssh=None, pw=None, repo=None, timeout=60):
    return run(['borg', 'list', repo], ssh=ssh, password=pw,
               password_var='BORG_PASSPHRASE', timeout=timeout).splitlines()


def check(**kwargs):
    times = [parse(line.split(maxsplit=1)[1]).timestamp()
             for line in get_borg(kwargs.get('ssh'), kwargs.get('password'),
                                  kwargs['repo'], kwargs.get('timeout', 60))
             if line.strip()]
    return SimpleNamespace(ok=bool(times), time=max(times, default=0), size=None,
                           err=None if times else 'No archives')
