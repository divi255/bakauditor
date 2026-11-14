import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from bakauditor.cli import audit, load_config, main, date_to_ts
from bakauditor.command import run
from bakauditor.plugins import restic, borg, zfs
from bakauditor.tools import bytes_to_iso


class ConfigTests(unittest.TestCase):
    def config(self, value):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.yml'
            path.write_text(value)
            return load_config(path)

    def test_empty_invalid_and_unsafe_configs(self):
        for value in ('', '{}', '[]', 'default: {}', 'a: {}',
                      'a: {type: file, path: /tmp/x}',
                      'a: {type: file, path: /tmp/x, time: -1}',
                      '!!python/object/apply:os.system [echo unsafe]'):
            with self.subTest(value=value), self.assertRaises(Exception):
                self.config(value)

    def test_defaults(self):
        checks = self.config('default: {time: 1d, min-size: 2K}\na: {type: file, path: /tmp/x}\nb: {type: file, path: /tmp/y, time: 2d}')
        self.assertEqual(checks['a']['time'], '1d')
        self.assertEqual(checks['b']['time'], '2d')

    def test_duration(self):
        self.assertEqual(date_to_ts('2h'), 7200)
        for value in ('nan', 'inf', '0', '-3d'):
            with self.assertRaises(ValueError): date_to_ts(value)

    def test_invalid_cli_exit(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['-f', '/nonexistent/bakauditor.yml']), 2)


