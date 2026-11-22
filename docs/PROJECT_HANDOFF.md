# HTP-1 Integration — Project Handoff

> **Purpose:** This is the continuity document for future development chats. Read it before proposing or making changes. This repository contains the **Unfolded Circle integration for the Monoprice HTP-1**. Keep that integration/platform context distinct from the user's separate Couch device and Couch-related project context, as well as from the Fire TV and hosted BEQ catalogue workstreams.
>
> **Device distinction:** The integration target is the Monoprice HTP-1 and the integration platform is Unfolded Circle. Keep those roles distinct from the user's separate Couch device and other project contexts. Do not conflate device identities or operating environments; verify or ask if a role is unclear.

## New-chat instructions

1. Read this document before continuing project work.
2. Verify the live GitHub state (branches, commits, open PRs, checks, and working changes) before assuming a task is complete or starting new work. This document records decisions and intended scope; live repository state is authoritative for implementation status.
3. Preserve the agreed branch strategy below. Do not develop production code directly on `main` or `tests-and-docs`.
4. Keep the approved development phases in order unless the user explicitly changes the plan. Phase 0 is complete; Phase 1.5 automated implementation and validation are complete but real HTP-1 hardware acceptance is pending. Phase 2 is the next planned development phase. Preserve the complete approved Phase 2–6 roadmap in PROJECT_HANDOFF.md.
5. Do not silently add, remove, or reinterpret requirements. Ask before expanding scope.
6. Preserve existing behavior unless a specific correction is required by the phase. Add regression coverage for each correction.
7. Distinguish automated tests, CI results, remote connectivity checks, and actual HTP-1 hardware acceptance. Never claim one proves another.
8. Do not push to upstream, merge PRs, publish releases, or deploy without explicit user authorization.
9. Update this document on `tests-and-docs` when the user approves a material plan or status change. Keep it out of production feature PRs to upstream.
10. **Test-isolation rule is mandatory:** all test code and QA-only assets live only on `tests-and-docs`. Never add or copy tests into `feature-validation`, `feature/*`, `main`, or an upstream PR. Read the Test isolation and upstream-leak prevention section below before any test, branch, workflow, or PR work.

## Repository and branch strategy

