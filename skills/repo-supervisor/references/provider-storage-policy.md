# Provider coordination and storage boundaries

Use this reference when an execution packet needs provider routing or artifact storage. Keep the existing [execution packet](execution-protocol.md), [continuity ledger](continuity-and-evidence.md), and strict v1 [verification packet](verification.md). The [policy module](../scripts/coordination_policy.py) supplies local decisions and typed observations, not another task schema or runner.

## Public rules, private bindings

Commit generic policy code, synthetic fixtures, tests, and portable instructions. Inject account bindings, exact-model catalog/price observations, mount identities, host paths, runtime config, state, execution receipts, and raw logs from private locations outside **all** Git checkouts. Do not solve this with an ignored directory inside the source repository. Public documentation uses abstract aliases such as `volume-a` and synthetic model bindings such as `provider/model-a`; these do not claim real availability or pricing.

`private_config(repo, path)` loads a private JSON object without printing values and rejects in-checkout locations and group/world-readable config. Controllers translate private config into the typed policies; this loader does not validate an arbitrary provider's configuration. `LocalLedger(repo, directory)` requires an external private directory, serializes transactions with an exclusive local lock, and atomically records state. No CLI prints its contents. Policy denials contain stable codes rather than input values; keep lower-level OS/Git exceptions and raw provider output local too. Pattern tests are supporting checks, not proof that every secret or identifying detail is absent.

Keep source, artifact, and controller state roots disjoint with `disjoint_roots`. Evidence belongs outside the checkout and must survive cleanup. Use aliases and digests in reviewable summaries; keep the mapping to real paths/accounts and raw receipts private. Do not publish private hashes or identifiers merely because their underlying values are omitted. The public examples and regression runs use synthetic data only.

## Provider contract and capability status

| Surface | This package supports | Validation status |
| --- | --- | --- |
| Capability/cost policy, claims, normalized failure transitions | Pure local decisions and persisted synthetic receipts | Synthetic tests |
| Receipt-to-checkpoint handoff | Require exact run/model match, positive stop confirmation and a stop-receipt digest | Synthetic trusted-controller inputs |
| Provider launch, effective model/cost observation, stop or authentication | No adapter provided; `live=True` is denied | NOT RUN / unsupported here |
| Mount, filesystem, free-space or recovery observation | Validate supplied typed observations only; no OS probe/copy tool | Synthetic tests; physical behavior NOT RUN |

Keep availability, quota, effective-model receipts, and validation status as fresh private observations; do not hardcode an account-specific limit, denial, or outage as a permanent default. Do not infer live support from a local prototype, mock result, or a configuration flag. Future adapters need independent real-surface evidence for launch, all primary/auxiliary model bindings, cost observations, owned process lifecycle, output capture, and stop before they can become eligible. An unavailable required observation remains blocked. This module is not execution containment or a cost-enforcement service.

Use `ProviderPolicy` with exact eligible models, required capabilities, cost currency/unit, maximum permitted input/output rate, quote freshness, all allowed auxiliary roles, finite attempts, and bounded cooldown. `Quote` binds capabilities and observed rates to the exact model and timestamps. Missing, nonfinite, excessive, future-dated, or expired price data fails closed; a free-looking name does not establish zero cost. Validate every auxiliary binding too. Hidden default models or unobserved roles make the adapter ineligible. Capability sizing, context budget, allowed writes, inputs, and invariants remain in the existing small execution packet; quote eligibility alone does not prove that a model can do the task or bound total spend.

`ProviderClaims.begin` only reserves a task/workspace claim. It never launches a worker. Use the task unit's contract digest, an owner alias, eligible quotes, and an explicit clock. Duplicate task/contract replay or a second workspace writer is rejected. All cooperating controllers for the same source must share one ledger. The local lock is not a distributed lease; do not run independent ledgers for the same writer scope. A leftover crash lock or uncertain claim requires reconciliation, never automatic deletion or expiry.

A trusted external controller must own the process associated with the returned run ID. Before calling `finish`, it must positively verify that the owned process and relevant descendants stopped, preserve the stop evidence privately, and supply its digest. Do not substitute a stale PID, timeout alone, or worker self-report. This package records and requires that controller assertion; it does not observe or kill processes itself. An unconfirmed stop retains the writer and blocks handoff. No checkpoint is measured after an uncertain stop.

