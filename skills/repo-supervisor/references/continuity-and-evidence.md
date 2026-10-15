# Continuity and evidence

## Claim and checkpoint

Before changing code, compare the objective, repository identity, branch, base revision, and write scope with available task history, sessions, and worktrees. Record one current owner and explicit handoff for overlapping work. An old timestamp or an idle session alone does not prove abandonment; verify ownership before takeover. If session discovery is unavailable, record the limitation and use the available claims and Git state. A Markdown claim is coordination evidence, not a distributed lock; simultaneous writers need a shared coordination mechanism or serialized handoff.

Keep the active `.repo-history/meta.json` entry pointing at a task note. For long work, checkpoint after a verified unit and before handoff, interruption, or context exhaustion. Record:

- Objective, current acceptance criteria, scope exclusions, owner, and active packet IDs.
- Repository/branch, base and candidate revision, changed files, and relevant dirty-tree ownership.
- Completed outputs, dependency contract versions, review revision, and remaining criteria.
- Check commands or user flows, observations, environment/runtime versions, baseline comparison, and evidence references.
- Status, blocker cause, attempts used, safe retry trigger, and the exact next action/file.

Do not copy whole conversations or sensitive tool output into history. Store redacted summaries and portable commands; keep raw evidence in an approved location with enough provenance to associate it with the measured revision. Do not fabricate a commit ID for the note's own future commit.

On resume, inspect live status, diff, branch, dependencies, and candidate revision. Reconcile changes since the checkpoint and confirm the prior writer has handed off before writing. Reuse evidence only for the same inputs, revision, and relevant environment; rerun affected checks when they change. Resume the next unmet criterion instead of replaying all work or starting a duplicate task.

## Status and acceptance ledger

Use these states in task notes; existing indexes can retain their schema and link the detailed ledger. No database or new runtime is required.

| State | Meaning and next action |
| --- | --- |
| planned | Scope or dependencies not yet ready; resolve them before dispatch |
| active | One owner is executing the ready packet |
| blocked | A required prerequisite or measurement is unavailable; record cause and retry trigger |
| failed | A performed check contradicts an expected result; preserve actual output and diagnose |
| ready-for-review | Fixed candidate and evidence prepared; required independent review remains |
| completed | Required acceptance and repository gates met; record delivery state separately |
| superseded | Replaced by named packets or a newer contract; do not resume it |

Distinguish worker-done, acceptance-verified, integrated, committed, and pushed milestones in the ledger, each tied to its revision. Also record review state. Worker-done cannot satisfy acceptance or integration. Commit success followed by push failure means committed, delivery blocked; retain the exact commit, recheck the remote, and retry a normal fast-forward push when access returns. Do not rerun implementation or create another commit merely because push failed. A non-fast-forward result requires reconciliation and affected verification; never force push. For example, implementation may be complete while acceptance is blocked by an unavailable runtime, or validation may pass while push is pending. An account limit, expired authentication, offline dependency, or unavailable device is a blocker, not proof of a code failure or completed validation. Record what ran and what did not, preserve work, and retry only when the prerequisite changes or within a finite transient retry budget. Do not rotate accounts, invent results, or change credentials to hide a blocker.

For each criterion record `expected -> observed`, candidate revision, environment, evidence, and `pass / fail / blocked / not-run`. A build or unit suite pass proves only its measured surface. Product completion requires the relevant actual UI or execution environment flow and state, including saved state, failure/cancel paths, or boundaries when the criterion depends on them. For documentation-only skills, exercise realistic decisions with synthetic scenarios and verify installed resource availability; do not claim a downstream application's runtime was tested.

Classify a failure as introduced, reproduced on baseline, environment-related, or unresolved, using the same check and environment on an isolated baseline where practical. Never reset a user's dirty checkout or overwrite saves to obtain the comparison. A baseline failure does not excuse a newly failed core criterion; explain whether it prevents acceptance and stop delivery when a required gate remains unmet. If comparison cannot run, say unresolved rather than assuming regression or pre-existing failure.

## Scope and preservation

Track the next action against the current core criteria. Put unrelated cleanup and speculative enhancements in an optional follow-up list; they do not keep the task active. Preserve original sources, provenance, evidence, fixtures, and user saves. Prefer isolated synthetic fixtures and reversible test operations. If a test would overwrite user state, find an isolated route or obtain authorization for that specific operation.

Before publishing, inspect the scoped diff and tracked package for secrets, personal identifiers, absolute local paths, private domains, and borrowed project material. Use synthetic names and `example.com` where examples need identities. Report suspected pre-existing exposure with locations and categories, without reproducing values. Do not rewrite history, rotate credentials, or change repository visibility as part of this check. Pattern scans are supporting evidence, not proof of complete absence.
