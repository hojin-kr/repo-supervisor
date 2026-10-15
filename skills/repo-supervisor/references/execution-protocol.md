# Capability-aware execution protocol

Use this protocol for delegated or multi-step work. It is a manual contract, not an automatic scheduler or a guarantee of model quality. Keep packets in the active task note or link them from it. For a small direct edit, record only fields that affect execution.

## Choose profiles and boundaries

Configure profiles for the current environment. A profile contains a locally chosen model/tool binding, supported reasoning and editing tasks, a usable context budget, permitted tools, and known limitations. Do not assume a model's name, size, price, or advertised context proves suitability. Use observed task results to revise the binding; if suitability is unknown, use a bounded trial or retain the work with the supervisor.

- **Coordinator:** architecture, contracts, ambiguous requirements, decomposition, risk decisions, and integration. Prefer the strongest suitable reasoning capability available for these tasks.
- **Bounded executor:** one well-understood objective with explicit inputs, limited write scope, and executable acceptance checks. Suitable for a smaller model only when the contract and context fit its demonstrated capability.
- **Independent reviewer:** inspect the fixed candidate and raw evidence against the original acceptance criteria. Use sufficient capability for the risk, preferably a fresh context. Do not give it only an implementer's summary. If independent review is unavailable, disclose that limit; do not label a self-check independent.

Split by coupling, risk, uncertainty, and context cost, not file count. A one-file security or state migration can need coordination; several mechanical files can be one bounded unit. Resolve uncertain interfaces first. Keep tightly coupled changes together if splitting would require shared mutable assumptions. Budget space for task instructions, relevant source, tool outputs, and the executor's work; reduce scope before dropping necessary context. Never split away the end-to-end acceptance obligation.

## Routing and readiness gate

For each profile, separate **hard constraints** (tool permissions, supported operation, known usable context budget, required reasoning capability) from **preferences** (latency, cost, familiarity). First eliminate profiles that fail or have unknown required constraints; then choose among eligible profiles by configured preferences. Do not infer missing capabilities from a model name. If none qualifies, create a read-only investigation packet to resolve unknowns, re-decompose the implementation, or mark blocked. Investigation returns evidence and a contract proposal; it does not grant write permission.

Estimate the whole packet: instructions + required source + dependency contracts + expected tool results + output/reasoning reserve. Compare that estimate with the profile's configured usable budget. If it does not fit, reduce the objective, fetch irrelevant context on demand, or route to a qualifying larger profile. Never remove evidence or a coupled invariant just to fit. An uncertain or high-risk unit stays with the coordinator until a bounded contract is established.

Before dispatch, manually validate the packet table: every dependency ID exists; edges form an acyclic graph (there is a ready node until all nodes are ordered); each consumed contract has a verified version; no simultaneously active units overlap write scopes or shared mutable resources. Missing dependencies, cycles, and conflicting writers make the affected units unready. Split a cycle by resolving the contract in a coordinator investigation or combine the coupled units. One writer also owns integration and shared history updates.

## Task packet

Copy this structure into a task note and fill it with real, portable references before dispatch. Empty required contracts mean the unit is not ready.

```yaml
id: U2
objective: One observable change
base_revision: Exact commit or immutable snapshot
role: bounded-executor
profile: A configured capability profile
inputs: [Contract version and relevant source or evidence references]
context_budget: Budget and what to omit or fetch on demand
write_scope: [Allowed files or narrowly defined symbols]
forbidden: [Unrelated refactors, user data, contract changes]
output: Patch or commit plus evidence and unresolved issues
acceptance: [Command or user flow, expected observable result]
depends_on: [U1]
owner: One current writer
stop_or_escalate: [Ambiguous contract, scope overflow, unsafe state, repeated failure]
retry_budget: A finite task-appropriate attempt limit
redecomposition_budget: A finite limit inherited by replacement packets
```

For each dependency edge, specify the producer's output, version, and consumer assumptions (types, error semantics, state invariants, fixtures). A dependency is satisfied by a verified output, not a worker's completion message. Include an integration unit that exercises the combined user flow. A table of IDs and edges is sufficient; no orchestration service is required.

## Dispatch, reconcile, and recover

1. Freeze the shared contract and base revision. Confirm there is no competing writer or duplicate active task. Assign one writer for overlapping files or symbols; reviewers are read-only. Concurrent notes in a shared history file also need a single writer.
2. Dispatch only ready units with verified dependencies. Parallelize disjoint write scopes with stable interfaces; serialize shared files, migrations, generated output, or changing contracts. A blocked prerequisite blocks its consumers but need not stop independent ready work.
3. Require each result to identify its base and candidate revision, changed scope, checks and observations, remaining acceptance gaps, and blocker state. The supervisor inspects the patch and reconciles contracts before integration. Reject out-of-scope output without discarding unrelated work.
4. Retry a transient tool failure only within the packet's budget, preserving the same candidate and evidence. For ambiguity, excessive context, repeated failed checks, or a contract change, stop the executor. The coordinator either resolves uncertainty, re-decomposes into new versioned packets, or escalates to a stronger suitable profile. Persist each attempt with packet ID, candidate revision, cause, outcome, and remaining retry/redecomposition budgets before redispatch. Replacement packets inherit the remaining recovery budget; changing IDs must not reset it. Record the reason and superseded IDs so retries cannot run alongside replacements. Budget exhaustion leaves the work blocked for a coordinator decision; do not automatically restart it. If no suitable profile is available, mark blocked instead of looping.
5. On the integrated fixed candidate, run relevant consolidated tests and the actual acceptance flow. Independent review checks both the diff and observations, including failure and boundary paths. A changed candidate invalidates affected review and evidence; repeat only the affected checks plus required integration gates. Publish only after required gates pass.

## Synthetic worked example

Request: a local record editor must reject a blank title and preserve the last saved record after a rejected save.

| Unit | Contract and scope | Depends on | Acceptance |
| --- | --- | --- | --- |
| U1 coordinator | Specify title normalization and rejected-save state; read-only design | none | Existing caller and storage assumptions checked; contract v1 recorded |
| U2 bounded executor | Change only `src/title_rules.py` and its focused tests; return validation result per v1 | U1 v1 | Blank/whitespace rejected; valid title accepted |
| U3 bounded executor | Change only `src/editor.py` and its UI tests; consume validation result per v1 | U1 v1 | Rejected save displays error without writing storage |
| U4 coordinator/integrator | Integrate U2/U3 and run editor with synthetic fixture; return fixed candidate and evidence | verified U2, U3 | Save valid record, attempt blank title, reopen editor: prior saved title remains |
| U5 independent reviewer | Read-only review of fixed U4 candidate and raw evidence against the request | verified U4 | Contract, diff, and acceptance observations agree; unresolved gaps reported |

U2 and U3 may run concurrently once v1 is stable. Neither owns storage changes. If U3 discovers that the storage API writes before validation, it stops and returns the conflicting source evidence to U1; it does not widen its scope. If unit tests pass but reopening loses the prior title, U4 records an acceptance failure and routes the scoped fix back through the coordinator. The supervisor records the accepted revision and evidence before delivery.
