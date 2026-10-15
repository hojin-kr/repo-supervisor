# Prepare standalone Codex skill repository

- Objective: prepare a separate Git repository containing the existing Codex skill for later GitHub publication.
- Baseline: two installed copies were compared. The Codex copy includes documentation alignment/design audit instructions and `agents/openai.yaml` absent from the other copy.
- Changes: preserve the Codex skill and UI metadata under `skills/repo-supervisor`; add Korean installation, invocation, and publication notes; initialize a standalone `main` branch with repository-local author settings.
- Scope: local preparation only. No remote repository creation, push, merge, or installed-skill modification.
- Validation: bundled `quick_validate.py` passed with Python 3.9 and PyYAML 6.0.3 in an isolated temporary environment. Source equality, UI metadata, history index links, isolated installation, and a scan for local paths, private keys, and token patterns passed. Behavioral execution of the supervision workflow is outside this packaging task.
- Account: GitHub CLI authentication and API user lookup confirm `hojin-kr`; the supplied author email's account association is unverified.
- Next: determine repository visibility and license, verify the intended GitHub account, create or confirm the remote repository, then push `main` and verify the remote commit.
- Resume files: `README.md`, `skills/repo-supervisor/SKILL.md`, `skills/repo-supervisor/agents/openai.yaml`.
