"""Black-box synthetic checks for the installed helper's evidence contract."""
import json
import re
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'skills/repo-supervisor/scripts/verify.py'
TEMPLATE = HELPER.parent.parent / 'assets/verification-packet.json'


class VerificationCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Example')
        self.git('config', 'user.email', 'author@example.com')
        (self.repo / 'record.txt').write_text('saved-title\n')
        self.git('add', 'record.txt')
        self.git('commit', '-qm', 'Synthetic baseline')
        self.packet_path = self.base / 'packet.json'
        self.report = self.base / 'report.json'
        self.packet = {
            'version': 1, 'objective': 'Read the saved record through a CLI',
            'inputs': ['record.txt'], 'write_scope': ['record.txt'],
            'invariants': ['Saved title is observable'], 'environment': 'python-fixture-v1',
            'checks': [{
                'id': 'read-record', 'invariant': 'Saved title is observable',
                'argv': [sys.executable, '-c',
                         "from pathlib import Path; print(Path('record.txt').read_text(), end='')"],
                'expected_exit': 0, 'stdout_contains': ['saved-title'], 'timeout_seconds': 5
            }]
        }

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.PIPE)

    def call(self, action='run', environment='python-fixture-v1', report=None):
        self.packet_path.write_text(json.dumps(self.packet))
        return subprocess.run([sys.executable, str(HELPER), action, str(self.packet_path),
                               '--repo', str(self.repo), '--report', str(report or self.report),
                               '--environment', environment], capture_output=True, text=True)

    def assert_blocked(self, result):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('BLOCKED', result.stdout + result.stderr)

    def test_real_cli_run_and_read_only_recheck(self):
        self.assertEqual(self.call().returncode, 0)
        before = self.report.read_bytes()
        self.assertEqual(self.call('check').returncode, 0)
        self.assertEqual(before, self.report.read_bytes())
        data = json.loads(before)
        self.assertEqual(data['observations'][0]['stdout'], 'saved-title\n')
        self.assertEqual(data['before']['revision'], self.git('rev-parse', 'HEAD').decode().strip())

    def test_stale_source_and_file_mode_rejected(self):
        for change in ('bytes', 'mode', 'untracked'):
            with self.subTest(change=change):
                self.report.unlink(missing_ok=True)
                path = self.repo / 'record.txt'
                path.write_text('saved-title\n')
                path.chmod(0o644)
                self.assertEqual(self.call().returncode, 0)
                if change == 'bytes':
                    path.write_text('different-title\n')
                elif change == 'mode':
                    path.chmod(0o755)
                else:
                    (self.repo / 'new-input').write_text('new')
                self.assert_blocked(self.call('check'))

    def test_new_commit_invalidates_old_evidence(self):
        self.assertEqual(self.call().returncode, 0)
        self.git('commit', '--allow-empty', '-qm', 'New candidate')
        self.assert_blocked(self.call('check'))

    def test_packet_or_environment_change_rejected(self):
        self.assertEqual(self.call().returncode, 0)
        self.packet['objective'] = 'A changed requirement'
        self.assert_blocked(self.call('check'))
        self.assert_blocked(self.call('check', environment='other-runtime'))

    def test_nonzero_or_wrong_output_fails_even_when_status_forged(self):
        for code in ("print('wrong')", "print('saved-title'); raise SystemExit(3)"):
            with self.subTest(code=code):
                self.report.unlink(missing_ok=True)
                self.packet['checks'][0]['argv'] = [sys.executable, '-c', code]
                self.assert_blocked(self.call())
                data = json.loads(self.report.read_text())
                data['observations'][0]['status'] = 'PASS'
                self.report.write_text(json.dumps(data))
                self.assert_blocked(self.call('check'))

    def test_manual_missing_tool_timeout_are_not_run(self):
        for argv in (None, ['missing-synthetic-executable'],
                     [sys.executable, '-c', 'import time; time.sleep(2)']):
            with self.subTest(argv=argv):
                self.report.unlink(missing_ok=True)
                self.packet['checks'][0]['argv'] = argv
                self.packet['checks'][0]['timeout_seconds'] = 1
                self.assert_blocked(self.call())
                self.assertEqual(json.loads(self.report.read_text())['observations'][0]['status'], 'NOT RUN')

    def test_missing_duplicate_or_extra_evidence_is_rejected(self):
        self.assertEqual(self.call().returncode, 0)
        original = json.loads(self.report.read_text())
        row = original['observations'][0]
        for rows in ([], [row, row], [dict(row, id='other')]):
            with self.subTest(rows=rows):
                original['observations'] = rows
                self.report.write_text(json.dumps(original))
                self.assert_blocked(self.call('check'))

    def test_schema_does_not_offer_skip_or_optional_bypass(self):
        original = json.loads(json.dumps(self.packet))
        for mutate in (
            lambda p: p.update(checks=[]),
            lambda p: p['checks'][0].update(required=False),
            lambda p: p['checks'][0].update(expected_exit=True),
            lambda p: p['checks'][0].update(stdout_contains=[]),
            lambda p: p['invariants'].append('uncovered invariant'),
            lambda p: p['checks'].append(dict(p['checks'][0])),
        ):
            with self.subTest(mutate=mutate):
                self.packet = json.loads(json.dumps(original))
                mutate(self.packet)
                self.assert_blocked(self.call())
                self.assertFalse(self.report.exists())

    def test_source_change_remaining_at_snapshot_blocks_and_retains_evidence(self):
        self.packet['checks'][0]['argv'] = [sys.executable, '-c',
            "from pathlib import Path; Path('record.txt').write_text('changed'); print('saved-title')"]
        self.assert_blocked(self.call())
        self.assertTrue(self.report.is_file())
        data = json.loads(self.report.read_text())
        self.assertNotEqual(data['before'], data['after'])

    def test_transient_change_restored_between_snapshots_is_not_detected(self):
        self.packet['checks'][0]['argv'] = [sys.executable, '-c', """
from pathlib import Path
path = Path('record.txt')
original = path.read_bytes()
try:
    path.write_text('transient-title')
    print(path.read_text())
finally:
    path.write_bytes(original)
"""]
        self.packet['checks'][0]['stdout_contains'] = ['transient-title']
        self.assertEqual(self.call().returncode, 0)
        data = json.loads(self.report.read_text())
        self.assertEqual(data['before'], data['after'])
        self.assertEqual(data['observations'][0]['stdout'], 'transient-title\n')
        self.assertEqual((self.repo / 'record.txt').read_text(), 'saved-title\n')
        self.assertEqual(self.call('check').returncode, 0)

    def test_report_is_external_and_never_overwritten(self):
        self.assert_blocked(self.call(report=self.repo / 'evidence.json'))
        self.assertFalse((self.repo / 'evidence.json').exists())
        self.assertEqual(self.call().returncode, 0)
        original = self.report.read_bytes()
        self.assert_blocked(self.call())
        self.assertEqual(self.report.read_bytes(), original)

    def test_template_fails_closed_until_real_driver_is_supplied(self):
        self.packet = json.loads(TEMPLATE.read_text())
        response = self.call(environment=self.packet['environment'])
        self.assert_blocked(response)
        self.assertIn('NOT RUN', response.stdout)

    def test_installed_package_keeps_links_and_helper_runnable(self):
        installed = self.base / 'installed-skill'
        shutil.copytree(HELPER.parent.parent, installed)
        for path in installed.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if '://' not in target and not target.startswith('#'):
                    self.assertTrue((path.parent / target.split('#')[0]).is_file(), target)
        self.packet_path.write_text(json.dumps(self.packet))
        completed = subprocess.run([
            sys.executable, str(installed / 'scripts/verify.py'), 'run', str(self.packet_path),
            '--repo', str(self.repo), '--report', str(self.report),
            '--environment', self.packet['environment']
        ], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_argv_is_not_a_shell(self):
        literal = '$(touch accidental-side-effect)'
        self.packet['checks'][0]['argv'] = [sys.executable, '-c', 'import sys; print(sys.argv[1])', literal]
        self.packet['checks'][0]['stdout_contains'] = [literal]
        self.assertEqual(self.call().returncode, 0)
        self.assertFalse((self.repo / 'accidental-side-effect').exists())

    def test_symlink_source_requires_specific_verifier(self):
        (self.repo / 'link').symlink_to(self.repo / 'record.txt')
        self.assert_blocked(self.call())
        self.assertFalse(self.report.exists())


if __name__ == '__main__':
    unittest.main()
