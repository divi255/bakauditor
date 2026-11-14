import argparse
from datetime import datetime
import importlib
import math
import re
import sys
import time
from types import SimpleNamespace
import yaml
from bakauditor import __version__
from bakauditor.command import CommandError
from bakauditor.tools import bytes_to_iso, iso_to_bytes

PLUGINS = {'file', 'dir', 'dod', 'zfs', 'borg', 'borg0', 'restic'}


def date_to_ts(value):
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*([SMHDW]?)', str(value).strip().upper())
    if not match:
        raise ValueError('Invalid duration')
    result = float(match[1]) * {'': 1, 'S': 1, 'M': 60, 'H': 3600, 'D': 86400, 'W': 604800}[match[2]]
    if not math.isfinite(result) or result <= 0:
        raise ValueError('Duration must be positive and finite')
    return result


def load_config(path, backup_id=None):
    with open(path, encoding='utf-8') as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict) or not config:
        raise ValueError('Configuration must contain backups')
    defaults = config.get('default', {})
    if defaults is None:
        defaults = {}
    if not isinstance(defaults, dict):
        raise ValueError('default must be a mapping')
    if backup_id is not None and (backup_id == 'default' or backup_id not in config):
        raise ValueError('No such backup')
    checks = {}
    for name, value in config.items():
        if name == 'default' or (backup_id is not None and name != backup_id):
            continue
        if not isinstance(name, str) or not isinstance(value, dict):
            raise ValueError('Each backup must be a named mapping')
        options = {**defaults, **value}
        kind = options.get('type')
        if kind not in PLUGINS:
            raise ValueError(f'{name}: Unknown backup type')
        required = 'fs' if kind == 'zfs' else 'repo' if kind in {'borg', 'borg0', 'restic'} else 'path'
        if not isinstance(options.get(required), str) or not options[required]:
            raise ValueError(f'{name}: Missing {required}')
        if 'time' not in options:
            raise ValueError(f'{name}: Missing time limit')
        date_to_ts(options['time'])
        timeout = float(options.get('timeout', 60))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('timeout must be positive and finite')
        if 'min-size' in options:
            size = iso_to_bytes(options['min-size'])
            if not math.isfinite(size) or size < 0:
                raise ValueError('min-size must be nonnegative and finite')
        checks[name] = options
    if not checks:
        raise ValueError('No backups configured')
    return checks


def audit(config):
    rows = []
    for name, options in sorted(config.items()):
        try:
            checker = importlib.import_module('bakauditor.plugins.' + options['type'])
            result = checker.check(**options)
            if result.size is not None and (not isinstance(result.size, (int, float))
                                            or not math.isfinite(result.size) or result.size < 0):
                raise ValueError('Invalid backup size')
            if not math.isfinite(result.time) or result.time <= 0:
                result.ok = False
                result.err = result.err or 'No backup timestamp'
            elif result.time > time.time() + 300:
                result.ok = False
                result.err = 'Future timestamp'
            elif time.time() - result.time > date_to_ts(options['time']):
                result.ok = False
                result.err = 'Outdated'
            # Check formatting within the failure boundary too.
            datetime.fromtimestamp(result.time if result.time > 0 else 0)
        except Exception as error:
            # Backend exceptions can embed credentials; never print their raw text.
            result = SimpleNamespace(ok=False, time=0, size=None,
                                     err=str(error) if isinstance(error, CommandError) else f'Check failed ({type(error).__name__})')
        rows.append((name, result))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description='Backup freshness and size auditor')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('-f', '--config', default='/usr/local/etc/bakauditor.yml', metavar='FILE')
    parser.add_argument('-x', dest='failed_only', action='store_true', help='Print failed only')
    parser.add_argument('backup_id', nargs='?', metavar='ID')
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config, args.backup_id)
    except (OSError, ValueError, TypeError, yaml.YAMLError) as error:
        print(f'Configuration error ({type(error).__name__}); check YAML and required options', file=sys.stderr)
        return 2
    rows = audit(config)
    failed = sum(not result.ok for _, result in rows)
    print(f'Checked: {len(rows)}, failed: {failed}\n')
    visible = [(name, r) for name, r in rows if not args.failed_only or not r.ok]
    if visible:
        import rapidtables
        from neotermcolor import cprint
        table = [dict(backup=name,
                      date=datetime.fromtimestamp(r.time).strftime('%Y-%m-%d %H:%M:%S') if r.time > 0 else '-',
                      size=bytes_to_iso(r.size) if r.size is not None else '-',
                      status='OK' if r.ok else r.err or 'Failed') for name, r in visible]
        header, values = rapidtables.format_table(table, fmt=rapidtables.FORMAT_GENERATOR)
        cprint(header, 'blue')
        cprint('-' * len(header), 'grey')
        for value, (_, result) in zip(values, visible):
            cprint(value, 'red' if not result.ok else None)
    elif args.failed_only:
        print('All backups are fine')
    return 1 if failed else 0