| Normalized result | Policy action |
| --- | --- |
| `policy_denied` | Terminal ledger latch; no retry, model/account/endpoint fallback, or new task alias to evade it |
| Auth / HTTP 403 | Distinct terminal outcomes; do not label them quota |
| Explicit quota / rate limit | Wait for bounded cooldown after confirmed stop; only then may an eligible exact model be chosen |
| Recognized network failure | Bounded retry of the same exact model after cooldown and stop confirmation |
| Test failure, unknown error, partial result | Preserve receipt, source, and partial output; no automatic acceptance or resume |
| Stopped / worker done | Stopped may resume within budget; worker done still needs fixed-candidate acceptance and independent review |

`remaining_fraction` requires explicit fraction/percent units and used/remaining meaning; it rejects ambiguous units, nonfinite values, and out-of-range inputs without guessing. A quota observation does not prove token capacity, price, model identity, or end-to-end readiness.

`classify` accepts explicit normalized codes from a trusted adapter plus HTTP status. It never guesses from quota-like prose. Policy-denial evidence takes precedence over quota; 401/403 remain auth/forbidden. Persist each run's identity and receipt; attempts do not reset on resume. Policy/contract/source drift blocks resume. Never edit state, refresh a denial into quota, change identity, or create replacement IDs to bypass budgets. Re-decomposition and any policy reconciliation remain coordinator decisions under the original scope and inherited recovery budget.

After stop-confirmed handoff, freeze the candidate before using the existing `verify.py`. Do not use that fixed-candidate verifier as a mutation worker. Link private receipt/observation checks through normal v1 `argv`, expected results, and environment identity; do not add orchestration or storage fields to the strict packet. Outside config, state, and artifacts are not automatically included in the source fingerprint: a project driver must check their actual identity/digests. Independent review inspects the original criterion, candidate, controller evidence, and raw observations. Keep worker done, accepted, integrated, committed, and pushed separate.

## Storage preflight and copy/recovery contract

`StoragePolicy` names the expected volume identity, required filesystem/metadata features, observation age limit, and safety reserve. A trusted read-only platform probe must produce `VolumeObservation` from actual OS mount/identity, filesystem, and free-space measurements. Mere directory existence or a label is not a mount proof. No platform probe is bundled. Synthetic flags in these tests are supplied observations, not physical mount verification.

`reserve` rejects absent/unverified mounts, identity mismatch, missing mount directories, stale observations, unsupported features, and insufficient free space including existing reservations. `within` rejects absolute paths, traversal, and symlink escapes for artifact-relative paths. A fabricated mount directory must never be marked `actual_mount=True` by a real probe. Bind the observed volume to the intended mount root, resolve the artifact path there, and re-observe before actual IO. If any check fails, stop; there is **no silent fallback** to another disk or a similarly named directory.

Budget peak additional usage, including duplicate copies, temporary files, metadata, validation/recovery scratch, and bounded retry overhead. Reserve before IO. Reservation tokens prevent duplicate claims and wrong-owner release; release only after the operation is positively stopped. Reservations are cooperative accounting, not filesystem quotas or a free-space guarantee against other processes. Coordinate all consumers through the same private ledger and obtain fresh observations. These rules do not authorize any real transfer.

For an authorized transfer, first quiesce the source or use an externally immutable snapshot. Inventory content hashes, file count, byte count, and required metadata. Copy to a separate destination, independently inventory it, restore into isolated scratch, and compare the restored inventory. `relocation_decision` only accepts matching stable-source/copy/recovery `Inventory` observations with supported metadata. It does not create or measure those inventories. Boundary matching cannot rule out transient change/restore; immutable-source enforcement and independent observation are required when that invariant matters.

Publish a durable reference only after the copy and recovery checks pass; retain the original on mismatch, incomplete copy, unsupported metadata, or unverified recovery. The decision always retains the original and never authorizes deletion. A relocation is not a backup. Logical bytes inventoried or copied are distinct from measured reclaimed filesystem space; report actual reclaimed bytes as unmeasured unless a same-volume, controlled before/after observation supports them. Permanent deletion requires separate explicit authorization and is not implemented by this module.

## Rerunnable synthetic acceptance

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

This executes existing verification tests, typed-policy transitions, private-state isolation, reservations, and the public text-pattern gate. The tests create only isolated synthetic repositories/state and do not import a user's config, mount a device, launch a provider, move real data, or change system settings. For installed use, add the installed `scripts` directory to a trusted controller's import path and import `coordination_policy`; there is intentionally no new dispatch CLI. Preserve test output privately and attach it to the fixed candidate with the unchanged v1 verifier.
