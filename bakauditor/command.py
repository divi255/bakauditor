"""Bounded external commands, with secrets kept out of process arguments."""
import math
import os
import shlex
import subprocess


class CommandError(RuntimeError):
    """Safe diagnostic without command arguments or backend output."""


def run(args, *, ssh=None, password=None, password_var=None, timeout=60, unset_env=()):
    timeout = float(timeout)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout must be positive and finite')
    args = [str(arg) for arg in args]
    env = os.environ.copy()
    allowed = {'RESTIC_PASSWORD', 'RESTIC_PASSWORD_FILE', 'RESTIC_PASSWORD_COMMAND'}
    if not set(unset_env) <= allowed:
        raise ValueError('unsupported environment variable')
    for name in unset_env:
        env.pop(name, None)
    data = None
    if password is not None:
        password = str(password)
        if '\n' in password or '\r' in password or '\0' in password:
            raise ValueError('password must not contain line breaks or NUL')
    if ssh:
        remote = shlex.join(args)
        if password is not None:
            if password_var not in {'BORG_PASSPHRASE', 'RESTIC_PASSWORD'}:
                raise ValueError('unsupported password variable')
            remote = (f'IFS= read -r {password_var}; export {password_var}; '
                      f'exec {remote}')
            data = password + '\n'
        if unset_env:
            remote = 'unset ' + ' '.join(unset_env) + '; ' + remote
        args = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                *shlex.split(ssh), remote]
    elif password is not None:
        env[password_var] = password
    try:
        result = subprocess.run(args, input=data, stdin=None if data is not None else subprocess.DEVNULL,
                                capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CommandError('Command timed out') from None
    except OSError:
        raise CommandError('Unable to execute command') from None
    if result.returncode:
        # Raw command output may contain repository credentials or passwords.
        raise CommandError(f'Command failed (exit {result.returncode})')
    return result.stdout
