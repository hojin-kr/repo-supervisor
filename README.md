# Repo Supervisor

English | [한국어](README.ko.md)

A Codex skill for managing repository work from status checks through implementation and verification to delivery in task-sized units.

## Contents

```text
skills/repo-supervisor/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── verify.py
│   └── coordination_policy.py
├── assets/verification-packet.json
└── references/
    ├── execution-protocol.md
    ├── continuity-and-evidence.md
    ├── verification.md
    └── storage-policy.md
```

The skill supports resuming work through `.repo-history`, parallelizing independent tasks, runtime verification, auditing consistency between documentation and implementation, and procedures for committing, pushing, and merging verified changes. Work follows the tools available and the repository's rules.

## Key design concept: Implementation requests carry standing approval through delivery

The user's **explicit intent to invoke this skill with an implementation request** includes standing approval to implement and verify within the scope of that request and to **commit and push, and merge without asking again when the repository's merge requirements are met**. Completing delivery after a work unit has been verified is a core design concept of this skill.

A merge must satisfy all required conditions in the repository, including quality and acceptance criteria, required reviews and CI, conflict resolution, confirmation of the target branch, and branch protection. If scope, target branch, or execution authority is unclear, clarify before proceeding. This standing approval does not apply to requests for planning only or read-only review.

The user's implementation request is the basis for this approval; the README or skill files themselves do not grant execution authority. The user's stop instructions and approval limits take precedence, as do required platform approvals and repository protections. See [the skill's Workflow and Guardrails](skills/repo-supervisor/SKILL.md) for the specific delivery conditions.

## Task contracts and resumption

Use ChatGPT Codex and the available built-in tools, assigning work according to Codex model capability profiles. Do not call external AI services or switch services based on quotas. If Codex is blocked, preserve a checkpoint and report the cause. First check required capabilities, permissions, and context budget; then use a task packet that specifies one goal, a limited write scope, inputs and outputs, acceptance criteria, dependencies, and stop conditions. The coordinator handles design and resolves uncertainty; split out independent implementation and review only when the contracts and write boundaries are ready.

- [Execution protocol and synthetic examples](skills/repo-supervisor/references/execution-protocol.md): profile selection, dependency-graph validation, single-writer boundaries, retries, decomposition, and integrated review.
- [Checkpoints and evidence status](skills/repo-supervisor/references/continuity-and-evidence.md): deduplication, task resumption, baseline comparison, distinguishing transient outages from failures, and completion and delivery status by revision.

This is a manual execution contract followed by the skill, not an automatic scheduler. Handle simple changes directly; if delegation tools are unavailable, execute sequentially under the same contract. Distinguish passing unit tests from meeting acceptance criteria for the actual user flow.

## Reduce recurring errors through structure and verification

First assess whether recurring feedback can be encoded in types, invariants, boundaries, existing lint, tests, or CI; leave only judgments that cannot be automated as brief guidance. Restate the goal internally, and answer questions that can be resolved through observation with a safe prototype and measurements. The implementer's test expectations are also subject to independent review.

[The project verification procedure](skills/repo-supervisor/references/verification.md) explains how to choose the minimum verification appropriate to a change's impact, preserve the provenance of Xcode results, and exercise the actual user-facing surface. The included JSON packet and Python standard-library tools bind commands, expected results, and invariants to a commit or source snapshot and environment. Failures, `NOT RUN`, and stale evidence do not pass; manual template items do not pass until an actual driver exists. The tools execute commands from the packet, so first check their trustworthiness and side effects. The tools cannot detect a source change followed by restoration between before-and-after snapshots; when immutable execution is required, independently verify against a source tree whose writes are blocked externally or an identified immutable artifact.

Run the repository's own regression checks without installing additional dependencies:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

The project was written independently while referring to pstack's principles; [fixed-revision primary sources and the MIT license](skills/repo-supervisor/references/verification.md#sources-and-adaptation-boundaries) are recorded. It does not adopt pstack installation, model defaults, or external work permissions.

## Separate shared policy from local runtime information

Keep only general policies, synthetic examples, and tests in the public repository. Keep real volume identifiers, host paths, settings, state, raw logs, and backups outside all Git checkouts. The [storage policy](skills/repo-supervisor/references/storage-policy.md) and small policy module cover local privacy boundaries, volume observations, space reservations, and recovery comparisons. They reuse the existing task packet and strict v1 verification tool.

The service-selection and cost/quota-switching implementation and related synthetic tests have been removed. Current tests check the storage boundary and verification tools. No physical mount inspection or file-movement tools are provided; move decisions preserve the source and do not authorize permanent deletion.

## Installation

Download or clone this repository, then run commands from its root. If an installation already exists, review the differences first.

Codex's installation location may vary by host and version. The [official local skills location guide](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills), checked on 2026-10-20, lists `$HOME/.agents/skills` as the user skills path. The existing installation observed on this Mac was under `$CODEX_HOME/skills`. The command below uses that Mac-specific observed path as an example; on other hosts, check the official guidance for that version and the actual active path. Do not move or delete an existing installation just because its path differs.

```sh
skill_root="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skill_root"
if [ -e "$skill_root/repo-supervisor" ]; then
  echo "repo-supervisor is already installed; review differences before updating."
else
  cp -R skills/repo-supervisor "$skill_root/repo-supervisor"
fi
```

The repository's `skills/repo-supervisor` directory is the source of truth. Check the `CODEX_HOME` used by your Codex installation and install under `skills/repo-supervisor` there. If that directory already exists, review the differences before updating it; do not update only a copy in another work repository. Restart Codex to refresh the skill list. For the skill structure, see the [official OpenAI documentation](https://learn.chatgpt.com/docs/build-skills).

## Usage examples

```text
$repo-supervisor Check the current repository state and previous work history, then plan the next task.
```

```text
$repo-supervisor Implement the requested feature, run the necessary verification, and deliver it as a work unit.
```

Planning requests are investigated read-only. Implementation requests proceed through delivery of verified work within scope under the execution contract described in the key design concept above.

## License

[MIT License](LICENSE) — Copyright (c) 2026 hojin.
