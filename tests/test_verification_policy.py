from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/repo-supervisor/SKILL.md'
VERIFICATION = ROOT / 'skills/repo-supervisor/references/verification.md'
CONTINUITY = ROOT / 'skills/repo-supervisor/references/continuity-and-evidence.md'
README = ROOT / 'README.md'


class VerificationPolicyDocs(unittest.TestCase):
    def test_checks_follow_change_impact_without_fixed_regression_counts(self):
        guide = VERIFICATION.read_text()
        self.assertIn('build, executed tests, runtime behavior, visual output, evidence provenance, or whole-product acceptance', guide)
        self.assertIn('This is a scope rule, not a universal checklist or fixed test-count gate', guide)
        self.assertIn('not a product gate unless the current user or project explicitly requires that format', guide)
        self.assertIn('A documentation-only change does not by itself require repeating a full application regression', guide)
        self.assertIn('do not copy a historical repetition count, exhaustive matrix, or time limit into a new global gate', guide)

    def test_build_tool_timeout_and_shared_derived_data_do_not_duplicate_work(self):
        guide = VERIFICATION.read_text()
        self.assertIn('it does not establish that the child build or test process exited', guide)
        self.assertIn('do not launch a duplicate', guide)
        self.assertIn('one active writer per shared `DerivedData` directory', guide)

    def test_xcode_fallback_preserves_raw_outputs_and_exit_status(self):
        guide = VERIFICATION.read_text()
        self.assertIn('Preserve the original stdout and stderr separately', guide)
        self.assertIn('the actual command exit status', guide)
        self.assertIn('the `.xcresult` bundle', guide)

    def test_empty_or_misspelled_test_selector_never_passes(self):
        guide = VERIFICATION.read_text()
        self.assertIn('verify that the requested class or test selector exists', guide)
        self.assertIn('at least one test was actually selected and executed', guide)
        self.assertIn('is `NOT RUN`, not `PASS`', guide)

    def test_evidence_reuse_and_issue_acceptance_are_source_bound(self):
        verification = VERIFICATION.read_text()
        continuity = CONTINUITY.read_text()
        self.assertIn('the same commit alone proves an old artifact is still valid', verification)
        self.assertIn('A partial PR merge does not mean the full issue is done', continuity)
        self.assertIn('every current issue acceptance criterion', continuity)

    def test_documented_installation_targets_configured_codex_home(self):
        readme = README.read_text()
        self.assertIn('${CODEX_HOME:-$HOME/.codex}/skills', readme)
        self.assertIn('skills/repo-supervisor`가 원본입니다', readme)
        self.assertIn('다른 작업 저장소의 복사본만 바꾸지 마세요', readme)

    def test_skill_links_to_platform_specific_build_guidance(self):
        skill = SKILL.read_text()
        self.assertIn('references/verification.md#xcode-builds-and-test-selection', skill)
        self.assertIn('references/continuity-and-evidence.md#status-and-acceptance-ledger', skill)

    def test_superseded_ux_contract_and_environment_errors_stay_scoped(self):
        skill = SKILL.read_text()
        self.assertIn('current user request explicitly supersedes a documented UX contract', skill)
        self.assertIn('DNS or `simctl` error alone does not establish a Mac-wide outage', skill)
        self.assertIn('does not relax operating-system, network, security, authorization, or access-control boundaries', skill)


if __name__ == '__main__':
    unittest.main()
