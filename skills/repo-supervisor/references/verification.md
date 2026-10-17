# Structural learning and project verification

## Frame the outcome, then choose the smallest route

Restate the user's outcome, core invariant, exclusions, and observable acceptance in your own words before implementation. Normally do this internally and proceed; surface a short statement when it helps the user steer. Ask only about material intent, scope, or authority that source inspection or a safe experiment cannot resolve. Existing implementation delivery authorization and required repository gates still apply.

Choose a route from the actual task: read-only investigation returns evidence; a defect starts with a reproduction; a feature names its data shape and boundaries; a refactor preserves observable behavior. Resolve an empirical design fork with the smallest isolated prototype and measured outcome. Do not widen a simple task into a rewrite. Keep an outside check of the result, independent of the implementer's explanation.

## Put recurring lessons in the system

Read only task-relevant feedback, commits, and local records already available and authorized. Do not collect whole chat histories or team messages. For a repeated failure, identify the first boundary where the invalid state becomes possible and choose the cheapest durable mechanism:

| Evidence from the task | Preferred response |
| --- | --- |
| Illegal combinations or repeated assumptions | Reshape the state/type so invalid combinations are unavailable; validate external inputs at the owning boundary |
| Mechanical convention or detectable omission | Existing lint, schema, test, CI, or a small validator; run a negative case to show it fails |
| Incorrect behavior | A reproduction and behavior test against a requirement independent of current implementation |
| Judgment that cannot be checked automatically | A short instruction and one concrete failure example at its owning entry point |

Record `failure evidence -> invariant -> owning structure/check -> negative case -> remaining judgment`. Delete superseded repetitive advice when a structural mechanism owns it; retain only the non-obvious reason or limits. Do not rewrite source or tests merely to make a check green. An expected value copied from the implementation can encode the bug: derive it from the user's criterion, a trusted specification, or a baseline whose behavior is explicitly intended. Have the independent reviewer challenge both the oracle and the implementation. Human review should concentrate on boundaries, tradeoffs, uncertain expectations, and unautomated behavior.

## Build a small project verification recipe

Use the repository's existing harness first. When no repeatable behavioral path exists, add only the smallest project-local recipe/helper needed for the current acceptance criteria, within authorized scope. Locate it using that repository's skill/document conventions; do not install a plugin or impose another tool's directory layout.

The recipe names the real surface, launch/setup, read-only readiness check, isolated data/configuration, exact drive command or steps, expected observable state and side effects, evidence location, and cleanup of only resources the run created. Preserve evidence after cleanup. A feature index is useful only when there are multiple relevant user journeys; start with the current feature rather than cataloging the whole product. Exercise at least one real mapped path from setup through cleanup before calling the recipe verified. Unavailable runtime or missing access means NOT RUN/blocked, not success. A prototype or stand-in does not establish target-environment acceptance.

For a small command-driven task, use the included [packet draft](../assets/verification-packet.json) and [helper](../scripts/verify.py). The packet is deliberately a draft with a null command; it cannot report success before a real driver and real expectations replace it. Include objective, source/requirement inputs, allowed changes, invariants, current environment identity, check argv, expected exit/output, and a finite timeout. All checks and invariants are required. The existing [execution packet](execution-protocol.md) still owns profile, writer, dependencies, and recovery budgets; link the verification packet rather than duplicating them.

```sh
python3 skills/repo-supervisor/scripts/verify.py run packet.json \
  --repo . --report ../evidence/run-1.json --environment runtime-config-fixture-v1
python3 skills/repo-supervisor/scripts/verify.py check packet.json \
  --repo . --report ../evidence/run-1.json --environment runtime-config-fixture-v1
```

Create a private evidence directory outside the checkout first. When installed, replace the helper path with its installed location. These commands do not create project recipes automatically. `run` explicitly executes the trusted packet's argv in the repository, without a shell, and records output; inspect the commands first. The runner is not a sandbox, and argv can invoke tools with side effects. Do not execute an untrusted packet. The helper never commits, pushes, or grants authority to the commands. `inputs` and `write_scope` are review metadata; the supervisor enforces those boundaries, not an execution sandbox.

The report records the exact HEAD, a content/mode fingerprint of tracked and nonignored untracked files, packet hash, declared runtime/config/fixture identity, and each command's raw output. Changed source, revision, packet, or declared environment blocks `check`. A change still present at a later snapshot during or after `run` blocks acceptance and retains the report. Only boundary snapshots are compared: changing source, executing or reading the changed version, and restoring it between snapshots is not detected and can still produce PASS. The same limitation applies to a restored revision, packet, or external state; this is not continuous mutation monitoring. Store generated data/build output in approved ignored locations or external scratch space, and record the actual tested artifact identity in the environment label. Ignored files, external services, environment variables, tool binaries, and mutable fixtures are not automatically fingerprinted; their identity and configuration must be checked by the project driver and reviewer. Unsupported symlinks/submodules require a project-specific verifier instead of silently incomplete coverage.

Exit 0 means the recorded commands matched this snapshot and declared environment. Exit 1 means blocked, malformed, stale, failed, or NOT RUN. The report is never overwritten. A fresh run needs a fresh path. Manual/null commands, missing tools, and timeouts stay NOT RUN. Output mismatch or an unexpected exit is FAIL. There is no skip, optional-check, or force-success flag. `check` recomputes decisions from observations rather than trusting a PASS label. Preserve failed evidence; fix the cause or report the blocker rather than removing a required criterion. Run `check` again after a commit; a new HEAD invalidates the prior report even if file bytes are unchanged.

This is a local consistency gate, not signed attestation or an authorization/merge gate. Reports can be edited; independent review must inspect raw artifacts and rerun critical checks. A command that merely prints the expected text proves little. The reviewer must confirm that it drives the required real surface and observes its state. When acceptance requires proof that source stayed unchanged throughout execution, use an execution environment that externally enforces read-only source at the fixed commit, or run an identified immutable build artifact with separate writable fixtures. Rerun critical observations independently in that controlled environment; a successful boundary comparison alone does not establish immutable execution. Manual criteria require separately identified direct observation and independent review; this helper will continue to show them as NOT RUN until a real driver replaces the null command. Do not present a blocked helper report as automated verification.

## Sources and adaptation boundaries

The workflow was independently written after reading the following pstack primary sources at revision `101b274dd991f694e1f7024be2157e5f3adf07de`:

- [Encode lessons in structure](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/principle-encode-lessons-in-structure/SKILL.md) and [prove it works](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/principle-prove-it-works/SKILL.md): prefer durable checks and direct observation.
- [Create verification skill](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/create-verification-skill/SKILL.md): a project-specific real-surface recipe with evidence and cleanup.
- [Sharpen](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/sharpen/SKILL.md), [in your own words](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/in-your-own-words/SKILL.md), and [poteto-mode](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/skills/poteto-mode/SKILL.md): clarify the outcome, route by task, and resolve observable questions with evidence.

The [pstack license](https://github.com/cursor/plugins/blob/101b274dd991f694e1f7024be2157e5f3adf07de/pstack/LICENSE) is MIT. No upstream implementation or skill text is vendored. Its model defaults, plugin installation, broad external-action permissions, and workflow-specific approval rules are not adopted. Local user authorization and repository rules remain the execution contract.
