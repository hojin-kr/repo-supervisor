"""Synthetic storage boundaries; no mount probe, process, or relocation."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/repo-supervisor/scripts'
sys.path.insert(0, str(SCRIPTS))
import coordination_policy as p


class StorageTests(unittest.TestCase):
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
        self.mount = self.base / 'synthetic-volume'
        self.mount.mkdir()
        self.volume = p.VolumeObservation(self.mount, 'volume-a', True, True,
                                           frozenset({'permissions', 'extended-metadata'}), 1000, 100)
        self.storage = p.StoragePolicy('volume-a', frozenset({'permissions', 'extended-metadata'}), 10, 100)

    def state(self):
        with self.ledger.transaction() as state:
            return json.loads(json.dumps(state))

    def test_local_lock_is_exclusive_and_crash_lock_is_not_expired(self):
        with self.ledger.transaction():
            with self.assertRaisesRegex(p.Denied, 'ledger_busy'):
                p.reserve(self.ledger, 'copy-a', self.storage, self.volume, 100, 100)
        lock = self.ledger.directory / 'lock'
        lock.mkdir()
        with self.assertRaisesRegex(p.Denied, 'ledger_busy'):
            p.reserve(self.ledger, 'copy-a', self.storage, self.volume, 100, 100)
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

    def test_private_paths_reject_checkout_aliases_and_intermediate_links(self):
        private = self.base / 'private-bindings'
        private.mkdir(mode=0o700)
        config = private / 'binding.json'
        config.write_text('{}')
        config.chmod(0o600)
        other = self.base / 'other-checkout'
        other.mkdir()
        subprocess.run(['git', '-C', str(other), 'init', '-q'], check=True, capture_output=True)
        for index, checkout in enumerate((self.repo, other)):
            (checkout / 'binding.json').symlink_to(config)
            (checkout / 'external-dir').symlink_to(private, target_is_directory=True)
            checkout_alias = self.base / ('checkout-alias-' + str(index))
            checkout_alias.symlink_to(checkout, target_is_directory=True)
            chained_alias = self.base / ('chained-alias-' + str(index))
            chained_alias.symlink_to(checkout / 'external-dir', target_is_directory=True)
            for path in (checkout_alias / 'binding.json', chained_alias / 'binding.json'):
                with self.subTest(path_kind=path.parent.name), self.assertRaises(p.Denied):
                    p.private_config(self.repo, path)
            with self.assertRaises(p.Denied):
                p.LocalLedger(self.repo, chained_alias / 'new-state')
            self.assertFalse((private / 'new-state').exists())

    def test_external_non_git_symlink_alias_is_usable(self):
        folder = self.base / 'private-bindings'
        folder.mkdir(mode=0o700)
        config = folder / 'binding.json'
        config.write_text('{}')
        config.chmod(0o600)
        outside_alias = self.base / 'outside-alias'
        outside_alias.symlink_to(folder, target_is_directory=True)
        self.assertEqual(p.private_config(self.repo, outside_alias / 'binding.json'), {})
        self.assertEqual(p.LocalLedger(self.repo, outside_alias / 'state').directory,
                         (folder / 'state').resolve())

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