Repository: [joemacjr92/uc-intg-monoprice-htp1](https://github.com/joemacjr92/uc-intg-monoprice-htp1)  
Upstream: [mase1981/uc-intg-monoprice-htp1](https://github.com/mase1981/uc-intg-monoprice-htp1)

| Branch | Purpose |
|---|---|
| `main` | Mirror Mase's upstream production code. Do not develop independent changes here. |
| `tests-and-docs` | QA and documentation workspace: tests, fixtures, project handoff, and branch-specific validation workflows. |
| `feature-validation` and `feature/*` | Production implementation only. `feature-validation` is the current production integration branch; focused `feature/*` branches are for scoped production changes. No test code or QA-only assets belong here. |
| Existing specialized branches | Preserve their purpose and history. Do not repurpose or delete without approval. |

### Branch rules

- Keep the fork's `main` aligned with upstream; do not put local product development there.
- Keep tests, fixtures, test configuration, coverage assets, and QA-only workflows on `tests-and-docs` exclusively.
- Implement production changes on `feature-validation` or focused production `feature/*` branches, as directed by the user. These branches must not contain test code or QA-only assets.
- Upstream PRs must contain only the intended production changes. Do not include this handoff, QA-only workflows, test fixtures, or unrelated documentation.
- Do not create a new branch when the user has specified an existing branch, and do not rewrite branch history without explicit approval.
- Before creating a feature branch, inspect the current branch heads and choose the correct base. Do not assume that `tests-and-docs` is the production base.

## Test isolation and upstream-leak prevention — mandatory

This rule takes precedence over convenience and applies to every future chat, branch, PR, and workflow:

1. **Single home for tests:** all automated test files (including unit, integration, regression, contract, and hardware-simulation tests), test helpers, `conftest.py`, fixtures and captured test data, snapshots, coverage configuration/reports, test-only scripts, and QA-only documentation/workflows must exist only on `tests-and-docs`.
2. **Never put tests on production branches:** do not add, copy, cherry-pick, merge, or otherwise transfer test assets onto `feature-validation`, any `feature/*` production branch, or `main`. Do not temporarily place tests there for convenience. If a test is needed for a production fix, add it to `tests-and-docs` and run it against the selected implementation branch.
3. **Production CI stays production-only:** workflows on `feature-validation` and production feature branches may build, package, lint production code, or perform non-test artifact/smoke validation only when explicitly part of the production build. They must not run pytest or a test suite, check out QA test files, or introduce test dependencies/configuration solely to execute tests. Test execution belongs to workflows on `tests-and-docs`, which may check out the implementation branch under test.
4. **Keep the QA workflow one-way:** `tests-and-docs` may fetch/check out `feature-validation` (or the specifically selected production ref) as implementation input and run its own tests against it. Never merge the QA branch into a production branch, and never use `tests-and-docs` as the source branch for an upstream PR.
5. **No bulk branch transfer:** do not merge `tests-and-docs` into `feature-validation`, `main`, or another production branch. Do not cherry-pick QA commits into production. If a commit mixes production and QA changes, stop and separate the changes on their proper branches before proceeding.
6. **Upstream PR is a strict allowlist:** prepare upstream-bound production work from a clean production lineage based on the appropriate upstream code. Transfer only the specific production source changes and strictly necessary runtime dependencies or user-facing documentation approved for that PR. Never transfer tests, fixtures, QA workflows, handoff/validation documents, coverage files, or test-only dependencies/configuration.
7. **Mandatory pre-PR audit:** inspect the complete diff and GitHub's final changed-file list against the upstream base. Confirm there are no test paths (for example `tests/**`, `test_*.py`, `*_test.py`, `conftest.py`), fixtures, QA workflows, coverage artifacts/configuration, handoff docs, or test-only dependency changes. Check the actual PR file list, not just the local commit summary. If anything is ambiguous, stop and ask; do not open or update the upstream PR.
8. **After every branch/workflow change:** verify the live GitHub tree for `tests-and-docs` and `feature-validation`. Confirm test assets remain in the QA branch and are absent from production branches. Do not claim isolation based only on intended branch names.
9. **If a test is missing from QA:** recover or recreate it on `tests-and-docs` from the relevant history or implementation behavior. Do not restore it to a production branch.
10. **User authorization does not imply permission to merge/release/deploy:** continue to follow the separate approval requirements above.

Before any upstream PR is considered ready, report the exact base/head, changed-file list, and the result of this isolation audit. A clean production diff is a release gate, not an optional cleanup step.

## Development principles

- Preserve existing logic and user-visible behavior unless the approved phase explicitly requires a correction.
- Inspect the current implementation, relevant upstream code, firmware/API behavior, and framework capabilities before changing code.
- Prefer small, reviewable changes with focused regression tests.
- Use official `ucapi` and `ucapi-framework` capabilities when available; do not recreate framework entities or introduce custom stateful-button mechanisms where explicitly prohibited.
- Validate device-specific ranges, steps, precision, readback, firmware compatibility, and runtime capabilities before exposing controls.
- Fail closed when a required capability is unknown, as specified in Phase 2.
- Keep `pyproject.toml` and `requirements.txt` synchronized; CI should enforce this.
- Do not claim hardware behavior based solely on mocks, unit tests, or CI.
- Do not add setup-only controls to the Remote interface.
- Keep excluded or deferred work excluded until the user approves it.

## Development roadmap

The phases below are the approved plan. Phase 0 adds configurable-port support required for remote testing through the user's existing private reverse-proxy setup. Phase 1.5 is an approved test-hardening phase added after the Phase 1 review; it does not replace or reorder Phases 2–6.

### Phase 0 — Configurable HTP-1 port and private reverse-proxy access

**Goal:** Support a configurable HTP-1 HTTP/WebSocket port so the integration can use the user's existing private reverse-proxy connection, while preserving the default local connection.

- Add a port field to setup; default to `80`.
- Validate ports as integers in the range 1–65535.
- Persist the configured port with each device entry.
- Use the configured port for controller WebSocket connections, setup probing, and HTTP IR commands.
- Preserve compatibility with existing configuration and backup data that do not contain a port; these entries default to `80`.
- Preserve configured ports through backup and restore.
- Validate remote connectivity through the user's established private reverse-proxy path. Keep network addresses, hostnames, topology, and tunnel details out of repository documentation.
- Keep credentials and private access details out of logs and public documentation.

**Acceptance:** Setup supports the default and custom ports; all connection paths use the selected port; legacy configuration and backup data default to port 80; backup/restore preserves configured ports; and the Remote successfully operates the HTP-1 through the private proxy route. Automated tests, backup inspection, and actual Remote/HTP-1 behavior are recorded separately in the Phase 0 QA record.

### Phase 1 — Correctness and safety

**First**

- Serialize all WebSocket state-changing transactions.
- Enforce PEQ Pre for BEQ and LFE-only routing.
- Implement add-on-aware input filtering.
- Validate source selection against eligible inputs.
- Resolve entity registration/connectivity behavior.
- Fix the unbounded catalogue lock registry.
- Validate hardware control bounds.
- Add regression tests for each correction.

**BEQ PEQ-placement contract (confirmed 2026-11-22):**

- Never change /peq/location as part of a BEQ load. In particular, do not attempt to override receiver policy such as allowPEQLocationChange: "no".
- BEQ loading is allowed only when the current receiver state explicitly reports peq.location == "pre". Reject post, missing, malformed, or unknown placement before sending any write.
- When placement is not confirmed as Pre-Dirac, the media browser must show a non-playable, non-browsable informational BrowseMediaItem titled **BEQ Unavailable**, with the explanation: "BEQ loading requires PEQ Location to be set to Pre-Dirac."
- Disable catalogue search/browsing in that state. If a BEQ is already active, retain its Clear BEQ action so the user can remove it.
- Keep the existing LFE-only sub1 filter routing. Do not copy BEQ filters to independent post-Dirac subwoofer channels.

### Phase 1.5 — Integration and state-flow test hardening

**Goal:** Improve confidence in the integration's connection lifecycle and end-to-end state handling without changing production behavior unless testing exposes a verified defect.

**Scope and priority:**

1. **Connection lifecycle tests**
   - Build a small in-process fake HTP-1 WebSocket server that can respond to initial `getmso` requests and accept/echo or acknowledge `changemso` updates.
   - Exercise the real WebSocket connection and message-handling path rather than mocking every internal method.
   - Cover WebSocket creation, receive/parse behavior, initial state retrieval, connection/disconnection callbacks, reconnect/recovery, and HTTP command delivery where practical.
   - Retain and extend the existing concurrent-write serialization, write-failure recovery, and disconnected-send tests; do not describe these existing tests as absent.

2. **Entity state synchronization and round trips**
   - Test connected-state synchronization for media player, remote, selects, and sensors, including representative state and malformed/missing fields.
   - Add command-to-patch-to-updated-state-to-parser-to-entity round-trip tests.
   - Prioritize volume scale/readback, mute, input selection, trims, and PEQ/BEQ state.
   - Verify that tests reflect actual HTP-1 state semantics; do not assume undocumented units or ranges.

3. **BEQ browser index loading**
   - Exercise actual `_load_index` behavior with mocked HTTP responses.
   - Cover successful manifest loading, malformed/invalid manifests, checksum mismatch, network errors/timeouts, and recovery after failure.
   - Keep live catalogue access opt-in; deterministic CI tests must not depend on external catalogue availability.

4. **Representative HTP-1 state fixture**
   - Obtain a representative full `getmso` capture from the user's HTP-1 when available.
   - Scrub identifying or private information while preserving the receiver's real structure and values.
   - Include real volume, shaker, input, and other relevant state where present; do not invent missing fields or fabricate device values.
   - Use the fixture to validate parsing, optional fields, and firmware-dependent behavior.

5. **Coverage reporting and CI**
   - Add reproducible coverage reporting and record a baseline.
   - Establish targeted expectations for important modules/paths before considering a global threshold.
   - Keep Phase 0 and Phase 1 compatibility/regression tests in their dedicated QA workflow, run against the intended implementation source.
   - Ensure the regular and dedicated QA workflows have clear, non-overlapping responsibilities and report what each actually tests.

**Constraints:** This is a test-focused phase. Preserve production behavior. If tests expose a real defect, isolate the correction, add a regression test, and keep the production change narrowly scoped. Do not bundle unrelated refactoring or feature work. Keep test-only code, fixtures, coverage configuration, and QA workflow changes on `tests-and-docs` exclusively; production fixes, if required, belong on `feature-validation` or a focused production `feature/*` branch. Never place tests on those production branches. Do not include QA-only material in upstream PRs. Follow the mandatory Test isolation and upstream-leak prevention gate above.

**Transaction safety behavior implemented (2026-11-22):**

- Serialize the complete state-changing transaction, not just the individual WebSocket frame.
- Refresh receiver state before read/modify/write operations and before deriving source, calibration, seat-shaker preset, or absolute-volume decisions.
- Do not assume `changemso` has an acknowledgement. After writing, request a fresh `getmso` snapshot and verify every touched JSON path before reporting success.
- A state-refresh timeout, disconnect, generation change, or mismatched/partial readback aborts the operation. Never blindly replay an incomplete transaction after reconnect.
- Preserve the last state actually reported by the receiver. A failed/unverified transaction is not a success, but do not fabricate a rollback when the receiver already echoed a change.
- Keep the confirmed BEQ PEQ-placement contract above: never write `/peq/location`; require explicit PEQ Pre.

**Real-time HTP-1 monitoring corrections (2026-11-22):**

- Ordinary `changemso` state writes wait up to two seconds for the relevant live `msoupdate` to converge, then perform one confirming `getmso` snapshot. The touched JSON paths must match before success is returned. The write transaction remains serialized; the live update is registered/observed before any subsequent operation can overtake it.
- Plain-text `error` WebSocket frames are handled as receiver protocol errors, not malformed JSON. Their message is retained for the pending operation.
- Dirac selection is no longer verified by the early `/cal/currentdiracslot` value. The HTP-1 generates the request ID; the integration compares the new `cal.diracSwitch.id` with the pre-write ID, waits for that request to reach `complete` (15-second overall budget), then performs one confirming `getmso` readback.
- `requested` and `running` are progress only. A matching-ID `diracSwitchReply` refusal is a failure; a newly changed non-`nr-...` refusal reply is also recognized if the receiver has already reverted the visible switch snapshot. An unrelated `nr-...` busy reply does not cancel an already accepted request. A plain-text error fails the pending change only if no accepted request ID has been observed.
- A receiver already reporting `diracSwitch.locked` or `diracApplying` is rejected locally before sending another slot change.
- QA-only regressions cover 250 ms delayed volume convergence, delayed Dirac completion, standby refusal, unrelated busy replies, plain-text busy rejection, and Dirac timeout. Tests remain exclusively on `tests-and-docs`; production code remains on `feature-validation`.
- These are automated/fake-receiver validations only. Real HTP-1 hardware acceptance remains pending.

**Validation results (2026-11-22):**

- Production source branch: `feature-validation` at `27ae1f47af651ba7dc63b9c535ebffbe9a8f9b29`.
- QA test commit: `f1d3b68d18b6bb13136a1105178687365b1daa37`; current QA/handoff branch head after recording these results: `1d77bb759ab383ebec34441049a7521c34c7127a`.
- ARM64 Test Build: passed — [run 45055106945](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45055106945).
- Phase 1 WebSocket Safety QA: passed — [run 45055356382](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45055356382). Results: 95 regression tests passed, 1 skipped; 33 Phase 0 compatibility tests passed; 21 added regression-gap tests passed; 111 Phase 1 tests passed; 2 TLS tests passed. Focused Ruff correctness checks passed. Broader Ruff audit remains diagnostic.
- Full QA and Phase 0 workflow: passed — [run 45055356346](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45055356346).
- Standard Tests workflow: passed — [run 45055356339](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45055356339). Results: 93 passed, 1 skipped.
- Coverage during Phase 1 suite: 79% across the measured device/browser modules.

**Acceptance:** The connection lifecycle is exercised through a fake server; connected entity synchronization and representative command/state round trips are covered; BEQ manifest validation and failure recovery are tested without live network dependencies; a scrubbed real-device fixture is added when available; and CI publishes a reproducible coverage report with documented baseline/targeted expectations. Record automated CI results separately from Remote connectivity and actual HTP-1 hardware acceptance.

### Phase 2 — Dependency and Number entity support

- Wait for compatible published `ucapi` and `ucapi-framework` releases.
- Use Jack's official `NumberEntity`; don't recreate it.
- Check Remote Number support at runtime and fail closed if capability is unknown.
- Add a CI check keeping `pyproject.toml` and `requirements.txt` synchronized.
- Investigate Center and LFE trims, Seat Shaker Trim and LFE Gain, and Mix Out Volume.
- Verify each device's actual range, step, precision, and readback before exposing it.

### Phase 3 — Hardware controls

- Seat Shaker: finish the Preset Select, Trim and LFE Gain Numbers, and Mute Button.
- Center and LFE channel trims, subject to confirmed device behavior.
- Mix Out Volume Number and Mute Button.
- WideSynth and Auro High Sides toggle commands.
- Keep setup-only controls out of the Remote interface.
- Do not introduce a custom stateful-button mechanism.

### Phase 4 — Dirac and calibration

- Improve Dirac state and error reporting.
- Investigate context-aware reload and apply recovery controls.
- Handle calibration busy states.
- Preserve the existing Calibration Select entity.
- Verify the actual HTP-1 API and behavior before implementing recovery commands.

### Phase 5 — Diagnostics and polish

- Review sensor accuracy and unavailable/unknown states.
- Improve error handling and diagnostics.
- Review compatibility with older firmware.
- Update documentation and dependency information.

### Phase 6 — Full regression and hardware acceptance

- Full automated test suite.
- Concurrency and state synchronization tests.
- BEQ/Dirac interaction tests.
- Older firmware and missing-capability tests.
- Remote entity creation and Number capability tests.
- Real HTP-1 testing.
- Final review for unintended behavior changes.

## Private remote HTP-1 access

A private reverse-proxy path is available for remote HTP-1 testing. Phase 0 validated the integration's configurable-port support using that path, and the user confirmed that the Remote connected and sensors operated successfully.

Operational network details are intentionally excluded from this repository's documentation. Do not record or reproduce private IP addresses, hostnames, ports tied to private infrastructure, VPN or tunnel addresses or configuration, proxy topology, internal service names, or deployment paths. If troubleshooting requires those details, obtain them directly from the user in the relevant private working context; do not copy them into handoff documents, issue reports, logs, or public materials.

Do not enable public port forwarding, change the established private access setup, or remove fallback connectivity without explicit approval. When documenting validation, state only that the private reverse-proxy path was used and describe the observed result without exposing its endpoints or implementation details.

## Separate workstreams — do not conflate

The following are not phases in the roadmap above:

1. **Hosted BEQ catalogue work:** catalogue publishing/compatibility, its own hardening tasks, and related CI. Keep it distinct from the HTP-1 feature roadmap.
2. **Generic performance/hardening investigations:** treat these as separately scoped tasks unless the user explicitly maps an item into one of the phases above.
3. **Couch device / separate Couch-related context:** not the Unfolded Circle integration platform and not the HTP-1. Keep any separate Couch project or operating-environment details out of HTP-1 implementation assumptions unless the user explicitly asks to work on them.

## Current status tracking

Update this section as work progresses. Record verified facts only.

| Item | Status |
|---|---|
| Branch strategy | Agreed: `main` mirrors upstream; `tests-and-docs` holds QA/docs; `feature/*` holds production development. |
| Phase 0 | **Complete.** Configurable port setup and connection paths implemented; legacy config/backup defaults to port 80; backup preserves per-entry ports. Remote sensors confirmed working through the user's private reverse-proxy path. Endpoint and topology details are intentionally not recorded. See `docs/phase-0-validation.md`. |
| Phase 1 | **Implementation and automated validation complete; hardware acceptance pending.** Feature branch `feature/phase-1-websocket-safety` at `d218f8a` merged into `feature-validation` via PR #3 (`f59e494`). QA: 91 regression tests passed, 1 skipped; 33 Phase 0 compatibility tests passed; 11 Phase 1 tests passed ([QA run](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44977615939)). ARM64 2.4.2 artifact built successfully ([run](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44977763697)). Remote/HTP-1 hardware validation is still pending. See `docs/phase-1-validation.md`. |
| Phase 1.5 | **Automated implementation and validation complete; HTP-1 hardware acceptance pending.** Detailed results and remaining hardware checks: [docs/phase-1.5-validation.md](phase-1.5-validation.md). Existing fake-WebSocket lifecycle, connected-entity synchronization, command/state round trips, BEQ index, and browser-index tests remain on tests-and-docs. The seat-shaker trim readback correction from PR #4 was merged into feature-validation at 652f8c4; it reads current top-level /shaker/trim with saved-preset fallback. PEQ placement behavior is implemented on feature-validation: d45043e requires PEQ Pre without modifying placement; 6eb1d78 gates the browser and supplies the informational unavailable item while retaining Clear BEQ for an active filter. Transaction safety implementation is on feature-validation: 5b44cd4 adds full-operation serialization, fresh-state refresh, and post-write verification; d2bd00c refreshes source/preset/calibration selections; 58d93e1 and f44c4f4 validate absolute volume against fresh calibration bounds and fail safely if state is missing; 366fad4 bounds state refresh with a cancellable event waiter. QA-only regression and failure-injection coverage is on tests-and-docs (latest QA commit 49f59ff). Validation against feature-validation: 94 regression tests passed with 1 skipped, 33 Phase 0 compatibility tests passed, and 71 Phase 1 tests passed; coverage is 76% for device.py, 57% for browser.py, and 70% combined ([Phase 1 QA](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44990210163), [Phase 0 QA](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44990210207), [regular tests](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44990210124)). ARM64 integration build succeeded ([run](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44990201038)). Remaining work is real HTP-1 hardware acceptance of transaction behavior and BEQ/Dirac behavior; no merge, release, or deployment has been performed. QA-only work stays on tests-and-docs; production corrections stay on feature-validation or another explicitly approved production feature branch. |
| Phases 2–6 | Approved scope; implementation status must be verified against current commits, PRs, tests, and hardware checks before being marked complete. |
| Handoff location | `docs/PROJECT_HANDOFF.md` on `tests-and-docs` only. |

**When updating status:** include the relevant branch, commit SHA, PR link (if applicable), CI run/result, and whether real HTP-1 hardware was tested. Do not mark a phase complete based only on an implementation commit.


## Lint audit — 2026-11-22

A broader diagnostic Ruff audit was added to the QA-only `phase1-qa.yml` workflow in commit `d66ec384b5781a6e10c9a537ece93cf2c332445d`. It checks implementation code from the selected production source ref together with QA tests and tools. The existing focused `F` check remains a required step; the broader rule-family audit is diagnostic and uses `continue-on-error`.

- Focused Pyflakes check (`ruff check --select F`): passed.
- Broader diagnostic check (`E,F,W,I,UP,B,SIM,ASYNC,PERF,PIE,PT,RET,RUF,C4,DTZ,LOG,PGH,PL,TRY`): reported 663 findings across implementation, tests, and tools.
- The largest reported groups include E501 line length, TRY003/TRY004 exception-style rules, and I001 import ordering.
- Existing `setup.cfg` declares a 120-character line limit, while the diagnostic Ruff invocation used Ruff's default 88-character limit. E501 findings therefore require a correctly aligned configuration before they can be treated as actionable.
- Many additional rules are opinionated modernization/style guidance, not evidence of runtime defects. Do not apply bulk `--fix`, unsafe fixes, or broad refactoring. Review rule families individually, preserve behavior, and add any adopted rules deliberately.
- The broader diagnostic run completed and the full Phase 1 QA workflow passed; the regular Tests workflow also passed. These are automated results only, not HTP-1 hardware acceptance.

No production source files, tests, or test fixtures were changed by this audit. QA workflow and handoff changes remain on `tests-and-docs`.


### Ruff configuration alignment follow-up — 2026-11-22

- The broader diagnostic invocation now passes `--line-length 120`, matching the existing `setup.cfg` `[flake8]` max-line-length setting. Ruff's default isort profile is Black-compatible, matching the existing `[isort]` profile.
- The aligned diagnostic reports 519 findings, down from 663. E501 findings fell from 190 to 46; the remaining 46 exceed the actual 120-character project limit.
- Remaining largest groups: TRY003 (86), I001 (47), E501 (46), TRY004 (21), UP041 (12), and TRY301 (10).
- Focused Pyflakes check passed. The aligned broader diagnostic completed with findings as expected; full Phase 1 QA and regular Tests workflows passed on commit `04aa707605024cda2f71605a40c5694138e38699`.
- This was configuration alignment only. No automatic fixes or production/test source edits were made. Do not bulk-fix remaining rules; review categories against behavior and project conventions before adopting them.



**Asynchronous Dirac lifecycle and command concurrency (2026-11-22):**

The approved Remote-timeout/concurrency follow-up is implemented on `feature-validation`:

- Dirac selection now holds the normal transaction lock only for preflight, sending the receiver request, and waiting briefly for a receiver-generated request ID / acceptance state. It returns success to the Remote after the HTP-1 announces the matching request in `requested`, `running`, or `complete`; immediate refusal, plain-text busy error, invalid selection, unavailable receiver, or acceptance timeout still returns failure.
- The accepted Dirac lifecycle is monitored by a background task with the existing 15-second completion timeout. The background task does not hold the normal transaction lock while the DSP applies the correction.
- Volume, mute, input, sound-mode, BEQ, power, and other ordinary transactions can run while Dirac is applying. Ordinary transactions remain serialized with each other.
- A separate Dirac operation lock prevents a second calibration selection while the first is pending. The second request is rejected promptly without sending another HTP-1 write.
- The calibration select keeps displaying the last confirmed slot while the receiver's early `currentdiracslot` value changes. The new slot is published only after the matching request reaches `complete` and a confirming `getmso` reports the expected request ID, slot, and current slot.
- Dirac lifecycle events use a dedicated event and error channel, separate from the ordinary write-convergence event/error channel. Disconnect wakes the background monitor; connection-generation checks prevent a stale task from confirming against a replacement connection.
- The Remote Integration API's `entity_command` result acknowledges command execution/initial failures; stateful entity values are subsequently communicated with `entity_change`. This implementation uses that distinction rather than holding the Remote command open for the full DSP lifecycle. See the official [Unfolded Circle entity command documentation](https://unfoldedcircle.github.io/core-api/entities/) and [integration driver message flow](https://unfoldedcircle.github.io/core-api/integration-driver/write-integration-driver.html).
- QA regressions were updated/added on `tests-and-docs`: prompt acknowledgement before completion, no premature displayed slot, nonblocking volume write during Dirac, immediate rejection of a second Dirac request, refusal/busy handling, asynchronous lifecycle timeout, and delayed final-readback behavior.
- A further QA-only regression now models the observed hardware timing where the receiver first publishes `requested`, the Remote is acknowledged, and a matching standby refusal arrives later. It verifies the background monitor catches the refusal, preserves the last confirmed slot, skips success readback, and releases the Dirac operation lock. Added in `e4a25188815649f00e63c69f66601e4ad5bfe43a`; CI validation is in progress.
- Production commits: `c69ac2fd22e628fa0a09cade87731c86740f7da1` (asynchronous lifecycle) and `a0ea1813b584868e0b3c97dbf8f23f99c0264cd4` (confirmed-display preservation fix); current production head is `a0ea1813b584868e0b3c97dbf8f23f99c0264cd4`. QA test commits include `524493f6f99fbbd74022d29f2f3f18236ba75379`, `23d7fdb5f7bc41502e00d2f555ebbfe8213562b3`, and `0ccf100503f6613a4942eeb2866fe5973da983f6`.
- Automated validation passed against production head `a0ea1813b584868e0b3c97dbf8f23f99c0264cd4` and QA head `0ccf100503f6613a4942eeb2866fe5973da983f6`: Phase 1 WebSocket Safety QA [run 45058395723](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45058395723) passed (112 Phase 1 tests, 95 general regressions with 1 skipped, 33 Phase 0 compatibility tests, 21 regression-gap tests, 2 TLS tests; focused Ruff checks passed; 79% measured coverage); Phase 0 and Full QA [run 45058395750](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45058395750) passed; standard Tests [run 45058395760](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45058395760) passed; ARM64 Test Build [run 45058383533](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45058383533) passed.
- Real Remote/HTP-1 validation remains required, particularly confirming the Remote receives prompt select acknowledgement and that volume remains responsive during an actual Dirac apply. No deployment, merge, release, or upstream PR has been performed.

### Minor maintenance cleanup — 2026-11-22

- Production release packaging on `feature-validation` now explicitly collects the `certifi` package in the PyInstaller build and fails the build if `certifi/cacert.pem` is absent. This aligns the release artifact with the already-verified ARM64 test build. Production commit: `94f69bf043b5eb3a160a76b454bc8539fa152714`.
- Every third-party `uses:` reference in `.github/workflows/build.yml` is pinned to a full commit SHA, with the corresponding upstream major version retained in a comment. This removes floating action-tag resolution from the release workflow.
- The user-facing README now accurately states that the BEQ catalogue uses HTTPS certificate-chain and hostname verification through the bundled `certifi` CA bundle. It no longer claims certificate verification is disabled. README commit: `a9bb791f4ffbe2d3d610142c54c0864ac113bf03`.
- The existing TLS unit test already asserts both `ssl.CERT_REQUIRED` and `check_hostname is True`; no duplicate test was added.
- The MD5 `usedforsecurity=False` argument in the catalogue ID generator is intentional: the digest preserves legacy BEQ media IDs and is not used for security. Keeping the flag also permits the compatibility hash in FIPS-restricted Python environments.
- Reviewed the `nonlocal` declarations across the current QA tests. The declarations are used to update enclosing-scope counters/state in their nested async test helpers; no unused declaration was found to remove.
- ARM64 Test Build passed after production commit `94f69bf043b5eb3a160a76b454bc8539fa152714`: [run 45059203941](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45059203941). Both the Docker TLS smoke check and ARM64 executable/package build passed. This confirms the existing no-push test packaging path. The modified release workflow itself was not dispatched because it also pushes a Docker image and creates a draft release; its build step is guarded with the same explicit certifi collection and bundle-presence check. No deployment, release, merge, or upstream PR has been performed.

### README attribution preservation requirement

- The complete `## Credits`, `## License`, and `## Support & Community` sections are protected project attribution and must be preserved verbatim in all README edits and upstream updates.
- Required acknowledgements include Developer: Meir Miyara, the Monoprice HTP-1, Unfolded Circle Remote 2/3 framework, HTP-1 WebSocket API, UC community, the original support links, the community thank-you, and the final `Thank You: Meir Miyara` line.
- Do not replace these sections with abbreviated credits, generic support text, or a consolidated attribution sentence. Before any upstream push or README rewrite, explicitly diff these sections against the approved wording and verify they remain present.
- Restored verbatim on `tests-and-docs` in commit `ce11002cfced917a609b7ecfd5a913987bd35da2` after the minor documentation cleanup.