class FileTests(unittest.TestCase):
    def test_file_statuses_and_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'backup with spaces;literal'
            path.write_bytes(b'x' * 32)
            options = dict(type='file', path=str(path), time='1h', **{'min-size': 20})
            self.assertTrue(audit({'a': options})[0][1].ok)
            self.assertEqual(audit({'a': {**options, 'min-size': 50}})[0][1].err, 'Too small')
            os.utime(path, (time.time()-7200,)*2)
            self.assertEqual(audit({'a': options})[0][1].err, 'Outdated')
            path.unlink()
            self.assertFalse(audit({'a': options})[0][1].ok)
            config = Path(directory) / 'c.yml'
            config.write_text('a:\n  type: file\n  path: '+str(path)+'\n  time: 1d\n')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['-f', str(config)]), 1)
            path.write_bytes(b'ok')
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(['-f', str(config), '-x']), 0)
                self.assertIn('All backups are fine', output.getvalue())

    def test_dir_and_dod(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root/'old'; old.write_bytes(b'x'*100)
            os.utime(old, (time.time()-100,)*2)
            new = root/'new'; new.write_bytes(b'x')
            options = {'type':'dir', 'path':str(root), 'time':'1d', 'min-size':50}
            self.assertEqual(audit({'a':options})[0][1].err, 'Too small')
            folder=root/'nested'; folder.mkdir(); (folder/'a').write_bytes(b'x'*64)
            options['type']='dod'
            self.assertTrue(audit({'a':options})[0][1].ok)

    def test_petabytes(self):
        self.assertEqual(bytes_to_iso(10**15), '1.0 PB')


class CommandTests(unittest.TestCase):
    def test_real_local_argument_boundaries(self):
        value = 'space; $(echo NOT_EXECUTED)'
        self.assertEqual(run([sys.executable,'-c','import sys; print(sys.argv[1])',value]).strip(), value)

    def test_secret_environment_and_remote_stdin(self):
        secret = 'a b; $c"d'
        with patch('bakauditor.command.subprocess.run') as mocked:
            mocked.return_value = subprocess.CompletedProcess([],0,'ok','')
            run(['borg','info','repo with spaces'], password=secret, password_var='BORG_PASSPHRASE')
            args, kw = mocked.call_args
            self.assertNotIn(secret, repr(args))
            self.assertEqual(kw['env']['BORG_PASSPHRASE'],secret)
            run(['borg','info','repo with spaces'], ssh='-p 222 user@host', password=secret, password_var='BORG_PASSPHRASE')
            args, kw = mocked.call_args
            self.assertNotIn(secret, repr(args))
            self.assertEqual(kw['input'],secret+'\n')
            self.assertIn("'repo with spaces'",args[0][-1])

    def test_remote_shell_quoting_and_password_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            ssh = Path(directory) / 'ssh'
            ssh.write_text('#!/bin/sh\nfor last; do :; done\nexec /bin/sh -c "$last"\n')
            ssh.chmod(0o755)
            secret = r"spaces ; $(not-a-command) ' \\\ end"
            with patch.dict(os.environ, {'PATH': directory + os.pathsep + os.environ['PATH']}):
                output = run(['/bin/sh', '-c', 'printf "%s" "$BORG_PASSPHRASE"'],
                             ssh='test-host', password=secret, password_var='BORG_PASSPHRASE')
                self.assertEqual(output, secret)

    def test_timeout_and_failures(self):
        with self.assertRaisesRegex(RuntimeError,'timed out'):
            run([sys.executable,'-c','import time; time.sleep(2)'],timeout=0.02)
        with self.assertRaisesRegex(RuntimeError,'exit 7'):
            run([sys.executable,'-c','raise SystemExit(7)'])


class BackendTests(unittest.TestCase):
    def test_restic_latest_and_pinned_stats(self):
        snapshots = [{'id':'new','time':'2026-01-02T00:00:00Z'},
                     {'id':'old','time':'2026-01-01T00:00:00Z'}]
        with patch('bakauditor.plugins.restic.run',side_effect=[json.dumps(snapshots),'{"total_size": 2000}']) as mocked:
            result=restic.check(repo='sftp:user@host:/bak',host='one',tag=['daily'],**{'min-size':'1K'})
            self.assertTrue(result.ok)
            self.assertEqual(result.size,2000)
            self.assertEqual(mocked.call_args_list[1].args[0][-1],'new')
            self.assertIn('--host',mocked.call_args_list[0].args[0])

    def test_restic_no_snapshots_small_and_bad_json(self):
        with patch('bakauditor.plugins.restic.run',return_value='[]'):
            self.assertFalse(restic.check(repo='/bak').ok)
        with patch('bakauditor.plugins.restic.run',side_effect=['[{"id":"x","time":"2026-01-01T00:00:00Z"}]','{"total_size":0}']):
            self.assertEqual(restic.check(repo='/bak',**{'min-size':1}).err,'Too small')
        for output in ('not json', '{}'):
            with patch('bakauditor.plugins.restic.run',return_value=output):
                self.assertFalse(audit({'a':dict(type='restic',repo='/bak',time='1d')})[0][1].ok)

    def test_failure_continues_and_redacts(self):
        with patch('bakauditor.plugins.restic.run',side_effect=RuntimeError('SECRET')):
            rows=audit({'a':dict(type='restic',repo='/bak',time='1d'),
                        'b':dict(type='restic',repo='/other',time='1d')})
            self.assertEqual(len(rows),2)
            self.assertTrue(all(not r.ok for _,r in rows))
            self.assertNotIn('SECRET',repr(rows))

    def test_borg_archive_timestamp(self):
        with patch('bakauditor.plugins.borg.get_borg',return_value=json.dumps({'repository':{'last_modified':'2030-01-01T00:00:00Z'},'archives':[{'start':'2020-01-01T00:00:00Z','stats':{'original_size':50}}]})):
            self.assertEqual(audit({'a':dict(type='borg',repo='/bak',time='1d')})[0][1].err,'Outdated')

    def test_zfs_latest_native_and_named(self):
        output='pool/a@one\t100\t1000\npool/a@two\t200\t2000\npool/ab@other\t1\t3000\n'
        with patch('bakauditor.plugins.zfs.run',return_value=output):
            result=zfs.check(fs='pool/a')
            self.assertEqual((result.time,result.size),(2000,200))
        with patch('bakauditor.plugins.zfs.run',return_value='pool/a@2020-01-01\t1\t1000\n'):
            self.assertTrue(zfs.check(fs='pool/a',**{'time-fmt':'%Y-%m-%d'}).ok)




@unittest.skipUnless(os.environ.get('RESTIC_TEST_BIN'), 'Set RESTIC_TEST_BIN for real repository smoke tests')
class ResticIntegration(unittest.TestCase):
    def test_real_repository_filters_stats_and_password(self):
        binary = os.environ['RESTIC_TEST_BIN']
        with tempfile.TemporaryDirectory(prefix='baka-restic-') as directory:
            root=Path(directory); source=root/'source'; source.mkdir()
            (source/'data').write_bytes(b'backup contents'*1024)
            repo=str(root/'repository')
            env={**os.environ, 'RESTIC_PASSWORD':'test password ; $not-a-command',
                 'PATH':str(Path(binary).parent)+os.pathsep+os.environ['PATH']}
            def command(*args):
                return subprocess.run([binary,'-r',repo,*args],env=env,
                                      capture_output=True,text=True,check=True,timeout=60)
            command('init')
            with patch.dict(os.environ,env):
                self.assertFalse(restic.check(repo=repo).ok)
            command('backup','--host','testhost','--tag','daily',str(source))
            with patch.dict(os.environ,env):
                result=restic.check(repo=repo,host='testhost',tag='daily',**{'min-size':'1K'})
                self.assertTrue(result.ok)
                self.assertEqual(result.size,len(b'backup contents')*1024)
                self.assertFalse(restic.check(repo=repo,host='another').ok)
                self.assertFalse(restic.check(repo=repo,**{'min-size':'1G'}).ok)
                checks={'a':dict(type='restic',repo=repo,password='wrong',time='1d')}
                self.assertFalse(audit(checks)[0][1].ok)


if __name__ == "__main__": unittest.main()
