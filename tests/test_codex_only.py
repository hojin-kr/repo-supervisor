"""Guard the supported Codex-only surface and retained storage boundary."""
import ast
from pathlib import Path
import sys
import unittest

SKILL = Path(__file__).resolve().parents[1] / 'skills/repo-supervisor'
sys.path.insert(0, str(SKILL / 'scripts'))
import coordination_policy as policy


class CodexOnly(unittest.TestCase):
    def test_retired_routing_api_is_absent_while_storage_remains(self):
        for name in ('Quote', 'ProviderPolicy', 'ProviderClaims', 'classify', 'remaining_fraction'):
            self.assertFalse(hasattr(policy, name), name)
        for name in ('private_config', 'LocalLedger', 'StoragePolicy', 'reserve',
                     'release_reservation', 'relocation_decision'):
            self.assertTrue(callable(getattr(policy, name)), name)

    def test_storage_policy_has_no_execution_or_network_dependencies(self):
        tree = ast.parse((SKILL / 'scripts/coordination_policy.py').read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module.split('.')[0])
        self.assertEqual(imported, {'contextlib', 'dataclasses', 'json', 'math', 'os',
                                    'pathlib', 're', 'tempfile', 'uuid'})

    def test_active_guides_require_codex_and_do_not_link_retired_policy(self):
        for name in ('SKILL.md', 'references/execution-protocol.md', 'references/storage-policy.md'):
            text = (SKILL / name).read_text()
            self.assertIn('ChatGPT Codex', text)
        for path in SKILL.rglob('*'):
            if path.is_file():
                self.assertNotIn('provider-storage-policy.md', path.read_text())
                self.assertNotIn('ProviderClaims', path.read_text())
        self.assertFalse((SKILL / 'references/provider-storage-policy.md').exists())


if __name__ == '__main__':
    unittest.main()
