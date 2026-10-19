# Private storage boundaries

Use this reference for artifact storage during Codex development. Keep the existing [execution packet](execution-protocol.md), [continuity ledger](continuity-and-evidence.md), and strict v1 [verification packet](verification.md). The [storage policy module](../scripts/coordination_policy.py) supplies local decisions and typed observations.

## Public rules, private state

Commit generic policy code, synthetic fixtures, tests, and portable instructions. Keep mount identities, host paths, runtime config, state, raw evidence, and backups outside **all** Git checkouts. An ignored directory inside a checkout is insufficient. Use abstract aliases such as `volume-a` in public summaries; keep actual mappings private.

`private_config(repo, path)` loads a private JSON object without printing values and rejects paths that enter a checkout at any symlink-resolution step, plus group/world-readable config. `LocalLedger(repo, directory)` requires an external private directory, serializes transactions with an exclusive local lock, and atomically records state. A leftover crash lock requires reconciliation, never automatic deletion or expiry. Existing task/writer ledger fields are retained only for state compatibility; this module has no execution-claim or service-selection API.

Keep source, artifact, and state roots disjoint with `disjoint_roots`. Preserve raw evidence outside the checkout. Policy denials contain stable codes rather than private values. Do not publish private hashes or identifiers merely because underlying values are omitted. Pattern tests support manual review; they do not prove absence of every secret.

Development uses ChatGPT Codex only. There is no external AI service adapter, model/cost catalog, quota conversion, fallback selector, or dispatch CLI. A blocked Codex action remains blocked until resolved within its original authorization. Confirm owned execution has stopped before checkpoint handoff; do not signal unrelated processes.

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

Tests use isolated synthetic repositories/state for verification, private-state isolation, storage reservations, recovery decisions, and public boundaries. They do not load user config, mount a device, call an AI service, move real data, or change system settings. Physical mount/copy/recovery observations remain unmeasured by this module. Preserve raw test output outside Git.
