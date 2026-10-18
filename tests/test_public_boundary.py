"""A limited text-pattern gate complements manual public diff review."""
from pathlib import Path
import json
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'personal-email': r'\b[A-Za-z0-9._%+-]+@(?!example\.com\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    'home-path': r'/(?:Users|home)/[^\s]+',
    'private-key': r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
    'credential': r'gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,}',
    'volume-identifier': r'\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b',
    'private-domain': r'\b[a-zA-Z0-9-]+\.(?:internal|corp|local)\b',
}


def violations(content):
    return [category for category, pattern in PATTERNS.items() if re.search(pattern, content)]


class PublicBoundary(unittest.TestCase):
    def test_synthetic_private_values_are_detected_without_real_identifiers(self):
        samples = ['person' + '@' + 'invalid.test', '/' + 'Users' + '/example/private',
                   'ghp_' + 'a' * 30, '12345678' + '-1234' * 3 + '-123456789abc',
                   'host' + '.' + 'internal']
        for content in samples:
            self.assertTrue(violations(content))
        self.assertFalse(violations('author@example.com and volume-a'))

    def test_public_tree_has_no_private_text_patterns_or_raw_log_files(self):
        names = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z',
                    '--cached', '--others', '--exclude-standard']).decode().split('\0')
        for name in filter(None, names):
            with self.subTest(file=name):
                self.assertNotIn(Path(name).suffix, {'.log', '.jsonl'})
                self.assertFalse(set(Path(name).parts) & {'.runtime', 'private', 'evidence', 'runtime-state'})
                if name.endswith('.json'):
                    def check_keys(value):
                        if isinstance(value, dict):
                            self.assertFalse(set(value) & {'stdout', 'stderr', 'account_id',
                                                           'access_token', 'mount_uuid', 'raw_logs'})
                            for item in value.values():
                                check_keys(item)
                        elif isinstance(value, list):
                            for item in value:
                                check_keys(item)
                    check_keys(json.loads((ROOT / name).read_text()))
                self.assertFalse(violations((ROOT / name).read_text()), name)
