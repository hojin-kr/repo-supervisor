"""Synthetic state transitions; no live adapter, mount probe, process, or relocation."""
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/repo-supervisor/scripts'
sys.path.insert(0, str(SCRIPTS))
import coordination_policy as p


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'source'
        self.repo.mkdir()
        for args in (['init', '-q'], ['config', 'user.name', 'Example'],
                     ['config', 'user.email', 'author@example.com']):
            subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)
        (self.repo / 'input').write_text('synthetic')
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'commit', '-qm', 'Synthetic baseline'], check=True)
        self.ledger = p.LocalLedger(self.repo, self.base / 'private-state')
        self.policy = p.ProviderPolicy(frozenset({'provider/model-a', 'provider/model-b'}),
            frozenset({'bounded-edit'}), 'credit', 1000, Decimal('0'), 30,
            frozenset({'auxiliary'}), 2, 5)
        self.quote = p.Quote('provider/model-a', frozenset({'bounded-edit'}), Decimal('0'),
                             Decimal('0'), 'credit', 1000, 90, 120)
        self.claims = p.ProviderClaims(self.ledger, self.policy)
        self.mount = self.base / 'synthetic-volume'
        self.mount.mkdir()
        self.volume = p.VolumeObservation(self.mount, 'volume-a', True, True,
                                           frozenset({'permissions', 'extended-metadata'}), 1000, 100)
        self.storage = p.StoragePolicy('volume-a', frozenset({'permissions', 'extended-metadata'}), 10, 100)

    def begin(self, task='unit-a', now=100, resume=False, quote=None, live=False):
        return self.claims.begin(task, hashlib.sha256(task.encode()).hexdigest(), 'writer-a', quote or self.quote,
                                {'auxiliary': self.quote}, now, resume=resume, live=live)

    def finish(self, run, outcome, stopped=True, now=100):
        self.claims.finish('unit-a', run, 'provider/model-a', outcome, stopped, now,
                           stop_receipt_sha256='b' * 64 if stopped else None)

    def state(self):
        with self.ledger.transaction() as state:
            return json.loads(json.dumps(state))

    def test_policy_denial_is_terminal_not_quota(self):
        self.assertEqual(p.classify(429, 'POLICY_DENIED'), 'policy_denied')
        run = self.begin()
        self.finish(run, 'policy_denied')
        self.assertEqual(self.state()['tasks']['unit-a']['status'], 'policy_denied')
        for quote in (self.quote, replace(self.quote, model='provider/model-b')):
            with self.assertRaisesRegex(p.Denied, 'policy_denied_terminal'):
                self.begin(now=106, resume=True, quote=quote)
        self.assertEqual(len(self.state()['tasks']['unit-a']['attempts']), 1)

    def test_denial_latches_ledger_and_stop_confirmation_requires_receipt(self):
        run = self.begin()
        with self.assertRaisesRegex(p.Denied, 'stop_receipt_required'):
            self.claims.finish('unit-a', run, self.quote.model, 'worker_done', True, 100)
        self.finish(run, 'policy_denied')
        with self.assertRaisesRegex(p.Denied, 'policy_denied_terminal'):
            self.begin(task='different-task', now=106)

    def test_classifier_never_uses_quota_prose(self):
        for status, code, expected in [(401, 'QUOTA_EXHAUSTED', 'auth'),
                (403, 'QUOTA_EXHAUSTED', 'forbidden'), (429, None, 'unknown'),
                (429, 'RATE_LIMIT', 'quota'), (None, 'NETWORK_TIMEOUT', 'network'),
                (None, 'TEST_FAILED', 'test_failed')]:
            self.assertEqual(p.classify(status, code), expected)

    def test_single_workspace_writer_and_duplicate_result(self):
        run = self.begin()
        with self.assertRaisesRegex(p.Denied, 'writer_already_claimed'):
            self.begin(task='unit-b')
        self.finish(run, 'worker_done')
        with self.assertRaisesRegex(p.Denied, 'not_resumable'):
            self.begin()
        with self.assertRaisesRegex(p.Denied, 'receipt_identity_mismatch'):
            self.finish(run, 'worker_done')

    def test_new_alias_cannot_replay_the_same_contract(self):
        run = self.begin()
        self.finish(run, 'worker_done')
        with self.assertRaisesRegex(p.Denied, 'duplicate_contract'):
            self.claims.begin('different-alias', hashlib.sha256(b'unit-a').hexdigest(),
                              'writer-b', self.quote, {'auxiliary': self.quote}, 106)

    def test_excessive_cooldown_does_not_release_the_claim(self):
        run = self.begin()
        with self.assertRaisesRegex(p.Denied, 'cooldown'):
            self.claims.finish('unit-a', run, self.quote.model, 'quota', True, 100, 4000, 'b' * 64)
        self.assertEqual(self.state()['tasks']['unit-a']['status'], 'claimed')

    def test_unknown_cost_expiry_exact_model_and_auxiliaries_block(self):
        for quote in (replace(self.quote, input_rate=None), replace(self.quote, expires_at=100),
                      replace(self.quote, observed_at=1), replace(self.quote, model='unlisted/model'),
                      replace(self.quote, output_rate=Decimal('NaN')),
                      replace(self.quote, capabilities=frozenset())):
            with self.assertRaises(p.Denied):
                self.begin(quote=quote)
        with self.assertRaisesRegex(p.Denied, 'auxiliary'):
            self.claims.begin('unit-a', 'a' * 64, 'writer-a', self.quote, {}, 100)
        with self.assertRaisesRegex(p.Denied, 'cost'):
            self.claims.begin('unit-a', 'a' * 64, 'writer-a', self.quote,
                              {'auxiliary': replace(self.quote, input_rate=Decimal('1'))}, 100)
        self.assertFalse(self.state()['tasks'])

    def test_quota_units_and_meaning_are_explicit(self):
        self.assertEqual(p.remaining_fraction(Decimal('25'), unit='percent', meaning='used'), Decimal('.75'))
        self.assertEqual(p.remaining_fraction(Decimal('.25'), unit='fraction', meaning='remaining'), Decimal('.25'))
        self.assertEqual(p.remaining_fraction(Decimal('1'), unit='fraction', meaning='remaining'), Decimal('1'))
        self.assertEqual(p.remaining_fraction(Decimal('100'), unit='percent', meaning='used'), Decimal('0'))

    def test_unknown_quota_units_or_values_are_not_guessed(self):
        for unit, meaning, value in [('unknown', 'remaining', Decimal('1')),
                ('percent', 'unknown', Decimal('1')), ('fraction', 'used', Decimal('25')),
                ('fraction', 'remaining', Decimal('NaN')), ('fraction', 'used', True)]:
            with self.assertRaises(p.Denied):
                p.remaining_fraction(value, unit=unit, meaning=meaning)

    def test_installed_policy_module_imports_without_a_provider_or_private_config(self):
        installed = self.base / 'installed'
        shutil.copytree(SCRIPTS.parent, installed)
        done = subprocess.run([sys.executable, '-c',
            "import sys; sys.path.insert(0, sys.argv[1]); import coordination_policy as p; "
            "assert p.classify(429, 'POLICY_DENIED') == 'policy_denied'", str(installed / 'scripts')],
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, '')

    def test_model_catalog_must_be_exact_and_typed(self):
        for catalog in ('provider/model-a', frozenset({'provider/*'}), frozenset()):
            self.claims.policy = replace(self.policy, models=catalog)
            with self.assertRaisesRegex(p.Denied, 'exact_model_policy'):
                self.begin()

    def test_live_is_never_activated_by_a_flag(self):
        with self.assertRaisesRegex(p.Denied, 'live_adapter_unverified'):
            self.begin(live=True)
        self.assertFalse(self.state()['tasks'])

    def test_partial_and_test_failure_are_not_accepted_or_resumed(self):
        for outcome in ('partial', 'test_failed', 'auth', 'forbidden', 'unknown'):
            with self.subTest(outcome=outcome):
                task = 'task-' + outcome.replace('_', '-')
                run = self.begin(task=task)
                self.claims.finish(task, run, self.quote.model, outcome, True, 100,
                                   stop_receipt_sha256='b' * 64)
                with self.assertRaisesRegex(p.Denied, 'not_resumable'):
                    self.begin(task=task, resume=True, now=106)
                self.assertEqual(self.state()['tasks'][task]['status'], outcome)

    def test_receipt_identity_and_unconfirmed_stop_keep_writer(self):
        run = self.begin()
        with self.assertRaisesRegex(p.Denied, 'identity'):
            self.finish('different-run', 'worker_done')
        self.finish(run, 'network', stopped=False)
        self.assertEqual(self.state()['tasks']['unit-a']['status'], 'stop_unknown')
        with self.assertRaisesRegex(p.Denied, 'writer_already_claimed'):
            self.begin(task='unit-b')

    def test_cooldown_budget_policy_drift_and_attempt_receipts_persist(self):
        run = self.begin()
        self.finish(run, 'network')
        with self.assertRaisesRegex(p.Denied, 'cooldown'):
            self.begin(now=102, resume=True)
        with self.assertRaisesRegex(p.Denied, 'exact_model'):
            self.begin(now=106, resume=True, quote=replace(self.quote, model='provider/model-b'))
        run2 = self.begin(now=106, resume=True)
        self.finish(run2, 'network', now=106)
        with self.assertRaisesRegex(p.Denied, 'budget_exhausted'):
            self.begin(now=112, resume=True)
        attempts = self.state()['tasks']['unit-a']['attempts']
        self.assertEqual([a['receipt']['outcome'] for a in attempts], ['network', 'network'])
        self.claims.policy = replace(self.policy, max_attempts=3)
        with self.assertRaisesRegex(p.Denied, 'drift'):
            self.begin(now=112, resume=True)

    def test_checkpoint_change_blocks_handoff(self):
        run = self.begin()
        self.finish(run, 'stopped')
        (self.repo / 'input').write_text('changed by another writer')
        with self.assertRaisesRegex(p.Denied, 'drift'):
            self.begin(now=106, resume=True)

    def test_quota_may_route_only_after_stopped_checkpoint_and_cooldown(self):
        run = self.begin()
        self.finish(run, 'quota')
        self.begin(now=106, resume=True, quote=replace(self.quote, model='provider/model-b'))
        self.assertEqual(self.state()['tasks']['unit-a']['model'], 'provider/model-b')

    def test_local_lock_is_exclusive_and_crash_lock_is_not_expired(self):
        with self.ledger.transaction():
            with self.assertRaisesRegex(p.Denied, 'ledger_busy'):
                self.begin()
        lock = self.ledger.directory / 'lock'
        lock.mkdir()
        with self.assertRaisesRegex(p.Denied, 'ledger_busy'):
            self.begin()
        lock.rmdir()

    def test_volume_mismatch_unmounted_fake_mount_and_metadata_fail_closed(self):
        for observation in (replace(self.volume, identity='volume-b'),
                replace(self.volume, mounted=False), replace(self.volume, actual_mount=False),
                replace(self.volume, mount_root=self.base / 'not-mounted'),
                replace(self.volume, features=frozenset({'permissions'})),
                replace(self.volume, measured_at=1)):
            with self.assertRaises(p.Denied):
                p.reserve(self.ledger, 'copy-a', self.storage, observation, 100, 100)
        self.assertFalse(self.state()['reservations'])

    def test_reservations_conflict_and_release_requires_owned_stopped_operation(self):
        token = p.reserve(self.ledger, 'copy-a', self.storage, self.volume, 600, 100)
        with self.assertRaisesRegex(p.Denied, 'storage_budget_conflict'):
            p.reserve(self.ledger, 'copy-b', self.storage, self.volume, 400, 100)
        with self.assertRaises(p.Denied):
            p.release_reservation(self.ledger, 'copy-a', token, False)
        with self.assertRaises(p.Denied):
            p.release_reservation(self.ledger, 'copy-a', 'wrong-token', True)
        p.release_reservation(self.ledger, 'copy-a', token, True)
        p.reserve(self.ledger, 'copy-b', self.storage, self.volume, 800, 100)
        with self.assertRaisesRegex(p.Denied, 'duplicate_reservation'):
            p.reserve(self.ledger, 'copy-b', self.storage, self.volume, 1, 100)

    def test_no_path_escape_or_overlapping_state(self):
        (self.mount / 'link').symlink_to(self.base)
        for relative in ('../escape', '/absolute', 'link/escape', 'a/../b', 'a\\b'):
            with self.assertRaisesRegex(p.Denied, 'path_escape'):
                p.reserve(self.ledger, 'copy-a', self.storage, self.volume, 10, 100, relative)
        with self.assertRaisesRegex(p.Denied, 'overlap'):
            p.disjoint_roots(self.repo, self.repo / 'artifacts', self.ledger.directory)
        p.disjoint_roots(self.repo, self.mount / 'artifacts', self.ledger.directory)
        for relative in ('source/artifacts', 'private-state/artifacts'):
            with self.assertRaisesRegex(p.Denied, 'overlap'):
                p.reserve(self.ledger, 'copy-a', self.storage,
                          replace(self.volume, mount_root=self.base), 10, 100, relative)

    def test_private_config_and_state_are_outside_git_and_never_echoed(self):
        config = self.base / 'private.json'
        config.write_text(json.dumps({'account_alias': 'synthetic-local-account'}))
        config.chmod(0o600)
        self.assertEqual(p.private_config(self.repo, config)['account_alias'], 'synthetic-local-account')
        inside = self.repo / 'ignored-config.json'
        inside.write_bytes(config.read_bytes())
        for action in (lambda: p.private_config(self.repo, inside),
                       lambda: p.LocalLedger(self.repo, self.repo / '.local-state')):
            with self.assertRaises(p.Denied) as caught:
                action()
            self.assertNotIn(str(self.repo), str(caught.exception))
            self.assertNotIn('synthetic-local-account', str(caught.exception))
        config.chmod(0o644)
        with self.assertRaises(p.Denied):
            p.private_config(self.repo, config)

    def test_private_state_cannot_be_placed_in_another_git_checkout(self):
        other = self.base / 'other-checkout'
        other.mkdir()
        subprocess.run(['git', '-C', str(other), 'init', '-q'], check=True, capture_output=True)
        with self.assertRaisesRegex(p.Denied, 'inside_git'):
            p.LocalLedger(self.repo, other / 'state')
        self.assertFalse((other / 'state').exists())

    def test_inventory_and_recovery_precede_reference_no_deletion_or_backup_claim(self):
        inventory = p.Inventory('a' * 64, 'b' * 64, 2, 100)
        result = p.relocation_decision(inventory, inventory, inventory, inventory, True)
        self.assertTrue(result['keep_original'])
        self.assertFalse(result['may_delete'])
        self.assertFalse(result['is_backup'])
        self.assertEqual(result['logical_bytes'], 100)
        self.assertIsNone(result['actual_reclaimed_bytes'])
        for bad in (replace(inventory, bytes=99), replace(inventory, count=1),
                    replace(inventory, content_sha256='c' * 64),
                    replace(inventory, metadata_sha256='d' * 64)):
            with self.assertRaises(p.Denied):
                p.relocation_decision(inventory, inventory, bad, inventory, True)
        with self.assertRaises(p.Denied):
            p.relocation_decision(inventory, inventory, inventory, inventory, False)
        with self.assertRaises(p.Denied):
            p.relocation_decision(inventory, replace(inventory, bytes=101), inventory, inventory, True)


if __name__ == '__main__':
    unittest.main()
