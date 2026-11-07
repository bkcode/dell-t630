import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock

INFRA = Path(__file__).resolve().parents[2]


def load(role, filename):
    path = INFRA / role / filename
    spec = importlib.util.spec_from_file_location(role + filename.replace('.', '_'), path)
    module = importlib.util.module_from_spec(spec)
    old = list(sys.path)
    try:
        sys.path.insert(0, str(path.parent))
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old
    return module


class GuestGuards(unittest.TestCase):
    def test_pve_rejected_before_guest_or_docker_queries(self):
        for role in ('penpot', 'nexus'):
            module = load(role, 'target_guard.py')
            with self.subTest(role=role), mock.patch.object(module.Path, 'exists', return_value=True), mock.patch.object(module, 'read_json') as query:
                with self.assertRaisesRegex(RuntimeError, 'PVE host'):
                    module.verify_guest({'expected_guest_ip': '10.63.30.30'})
                query.assert_not_called()

    def test_wrong_assigned_ip_is_rejected(self):
        for role in ('penpot', 'nexus'):
            module = load(role, 'target_guard.py')
            with self.subTest(role=role), mock.patch.object(module.Path, 'exists', return_value=False), mock.patch.object(module.platform, 'system', return_value='Linux'), mock.patch.object(module.platform, 'machine', return_value='x86_64'), mock.patch.object(module.os, 'geteuid', return_value=0), mock.patch.object(module, 'read_json', return_value=[{'addr_info': [{'local': '192.168.21.22'}]}]):
                with self.assertRaisesRegex(RuntimeError, 'IP'):
                    module.verify_guest({'expected_guest_ip': '10.63.30.30'})

    def test_remote_docker_environment_rejected(self):
        for role in ('penpot', 'nexus'):
            module = load(role, 'target_guard.py')
            with self.subTest(role=role), mock.patch.dict(module.os.environ, {'DOCKER_HOST': 'tcp://example.invalid:2375'}, clear=True), mock.patch.object(module, 'read_json') as query:
                with self.assertRaisesRegex(RuntimeError, 'DOCKER_HOST'):
                    module.verify_docker()
                query.assert_not_called()

    def test_remote_context_rejected(self):
        for role in ('penpot', 'nexus'):
            module = load(role, 'target_guard.py')
            with self.subTest(role=role), mock.patch.dict(module.os.environ, {}, clear=True), mock.patch.object(module.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout='remote\n')), mock.patch.object(module, 'read_json', return_value=[{'Endpoints': {'docker': {'Host': 'ssh://another-server'}}}]):
                with self.assertRaisesRegex(RuntimeError, 'context'):
                    module.verify_docker()

    def test_forwarded_socket_wrong_daemon_is_rejected(self):
        for role in ('penpot', 'nexus'):
            module = load(role, 'target_guard.py')
            replies = [[{'Endpoints': {'docker': {'Host': 'unix:///var/run/docker.sock'}}}], {'OSType': 'linux', 'Architecture': 'x86_64', 'Name': 'another-server'}]
            with self.subTest(role=role), mock.patch.dict(module.os.environ, {}, clear=True), mock.patch.object(module.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout='default\n')), mock.patch.object(module, 'read_json', side_effect=replies), mock.patch.object(module.Path, 'exists', return_value=True), mock.patch.object(module.Path, 'stat', return_value=types.SimpleNamespace(st_mode=stat.S_IFSOCK)), mock.patch.object(module.socket, 'gethostname', return_value='assigned-guest'):
                with self.assertRaisesRegex(RuntimeError, 'daemon'):
                    module.verify_docker()

    def test_pending_storage_and_parent_escape_rejected(self):
        for role in ('penpot', 'nexus'):
            module = load(role, 'target_guard.py')
            with self.subTest(role=role):
                with self.assertRaisesRegex(RuntimeError, 'Storage mode'):
                    module.verify_storage({'storage': {'mode': 'pending'}}, {})
                with self.assertRaisesRegex(RuntimeError, 'canonical'):
                    module.canonical('/srv/dell-data/../../tmp')

    def test_source_version_change_rejected(self):
        for role in ('penpot', 'nexus'):
            module = load(role, 'source_guard.py')
            expected = {'id': 'locked', 'architecture': 'arm64', 'versions': {'version': 'one'}, 'postgres_package_version': None, 'repo_digests': ['repo@sha256:locked']}
            changed = copy.deepcopy(expected)
            changed['versions']['version'] = 'two'
            with self.subTest(role=role):
                self.assertFalse(module.same_image(changed, expected))


class RestorePreflight(unittest.TestCase):
    def test_second_nonempty_volume_prevents_first_archive_extraction(self):
        module = load('penpot', 'restore-target.py')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot, private = root / 'snapshot', root / 'private'
            snapshot.mkdir(); private.mkdir()
            (snapshot / 'postgres.dump').write_bytes(b'fixture only')
            for name in ('assets.tar', 'import-jobs.tar'):
                with tarfile.open(snapshot / name, 'w'):
                    pass
            files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.iterdir()}
            (snapshot / 'snapshot.json').write_text(json.dumps({'version': '2.18.5', 'captured_at': 'test', 'files': files}))
            config = {'services': {'penpot-postgres': {'image': 'postgres@sha256:locked'}}, 'volumes': {'penpot_assets': {'name': 'assets'}, 'penpot_import_jobs': {'name': 'jobs'}}}
            def compose(private, args, **kwargs):
                if args[0] == 'config':
                    return subprocess.CompletedProcess(args, 0, json.dumps(config))
                if args[:3] == ['ps', '-q', 'penpot-postgres']:
                    return subprocess.CompletedProcess(args, 0, 'postgres-container')
                return subprocess.CompletedProcess(args, 0, '')
            called = []
            def run(command, **kwargs):
                called.append(command)
                if 'psql' in command:
                    return subprocess.CompletedProcess(command, 0, '0\n')
                if any('src=jobs,' in x for x in command):
                    return subprocess.CompletedProcess(command, 1, '')
                return subprocess.CompletedProcess(command, 0, '')
            argv = ['restore-target.py', '--snapshot', str(snapshot), '--private-dir', str(private), '--confirm-empty-target']
            with mock.patch.object(sys, 'argv', argv), mock.patch.object(module.platform, 'system', return_value='Linux'), mock.patch.object(module.platform, 'machine', return_value='x86_64'), mock.patch.object(module, 'verify_target'), mock.patch.object(module, 'compose', side_effect=compose), mock.patch.object(module.subprocess, 'run', side_effect=run):
                with self.assertRaisesRegex(SystemExit, 'not empty'):
                    module.main()
            self.assertFalse(any('tar' in command for command in called), 'No archive may be extracted before every volume is empty')
            self.assertFalse(any('pg_restore' in command for command in called))


if __name__ == '__main__':
    unittest.main()
