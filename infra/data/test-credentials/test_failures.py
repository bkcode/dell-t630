#!/usr/bin/env python3
"""Synthetic credentials only, generated in memory. Native/SQL/API/IO are mocked."""
import base64
import copy
import contextlib
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location('credentials_under_test', Path(__file__).with_name('worker.py'))
w = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(w)

class CredentialFailureTests(unittest.TestCase):
    def mysql_failure(self, failure):
        old, new = secrets.token_hex(12), secrets.token_hex(12)
        accounts = {h: {'primary': old, 'secondary': None} for h in ['%', 'localhost']}
        file_value = [old.encode()+b'\n']; fired = [False]; auth_choices = []
        def sql(query, password, tcp=False):
            account = accounts['%' if tcp else 'localhost']
            auth_choices.append('old' if password == old else 'new')
            if password not in (account['primary'], account['secondary']): raise RuntimeError('synthetic-auth-failed')
            if query.startswith('SELECT JSON_ARRAY'):
                return '\n'.join(json.dumps(['root', h, 'caching_sha2_password', '', 'N', int(accounts[h]['secondary'] is not None)]) for h in ['%', 'localhost'])
            if query.startswith('SELECT @@'): return '0\tTLSv1.2,TLSv1.3'
            if query.startswith('SELECT CURRENT_USER'): return 'root@%' if tcp else 'root@localhost'
            for statement in query.split(';'):
                if not statement.strip(): continue
                host = re.search(r"'root'@'([^']+)'", statement)[1]
                account = accounts[host]
                if 'IDENTIFIED WITH' in statement:
                    value = new if 'RETAIN CURRENT PASSWORD' in statement else old
                    account['secondary'] = account['primary'] if 'RETAIN CURRENT PASSWORD' in statement else account['secondary']
                    account['primary'] = value
                    if failure == 'second-alter-after-commit' and host == 'localhost' and 'RETAIN' in statement and not fired[0]:
                        fired[0] = True; raise RuntimeError('synthetic-alter-ack-failed')
                elif 'DISCARD OLD PASSWORD' in statement:
                    account['secondary'] = None
                    if failure == 'second-discard-after-commit' and host == 'localhost' and not fired[0]:
                        fired[0] = True; raise RuntimeError('synthetic-discard-ack-failed')
                else: self.fail('unexpected mocked statement class')
            return ''
        def inplace(path, data, identity):
            if failure == 'secret-write' and data.strip() == new.encode() and not fired[0]:
                fired[0] = True; raise RuntimeError('synthetic-file-failed')
            file_value[0] = data
        with patch.object(w, 'sql', side_effect=sql), patch.object(w, 'inplace', side_effect=inplace), patch.object(w, 'put_private') as report:
            with self.assertRaises(RuntimeError): w.mysql_change({'mysql_password': new}, old.encode()+b'\n', (), Path('/synthetic-work'))
            report.assert_not_called()
        self.assertTrue(fired[0])
        self.assertTrue(all(a['primary'] == old and a['secondary'] is None for a in accounts.values()))
        self.assertTrue(file_value[0].strip() == old.encode())
        return auth_choices

    def test_mysql_ambiguous_second_account_change_is_compensated(self):
        self.mysql_failure('second-alter-after-commit')

    def test_mysql_after_discard_can_recover_using_new_connection(self):
        choices = self.mysql_failure('second-discard-after-commit')
        self.assertIn('new', choices)

    def test_mysql_secret_failure_restores_credentials_and_file(self):
        self.mysql_failure('secret-write')

    def test_redis_broken_original_connection_uses_fallback_and_restores_all_files(self):
        old, new = secrets.token_hex(12), secrets.token_hex(12)
        passwords = {old}; secret_file = [old.encode()+b'\n']; conf_before = b'port 6379\nrequirepass '+old.encode()+b'\n'
        conf_file = [conf_before]; clients = []; failed = [False]
        class Client:
            def __init__(self, cfg, auth=True):
                self.ordinal = len(clients); clients.append(self)
                self.authenticated = False
                if auth: self.call('AUTH', secret_file[0].decode().strip())
            def call(self, *args):
                if args[0] == 'AUTH':
                    if args[1] not in passwords: raise RuntimeError('synthetic-auth-failed')
                    self.authenticated = True; return 'OK'
                if not self.authenticated: raise RuntimeError('synthetic-not-authenticated')
                if args[0] == 'PING': return 'PONG'
                if args[:3] == ('ACL', 'SETUSER', 'default'): passwords.add(args[3][1:]); return 'OK'
                if args[:3] == ('CONFIG', 'SET', 'requirepass'):
                    if self.ordinal == 0 and failed[0]: raise RuntimeError('synthetic-connection-broken')
                    passwords.clear(); passwords.add(args[3]); return 'OK'
                raise RuntimeError('unexpected-synthetic-command')
            def close(self): pass
        def run(args, data=None, **kw):
            if args[-2:] == ['cat', '/run/dell-redis/redis.conf']: return conf_before
            if data is not None:
                if data != conf_before and not failed[0]: failed[0] = True; raise RuntimeError('synthetic-runtime-file-failed')
                conf_file[0] = data; return b''
            raise RuntimeError('unexpected-synthetic-native')
        module = types.SimpleNamespace(Redis=Client)
        spec = types.SimpleNamespace(loader=types.SimpleNamespace(exec_module=lambda m: None))
        acl = lambda: {'passwords': [hashlib.sha256(v.encode()).hexdigest() for v in passwords], 'flags': ['on'], 'commands': '+@all'}
        with patch.object(w.importlib.util, 'spec_from_file_location', return_value=spec), patch.object(w.importlib.util, 'module_from_spec', return_value=module), patch.object(w, 'redis_acl', side_effect=acl), patch.object(w, 'run', side_effect=run), patch.object(w, 'inplace', side_effect=lambda p, data, identity: secret_file.__setitem__(0, data)), patch.object(w, 'put_private'):
            with self.assertRaises(RuntimeError): w.redis_change({'redis_password': new}, old.encode()+b'\n', (), Path('/synthetic-work'))
        self.assertTrue(failed[0] and len(clients) >= 3)
        self.assertTrue(passwords == {old} and secret_file[0].strip() == old.encode() and conf_file[0] == conf_before)

    def test_rabbit_persistent_hash_and_old_accounts_are_preserved(self):
        old, new, app = [secrets.token_hex(12) for _ in range(3)]
        runtime_users = {'old_admin': old, 'application': app}; vhosts = {'/finger-test'}; permissions = {}; stored = {}
        class Rabbit:
            def __init__(self, user, password): self.user, self.password = user, password
            def api(self, method, path, data=None, **kwargs):
                if runtime_users.get(self.user) != self.password: raise RuntimeError('synthetic-auth-failed')
                if method == 'GET':
                    if path == '/api/users': return [{'name': u} for u in runtime_users]
                    if path == '/api/vhosts': return [{'name': v} for v in vhosts]
                    if path == '/api/whoami': return {'name': self.user}
                if path.startswith('/api/users/'):
                    runtime_users['admin'] = data['password']; return None
                if path.startswith('/api/vhosts/'):
                    vhosts.add('/'); return None
                if path.startswith('/api/permissions/'):
                    permissions[path] = copy.deepcopy(data); return None
                raise RuntimeError('unexpected-synthetic-api')
        original = {'users': [{'name': 'old_admin', 'password_hash': secrets.token_hex(12)}, {'name': 'application', 'password_hash': secrets.token_hex(12)}], 'vhosts': [{'name': '/finger-test'}], 'permissions': [{'user': 'application', 'vhost': '/finger-test', 'configure': '.*', 'write': '.*', 'read': '.*'}]}
        with patch.object(w, 'Rabbit', Rabbit), patch.object(w, 'inplace', side_effect=lambda p, data, identity: stored.__setitem__(str(p), data)), patch.object(w, 'put_private'):
            w.rabbit_change({'rabbit_user': 'admin', 'rabbit_password': new}, old.encode()+b'\n', (), b'RABBIT_ADMIN_USER=old_admin\nKEEP=value\n', (), json.dumps(original).encode(), (), Path('/synthetic-work'))
        definition = json.loads(stored[str(w.B/'secrets/rabbit-definitions.json')])
        self.assertTrue(definition['users'][:2] == original['users'])
        entry = definition['users'][-1]; decoded = base64.b64decode(entry['password_hash'])
        self.assertTrue(decoded[4:] == hashlib.sha256(decoded[:4]+new.encode()).digest())
        self.assertTrue(runtime_users['old_admin'] == old and runtime_users['application'] == app and runtime_users['admin'] == new)
        self.assertEqual(len(permissions), 2)
        self.assertTrue(stored[str(w.B/'.env')] == b'RABBIT_ADMIN_USER=admin\nKEEP=value\n')

    def test_failing_health_is_rejected_before_credentials(self):
        rows = [{'ID': str(i), 'Image': 'synthetic', 'PID': i+1, 'Start': 'fixed', 'Running': True, 'Health': 'healthy', 'FailingStreak': 0, 'Restarts': 0, 'OOM': False} for i in range(4)]
        rows[2]['FailingStreak'] = 1; responses = [b'a b c d', *[json.dumps(r).encode() for r in rows]]
        with patch.object(w, 'run', side_effect=responses):
            with self.assertRaisesRegex(RuntimeError, '^healthy-base-required$'): w.frames()

    def test_existing_transaction_lock_refuses_before_any_credential_action(self):
        with tempfile.TemporaryDirectory(prefix='test-credentials-lock-') as tmp:
            state = Path(tmp).resolve(); state.chmod(0o700); lock = state/'.transaction.lock'
            fd = os.open(lock, os.O_RDWR|os.O_CREAT, 0o600); fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            actual_stat, actual_fstat = Path.stat, os.fstat
            def root_stat(p, *a, **kw):
                item = actual_stat(p, *a, **kw)
                if p == state:
                    fields = list(item); fields[4] = 0; return os.stat_result(fields)
                return item
            def root_fstat(number):
                item = actual_fstat(number); fields = list(item); fields[4] = 0; return os.stat_result(fields)
            try:
                with patch.object(w, 'STATE', state), patch.object(w.os, 'geteuid', return_value=0), patch.object(w.os, 'umask'), patch.object(w.socket, 'gethostname', return_value='data-test'), patch.object(Path, 'stat', root_stat), patch.object(w.os, 'fstat', side_effect=root_fstat), patch.object(w, 'run', return_value=json.dumps({'filesystems': [{'uuid': 'dd1773f9-aa48-4401-a9c8-caf0f66845f3'}]}).encode()), patch.object(sys, 'argv', ['worker', '--run-id', 'a'*32]), patch.object(w, 'rabbit_change') as rabbit:
                    with self.assertRaises(BlockingIOError): w.main()
                    rabbit.assert_not_called()
            finally: os.close(fd)

if __name__ == '__main__': unittest.main()
