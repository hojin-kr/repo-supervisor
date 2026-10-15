# Clarify standing delivery authorization

- Objective: present implementation-through-delivery as a primary design concept in README, reflecting the user's explicit implementation invocation.
- Baseline: clean `main` at `dff60b5`; prior protocol delivery is complete.
- Changes: README now states scoped commit/push and conditional merge proceed without reconfirmation. Clarify read-only/plan exclusions, unknown scope/branch/permission, user stop or approval limits, mandatory platform approvals, quality/review/CI/conflict gates, and branch protection. Align skill wording so authority derives from user intent rather than files themselves. No protocol or implementation feature changes.
- Validation: inspect README/skill consistency; skill format, local Markdown links, history targets, whitespace, and tracked content privacy patterns checked before commit. Documentation-only change; no downstream runtime claim.
- Delivery: commit this scoped documentation unit and use only normal fast-forward push to the verified existing remote main; compare final remote SHA with local HEAD. No merge or protection bypass is part of this task.
- Next: no remaining content criteria. Remote comparison establishes delivery of this record. The original checkout remains untouched.
