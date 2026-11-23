# HTP-1 Integration — Project Handoff

> **Purpose:** This is the continuity document for future development chats. Read it before proposing or making changes. This repository contains the **Unfolded Circle integration for the Monoprice HTP-1**. Keep that integration/platform context distinct from the user's separate Couch device and Couch-related project context, as well as from the Fire TV and hosted BEQ catalogue workstreams.
>
> **Device distinction:** The integration target is the Monoprice HTP-1 and the integration platform is Unfolded Circle. Keep those roles distinct from the user's separate Couch device and other project contexts. Do not conflate device identities or operating environments; verify or ask if a role is unclear.

## New-chat instructions

1. Read this document before continuing project work.
2. Verify the live GitHub state (branches, commits, open PRs, checks, and working changes) before assuming a task is complete or starting new work. This document records decisions and intended scope; live repository state is authoritative for implementation status.
3. Preserve the agreed branch strategy below. Do not develop production code directly on `main` or `tests-and-docs`.
4. Keep the approved development phases in order unless the user explicitly changes the plan. Phase 0 is complete; Phase 1.5 automated implementation and validation are complete. Limited physical HTP-1 testing has now verified deferred volume handling during Dirac application, but full Remote/HTP-1 hardware acceptance remains pending. Phase 2 is the next planned development phase. Preserve the complete approved Phase 2–6 roadmap in PROJECT_HANDOFF.md.
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
- While an accepted Dirac operation is active, ordinary non-volume state-changing commands (power, mute, input, sound mode, BEQ, seat-shaker controls, menu, and IR commands) are rejected promptly without a state refresh or write. Volume requests are captured in memory instead of being sent to the receiver.
- A separate Dirac operation lock prevents a second calibration selection while the first is pending. The second request is rejected promptly without sending another HTP-1 write.
- The calibration select keeps displaying the last confirmed slot while the receiver's early `currentdiracslot` value changes. The new slot is published only after the matching request reaches `complete` and a confirming `getmso` reports the expected request ID, slot, and current slot.
- Dirac lifecycle events use a dedicated event and error channel, separate from the ordinary write-convergence event/error channel. Disconnect wakes the background monitor; connection-generation checks prevent a stale task from confirming against a replacement connection.
- The Remote Integration API's `entity_command` result acknowledges command execution/initial failures; stateful entity values are subsequently communicated with `entity_change`. This implementation uses that distinction rather than holding the Remote command open for the full DSP lifecycle. See the official [Unfolded Circle entity command documentation](https://unfoldedcircle.github.io/core-api/entities/) and [integration driver message flow](https://unfoldedcircle.github.io/core-api/integration-driver/write-integration-driver.html).
- QA regressions on `tests-and-docs` cover prompt acknowledgement before completion, no premature displayed slot, deferred volume capture/aggregation, one post-Dirac volume write, immediate rejection of a second Dirac request, refusal/busy handling, asynchronous lifecycle timeout, and delayed final-readback behavior.
- A further QA-only regression now models the observed hardware timing where the receiver first publishes `requested`, the Remote is acknowledged, and a matching standby refusal arrives later. It verifies the background monitor catches the refusal, preserves the last confirmed slot, skips success readback, and releases the Dirac operation lock. Added in `e4a25188815649f00e63c69f66601e4ad5bfe43a`; CI validation is in progress.
- Production commits: `c69ac2fd22e628fa0a09cade87731c86740f7da1` (asynchronous lifecycle) and `a0ea1813b584868e0b3c97dbf8f23f99c0264cd4` (confirmed-display preservation fix); current production head is `a0ea1813b584868e0b3c97dbf8f23f99c0264cd4`. QA test commits include `524493f6f99fbbd74022d29f2f3f18236ba75379`, `23d7fdb5f7bc41502e00d2f555ebbfe8213562b3`, and `0ccf100503f6613a4942eeb2866fe5973da983f6`.
- Automated validation passed against production head `a0ea1813b584868e0b3c97dbf8f23f99c0264cd4` and QA head `0ccf100503f6613a4942eeb2866fe5973da983f6`: Phase 1 WebSocket Safety QA [run 45058395723](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45058395723) passed (112 Phase 1 tests, 95 general regressions with 1 skipped, 33 Phase 0 compatibility tests, 21 regression-gap tests, 2 TLS tests; focused Ruff checks passed; 79% measured coverage); Phase 0 and Full QA [run 45058395750](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45058395750) passed; standard Tests [run 45058395760](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45058395760) passed; ARM64 Test Build [run 45058383533](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45058383533) passed.
- The earlier real-hardware investigation used the integration simulator/debug session connected to a physical HTP-1; no actual Unfolded Circle Remote was involved. At that point, deferred-volume behavior had not yet been tested on the physical HTP-1. The subsequent limited physical HTP-1 tests are recorded in the latest verification addendum below. Full Remote/HTP-1 acceptance remains required. No deployment, merge, release, or upstream PR has been performed.

### Dirac apply-window volume protection — 2026-11-22

The intermittent HTP-1 responsiveness observed during a real hardware Dirac apply led to a protected command window and deferred volume handling.

- At Dirac request start, production code captures the confirmed raw volume, `vpl`, `vph`, and zero point.
- Volume up/down requests are acknowledged promptly and accumulated as a relative dB delta; no volume write or state refresh is sent during DSP application.
- Absolute `set_volume` and normalized `set_volume_level` requests are captured as the latest absolute displayed-dB target. Later relative steps adjust that target; a later absolute request replaces the previous target and clears earlier relative steps.
- Relative intent is bounded against the captured calibration limits. At successful completion, after a confirming full-state readback, the target is translated through the current zero point and current `vpl`/`vph`.
- The existing normalized volume calculation and 5 dB maximum-jump limiter were extracted into one lock-aware helper shared by ordinary `set_volume_level` and the deferred Dirac apply path. The deferred operation sends at most one volume write.
- Non-volume state mutations, menu commands, and IR commands are rejected during the Dirac apply window without sending additional receiver traffic. Commands resume after final confirmation and deferred-volume handling.
- Receiver refusal, failure, timeout, disconnect, invalid starting volume metadata, or invalid final calibration metadata discard the pending volume intent; it is never applied against an unconfirmed state.
- Production commits on `feature-validation`: `ecd02d1` (capture/defer volume and command gate), `fce95e1` (serialize commands at finalization), `62fe325` (format helpers), `79f7e0a` (gate menu/IR commands), `3edb2e3` (support partially initialized device instances), `512bbf0` (recheck command gates after acquiring the transaction lock and add a final write guard), and `282bf48` (preserve compatibility with existing transaction test doubles while reusing the shared volume limiter).
- QA tests on `tests-and-docs`: `d126b41`, `0da7db4`, `6d4e174`, `b02da8f`, `dbafdae`, `4c73394`, and `3ef188c`. Coverage includes aggregation, high-frequency bursts, positive/negative deltas, raw and normalized absolute targets, zero-point changes, calibration bounds, 5 dB limiting, command rejection/release, refusal, timeout, disconnect, invalid calibration metadata, and relative/absolute volume plus non-volume commands queued across the Dirac-start lock boundary.
- ARM64 Test Build passed on production commit `282bf486d4ac6ddc5068b57168177b75e5ccf1b3`: [run 45070154233](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070154233). Phase 0 and Full QA passed on QA commit `3ef188cd1bd5b2fa82f0c44f10a6ca5741c247a8`: [run 45070175100](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070175100). Standard Tests passed on the same QA commit: [run 45070175088](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070175088). Phase 1 WebSocket Safety QA passed: [run 45070175008](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070175008), with 132 Phase 1 tests passing in 36.06 seconds, all Phase 0/general/TLS checks passing, and five isolated Dirac stress runs of 20 attempts each (100 total) passing. Focused Ruff checks passed. Automated tests are not hardware acceptance. No deployment, release, merge, or upstream PR has been performed.

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


### Latest verification update — 2026-11-22

**Verified branch state**

- Production implementation commit: 282bf486d4ac6ddc5068b57168177b75e5ccf1b3 on feature-validation. The only later branch change observed during this review is an update to dumps/integration.log, not production source.
- QA/test snapshot before the documentation-only audit: 7c5ed4c66e7126ddfed106a6cbde89b598c613c0. Documentation-only commits since that snapshot: README 4a0544c; handoff b9005ba and final reconciliation in this document; Phase 1.5 validation record subsequently reconciled on the QA branch; the current file is authoritative. The documentation changes remain confined to tests-and-docs.
- The test/QA branch remains separate from production. QA tests and QA-only workflow changes are not present in the production branch.

**Latest automated validation**

- Phase 1 WebSocket Safety QA: [run 45070175008](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070175008) passed: 132 Phase 1 tests, all Phase 0/general/TLS checks, and five isolated Dirac stress repetitions of 20 attempts each (100 total). Focused Ruff checks passed.
- Phase 0 and Full QA: [run 45070175100](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070175100) passed.
- Standard Tests: [run 45070175088](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070175088) passed.
- ARM64 Test Build: [run 45070154233](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070154233) passed against production commit 282bf486d4ac6ddc5068b57168177b75e5ccf1b3.
- The Phase 1 QA workflow measures device.py and browser.py with pytest-cov and emits terminal and XML coverage reports. The latest explicitly recorded percentage in the handoff history is 79% combined coverage (run 45058395723). The later 45070175008 run passed its coverage-enabled suite, but its exact percentage was not captured in the handoff record; do not label 79% as a newly measured result for that later run. Coverage is strong, but the workflow currently reports rather than enforces a minimum threshold.
- The Phase 1 QA workflow includes the added power/Dirac slow-response, power-toggle, HTTP IR, Remote command-sequence, WebSocket-probe, transaction-safety, and Dirac lifecycle regression tests. The new regression-gap suite explicitly runs power-toggle, HTTP IR, Remote command-sequence, and WebSocket-probe tests. These are automated unit/fake-receiver tests; on-device testing for those cases remains part of the broader hardware effort.
- The broader Ruff rule-family scan remains diagnostic. The required focused Pyflakes (ruff check --select F) check passes. Do not describe the diagnostic Ruff scan as clean or imply every advisory rule has been fixed.

**Limited physical HTP-1 verification of deferred Dirac volume**

Two tests were performed using the integration debug/simulator session connected to the real HTP-1. The actual Unfolded Circle Remote was not involved.

1. Starting at displayed volume -20 dB, repeated volume-up requests during Dirac application were captured and aggregated. The requested accumulated increase was +13 dB. After Dirac completed, one consolidated volume write was issued and the receiver's displayed volume moved to -15 dB, exactly the existing +5 dB maximum-change limit.
2. Starting at displayed volume -15 dB, 30 volume-down requests were captured and aggregated. After Dirac completed, one consolidated write was issued and the receiver's displayed volume moved to -20 dB, again exactly the -5 dB maximum-change limit.

These observations support that the apply-window capture, aggregation, calibration bounds/zero-point translation, and shared 5 dB limiter work on the physical HTP-1 for these two cases. They do not establish complete hardware acceptance or cover all command types.

**Outstanding receiver readback warning**

Both tests also logged "Receiver state mismatch after transaction at /volume" immediately after the consolidated write. A later receiver state event reported the expected displayed volume in each case. This is consistent with a possible immediate readback/convergence timing race, but the cause has not yet been proven. Do not dismiss the warning as harmless, and do not add automatic retries without further investigation because a duplicate write could cause an additional volume change. Investigate the transaction verifier and event ordering before changing behavior.

**Remaining acceptance boundary**

- Unit tests and CI do not replace testing with the actual Unfolded Circle Remote.
- Power/Dirac slow-response and regression-gap cases were approved for automated tests; the user explicitly deferred the corresponding on-device testing to a larger testing effort.
- The two physical HTP-1 Dirac-volume tests are limited evidence, not full Phase 1.5 acceptance.
- No deployment, release, merge, or upstream PR has been performed.



## Architectural hardening — Dirac lifecycle and transaction verification (2026-11-22)

This addendum supersedes older branch-head and CI status statements above. Earlier entries remain historical records of the work performed at those points.

### Pass 1 — Explicit Dirac lifecycle state

The Dirac asynchronous switch flow now uses one explicit integration-owned lifecycle enum on `feature-validation`:

`IDLE → REQUESTED → ACCEPTED → APPLYING → COMPLETE / FAILED`

- `DiracLifecycleState` enforces an allowed transition graph. A new request may begin from either terminal state; invalid transitions raise immediately.
- Removed the overlapping `_dirac_accepting`, `_dirac_display_hold`, and `_dirac_pending_slot_idx` fields. Command blocking and preservation of the last confirmed calibration display are derived from the lifecycle state.
- The operation lock remains solely for serializing concurrent calibration selections. The task handle remains solely for tracking the background monitor; neither is used as a second lifecycle flag.
- A task completion callback handles the edge case where the monitor task is cancelled before its coroutine starts. It transitions an active operation to `FAILED`, discards deferred volume intent, and releases the operation lock. Cancellation after the monitor starts is handled by the monitor's own finalizer.
- The connection generation is captured when the request is sent. A disconnect during acceptance or application cannot allow a stale monitor to confirm a request on a replacement connection.
- `COMPLETE` is entered only after the final full-state readback confirms the request ID, requested slot, and current slot, and deferred-volume finalization has finished. The command gate therefore remains active through the deferred-volume attempt.
- Refusal, busy response, acceptance/completion timeout, disconnect, failed final readback, and cancellation produce `FAILED`. The last confirmed calibration display remains held after failure; ordinary state-changing commands are unblocked.
- The existing deferred-volume behavior is preserved: captured calibration/zero-point basis, relative and absolute request aggregation, calibration bounds, one consolidated post-Dirac write, and the shared 5 dB maximum-jump limiter.

Production commits on `feature-validation`:
- `00153a7c519249f02b782763785aa3bd38219418` — introduce explicit lifecycle state and transition validation.
- `458542a9b33c41e8797bbf211a120db332ece1ac` and `60fc568a0139ca82165b1113ab36b49c67424db9` — finalize lifecycle at authoritative readback and use connection-generation change for acceptance disconnect detection.
- `f98b94acf6069e79105daf55fb9494d174ac690e` — derive display hold from lifecycle and remove unused pending-slot state.
- `852fe5bad3fb31a49d0626386ea7308bdec6f14c` — keep the command gate active through deferred-volume finalization.
- `b8ee891275ac38d8122e3a7a9354094aa67bf88f` — clean up cancellation when the monitor task is cancelled before starting; current production head for this work.

QA-only lifecycle tests on `tests-and-docs` cover legal/illegal transitions, each active/terminal phase, immediate and delayed refusal, busy response, acceptance and completion timeouts, disconnect before and after acceptance, cancellation before the monitor starts, second-request rejection, a new request after terminal states, command-gate lifetime, display preservation, and the existing deferred-volume/5 dB regressions.

Automated validation:
- Phase 1 WebSocket Safety QA [run 45089825685](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45089825685) passed: 140 Phase 1 tests, 81% combined coverage (device.py 84%, browser.py 66%), focused Ruff checks, five isolated Dirac stress repetitions of 20 attempts each (100 total), and both TLS regressions.
- Phase 0 and Full QA [run 45089825680](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45089825680) passed.
- Standard Tests [run 45089825565](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45089825565) passed.
- ARM64 Test Build [run 45089808380](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45089808380) passed against production commit `b8ee891275ac38d8122e3a7a9354094aa67bf88f`.

### Pass 2 — Separate transaction convergence from final verdict

The production implementation introduced in commit `b90d37ffa15044c23714c461638cd536f8e1dd7b` remains the basis of this pass; no additional production transaction behavior was changed.

- `_transaction_mismatch_path()` is a read-only diagnostic helper. It returns the first touched JSON Pointer path that differs, a missing path, or the no-state marker; it does not log.
- `_transaction_matches_state()` is a quiet boolean predicate used during the live convergence wait. It can be called repeatedly while receiver state is still changing without emitting premature error logs.
- `_execute_transaction_locked()` retains the existing send, convergence wait, and authoritative `getmso` refresh. Only after that final full-state readback does it evaluate the mismatch and emit one final diagnostic if the receiver did not apply the transaction.
- The final-verdict behavior, transaction timing, readback sequence, and no-retry policy are unchanged. In particular, no automatic retry was added for the previously observed HTP-1 volume readback warning.

The transaction-safety tests now cover both sides of the distinction:
- An ignored receiver patch still fails after final readback and emits exactly one authoritative transaction mismatch error.
- The mismatch helper identifies the first differing/missing path and handles unavailable state; the live predicate remains quiet.
- A delayed-convergence fake receiver first publishes a relevant but stale live patch, then returns the expected state in the final full-state readback. The transaction succeeds with no transient transaction error log.

QA test commits include `04a1eb18fb7f7804b0ff7dc8bfc5734ed5f76255` (quiet predicate/final diagnostic regressions) and `a57d000f8c227f9f1024d7a09d62da039ef68282` (delayed-convergence regression and deterministic timeout setup).

Final automated validation after both passes:
- Phase 1 WebSocket Safety QA [run 45090272483](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45090272483) passed: 141 Phase 1 tests, 81% combined coverage, five isolated Dirac stress repetitions of 20 attempts each (100 total), and both TLS regressions.
- Phase 0 and Full QA [run 45090272492](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45090272492) passed.
- Standard Tests [run 45090272398](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45090272398) passed.
- Focused Ruff correctness checks passed. The broader Ruff rule-family scan remains diagnostic/non-gating and must not be described as clean.

**Acceptance boundary:** these are automated fake-receiver/unit tests and an ARM64 package build. No actual Unfolded Circle Remote or physical HTP-1 acceptance test was performed as part of these two passes. The earlier two limited physical HTP-1 deferred-volume observations and their immediate-readback warning remain as documented above. No merge, upstream PR, release, or deployment has been performed.


### Volume command coalescing simulation — 2026-11-23

A QA-only design simulation was added in `tests/phase1/test_volume_worker_simulation.py` on `tests-and-docs`. No production volume-command behavior was changed.

The simulation is informed by the slow-response trace in `dumps/integration.log`:
- At 15:12:43.664, the volume-down request path began while Dirac was applying.
- The associated `getmso` response arrived at 15:12:45.754, approximately 2.09 seconds later.
- The trace then recorded a live-convergence timeout at 15:12:47.767 and a later confirmation `getmso` response at 15:12:50.215, approximately 2.45 seconds after that request.

These are observations from the Dirac slow-response scenario, not a measured ordinary volume-write round-trip. The tests use 2.1 seconds as a deliberately slow per-write acknowledgement proxy; this is a simplifying simulation input, not a claim about every HTP-1 volume transaction.

The stress profile is a five-second hold at 10 relative requests per second (50 one-decibel requests), explicitly an assumed test rate rather than a measured Remote repeat rate. It compares two possible write policies:

- **Bounded 5 dB writes:** preserve a conservative maximum per-write change. Starting at -40 dB and targeting +10 dB, the immediate first one-decibel write plus subsequent five-decibel chunks require 11 serialized writes. At the 2.1-second proxy, that is 23.1 seconds of acknowledgement time and approximately 18.1 seconds after release.
- **Unbounded latest-target writes:** allow each write to jump directly to the latest accumulated target. The same timeline needs four serialized writes and settles approximately 3.4 seconds after release (the remaining 1.3 seconds of the in-flight write plus one final 2.1-second acknowledgement). This is closer to the proposed responsiveness, but permits larger individual jumps (+20 dB, +21 dB, and +8 dB in this model).

The 5 dB limit is not currently applied to ordinary `volume_up`/`volume_down` one-decibel commands; it is used by normalized volume setting and Dirac consolidation. The simulation therefore compares the two policies rather than declaring either one to be the required production behavior. The result makes the safety/responsiveness trade-off explicit: the one-round-trip-after-release expectation is optimistic; even the unbounded policy takes about 1.6 proxy round-trips in this timeline.

The model also reflects the HTP-1 protocol accurately in one important respect: live state patches do not carry transaction sequence IDs. A delayed patch may temporarily change the reported snapshot, but it must not overwrite the worker's logical target or transaction-confirmed base. The worker advances from its own authoritative transaction result/readback. Tests cover serialized writes, rapid relative-step accumulation, stale untagged state patches, failure reconciliation without automatic retry, volume bounds, and disconnect cancellation.

Validation status at the time of this handoff update:
- Standard Tests passed on QA commit `14955cb7e131cdafef1efd4b898217a458880583`: [run 45092006864](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45092006864).
- Phase 0 and Full QA passed on the same commit: [run 45092006809](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45092006809).
- Phase 1 test suite step passed on the same commit. The complete Phase 1 workflow was still running its isolated Dirac stress repetitions and TLS checks: [run 45092006882](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45092006882).

**Acceptance boundary:** this is a deterministic model of the proposed architecture, not an implementation test of production volume commands and not hardware validation. It cannot establish how the actual Remote displays optimistic volume changes or how the physical HTP-1 orders delayed state events. Keep the five-second hold test with the actual Remote and HTP-1 on the deferred hardware-validation list. No production source, release, merge, upstream PR, or deployment was changed by this simulation work.


### Volume worker simulation — normal response-time model (2026-11-22)

The earlier 2.1-second Dirac/full-state proxy simulation is retained above as a historical stress case, but it is not representative of normal volume-write response time. The revised deterministic QA model uses the normal 0.3–0.5 second response-time estimate discussed from the earlier captures. These values are simulation inputs based on the capture-derived estimate; this rerun is not a new timed hardware measurement.

Model assumptions:
- Five-second hold at 10 relative requests per second: 50 one-decibel requests, from an assumed stress rate rather than a measured Remote repeat rate.
- Start at -40 dB and finish at +10 dB.
- One volume write may be outstanding at a time.
- Every write is limited to a maximum 5 dB change.
- A write is modeled as complete when a matching post-send `/volume` `msoupdate` arrives.
- The worker immediately sends the latest bounded target after a completion if the target differs from confirmed volume.
- No pre-write `getmso` refresh and no full-state readback after each write.
- One authoritative full snapshot is requested after the worker becomes idle. For this comparison, its latency is also modeled as 0.3–0.5 seconds.
- No automatic retry is modeled.

Results:

| Matching `msoupdate` response time | Serialized writes | Final write completes | Idle snapshot completes | Time after 5 s release |
|---:|---:|---:|---:|---:|
| 0.30 s | 18 | 5.4 s | 5.7 s | 0.7 s |
| 0.40 s | 14 | 5.6 s | 6.0 s | 1.0 s |
| 0.50 s | 11 | 5.5 s | 6.0 s | 1.0 s |

Interpretation:
- All three cases settle the final authoritative snapshot within about one second after the five-second hold ends.
- At 0.50 seconds, roughly five button presses accumulate between completions, so the worker uses 11 writes, each no larger than 5 dB.
- At 0.30 seconds, only about three presses accumulate between completions. The worker therefore sends smaller bounded changes more frequently (18 writes), but catches up sooner after release.
- The write count is not fixed at 11: it depends on the relationship between button-repeat rate and response latency. The 5 dB cap is preserved in every case.
- The model eliminates the old 2.1-second assumption from the ordinary-volume path and represents the proposed optimization: no pre-write refresh and one full snapshot at idle rather than a full read after every write.

The updated QA simulation is in `tests/phase1/test_volume_worker_simulation.py`. Four deterministic tests cover the latency sweep, 5 dB per-write cap, single-write serialization, one idle snapshot, and coalescing of 50 requests. Local pytest result: 4 passed.

Important limitations:
- The 0.3–0.5 second values are the earlier capture-derived normal-response estimate used as inputs, not a fresh hardware timing run.
- The model treats a matching post-send `msoupdate` as the completion event for timing. It does not prove that an untagged update belongs to the write; ABA/stale-duplicate ambiguity and timeout handling remain separate design requirements.
- The snapshot completion time is not the same as verified Remote display convergence. Measuring how long the Remote display takes to match the HTP-1 remains part of hardware acceptance.
- This is a deterministic QA model, not production implementation or hardware validation. No production source, release, merge, upstream PR, or deployment was changed.


### Volume cache freshness and WebSocket event-order regressions — 2026-11-23

QA-only coverage lives in `tests/phase1/test_volume_cache_safety.py` and runs against the `feature-validation` implementation. Production source is unchanged.

The fake receiver maintains authoritative state separately from the integration cache. It can deliver or omit external changes, withhold full snapshots, and inject duplicate, out-of-order, and delayed ABA-replay patches.

Current regression coverage:

- **Silent lost update:** the receiver changes from -20 dB to -10 dB without delivering an `msoupdate`. The current implementation's mandatory pre-write `getmso` must observe -10 dB and write -9 dB. This is a baseline check of unconditional refresh; it does not test a time threshold.
- **Delivered volume update:** a valid `/volume` patch updates raw cached state and parsed displayed volume.
- **Delivered calibration updates:** `/cal/vpl`, `/cal/vph`, and `/cal/zeroPoint` patches update the relative-volume dependencies and enforce the changed upper/lower boundaries.
- **Disconnect:** connection loss clears state and prevents a relative write.
- **Malformed valid-JSON patch:** an invalid JSON Patch operation is rejected, a full snapshot is requested, and the relative command fails closed if that snapshot is unavailable.
- **Duplicate and out-of-order updates:** live matching patches are provisional only; the final authoritative `mso` readback decides transaction success.
- **True delayed ABA replay:** a matching `/volume` event is queued before the transaction, the value changes away, and the queued old event is delivered after the write. Since the protocol has no transaction ID or sequence number, the old event is indistinguishable from a new matching echo; final full-state readback must reject it when receiver state did not change.

### Implemented volume cache validity and freshness policy

The production implementation is now on `feature-validation` at `9884b4f82b48c1015e7468c9e15cc38d2e4edb7c`. The change is limited to ordinary `volume_up` and `volume_down` cache handling; it does not introduce the proposed coalescing worker.

**Validity and recovery**
- Malformed JSON `mso` or `msoupdate` frames invalidate the cached state and request a new full `getmso`.
- Non-object full-state payloads invalidate the cache and request a replacement snapshot.
- Patch batches are applied to a deep-copied candidate. If any operation is malformed, the entire batch is rejected, the cached baseline is discarded, and a full snapshot is requested.
- Partial `msoupdate` events are ignored while the baseline is invalid. Only a later full `mso` object can restore it.
- Relative volume commands require a raw integer volume and finite `vpl`, `vph`, and `zeroPoint`, with `vpl < vph`. Missing values, booleans, strings, NaN, infinity, and inverted bounds fail closed instead of using parser fallback defaults.
- A failed or timed-out authoritative refresh also invalidates the cache. A live write echo alone is not retained as a trusted baseline when the final full snapshot cannot be obtained.

**Freshness**
- Each of `/volume`, `/cal/vpl`, `/cal/vph`, and `/cal/zeroPoint` has its own monotonic observation timestamp.
- A full `mso` refreshes all four timestamps. A patch refreshes only the dependency it actually changes; a parent `/cal` patch refreshes all three calibration dependencies. Unrelated paths do not refresh volume freshness.
- Both validity and freshness are checked after acquiring the serialized transaction lock. An invalid or stale cache triggers one pre-write `getmso`; a fresh valid cache can be used without that extra request.
- The maximum age is `VOLUME_STATE_MAX_AGE = 0.5` seconds. The selected bound is the earliest of the deliberate silent-update intervals requested for the regression sweep (0.5, 2, 5, and 10 seconds). The comparison is strict: age **at or above** 0.5 seconds triggers refresh.
- This is a conservative policy bound, not a measurement of the HTP-1's event-loss rate. The explicit just-below-boundary test documents the remaining limitation: a silently lost external update less than 0.5 seconds old can still be indistinguishable from a current cache. The protocol has no sequence number or gap signal to detect it sooner.

**Preserved behavior**
- The transaction lock, live convergence wait, final authoritative full-state readback, no-retry policy, 5 dB safeguards used by normalized/Dirac volume handling, and all Dirac deferred-volume capture/finalization behavior remain intact.
- Every successful state-changing transaction still ends with the existing authoritative snapshot. This refreshes the four timestamps, so a queued relative-volume press can generally use the just-confirmed cache rather than issuing a redundant pre-write snapshot.
- Other commands retain their existing refresh behavior. No coalescing worker, automatic retry, or device-specific timing assumption was introduced.

QA coverage in `tests/phase1/test_volume_cache_safety.py` now includes:
- Silent external volume changes with the update omitted at 0.5, 2, 5, and 10 seconds; both up and down paths.
- Delivered external volume/calibration patches, no unnecessary pre-write refresh for a fresh delivered volume update, per-dependency timestamp updates, full-snapshot timestamp reset, and parent `/cal` handling.
- Unrelated patches not refreshing volume dependencies, and the freshness check occurring only after the transaction lock is acquired.
- Disconnect, malformed JSON, malformed patch batches, partial-update rejection while invalid, full-snapshot-only recovery, invalid/missing numeric inputs, and inverted bounds.
- Duplicate, out-of-order, and delayed ABA-replay volume patches remaining provisional until the authoritative full snapshot.
- Failed final readback invalidating the unconfirmed cache, plus the documented sub-0.5-second silent-update limitation.

Production commits:
- `a77a0ee2541a6c934bc35931f5dce2555f8dd3a7` — invalidate malformed state and validate relative-volume inputs.
- `9d564f91ddb27e7531030d12e28d82e333481a90` — preserve state-waiter wake-up on WebSocket loss.
- `71e93a3921733d6e0b20adce9bad4a7378509efb` — track per-dependency monotonic freshness and gate volume-up.
- `514f85dad235e34b3299207630c28949d79070a1` — apply the same freshness gate to volume-down.
- `9884b4f82b48c1015e7468c9e15cc38d2e4edb7c` — invalidate the cache when an authoritative refresh fails.

The Standard Tests workflow was also adjusted to check out `feature-validation` as the implementation under test, keeping QA tests/docs on `tests-and-docs` while avoiding tests running against the older QA-branch copy of production code.

### Validation status

For QA commit `4f6ff939065056c003fc340d8d4bca6695e680b1`:
- Standard Tests [run 45101402643](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45101402643) passed: 93 passed, 1 skipped.
- Phase 0 and Full QA [run 45101402455](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45101402455) passed: 95 passed, 1 skipped, plus 33 Phase 0 tests.
- Phase 1 WebSocket Safety QA [run 45101402709](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45101402709) passed: 180 Phase 1 tests, 82% combined coverage (device.py 86%, browser.py 66%), five isolated Dirac stress repetitions, and both TLS regressions.
- ARM64 Test Build for production commit `9884b4f` [run 45101254231](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45101254231) passed.

The additional just-below-0.5-second limitation test is on the newer QA commit `1888dbccd01cae3b867c29f593569cb17c9d7ec7`; its final Phase 1 run is still pending at the time of this handoff update. The focused Ruff correctness checks passed. The broader Ruff scan remains diagnostic/non-gating and still reports existing findings; do not describe it as clean.

**Acceptance boundary:** deterministic tests are authoritative for the injected state, timing, and event-order behavior. No physical HTP-1/Remote hardware test was performed for this cache policy. No merge, upstream PR, release, or deployment has been performed.

### Pre-change regression comparison and hardware acceptance gate

The new `tests/phase1/test_volume_cache_safety.py` suite was run against the pre-cache-hardening implementation commit `b8ee891275ac38d8122e3a7a9354094aa67bf88f` using an isolated implementation checkout. The focused baseline run produced **22 failures and 14 passes**. The failures expose the expected missing protections: unconditional pre-write refresh despite a delivered fresh update, no per-dependency freshness metadata, stale/malformed cache remaining trusted, missing/invalid calibration inputs being accepted, and failure to invalidate an unconfirmed cache after a failed final snapshot. This confirms the new regressions distinguish the hardened implementation from the previous head; the baseline failure is intentional, not a current-branch CI failure.

Baseline run: [Phase 1 WebSocket Safety QA run 45102729576](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45102729576), focused test step output: 22 failed, 14 passed. The workflow also ran the full existing regression suite against the baseline and stopped there with 15 failures, 80 passed, 1 skipped because the current QA test fixtures now assert the new invalidation behavior and use the new cache metadata helpers. That broader baseline failure is expected for this comparison and is not a clean full-suite baseline.

The temporary baseline-only workflow changes were reverted. `.github/workflows/phase1-qa.yml` again defaults to `feature-validation` and contains no baseline-only step.

**Hardware acceptance remains outstanding and cannot be performed from the GitHub CI environment.** It requires the actual HTP-1 and Remote in normal operating mode. Before merging, record:

1. Starting receiver volume and Remote-displayed volume.
2. Hold volume-up for exactly 5 seconds, then release. Record the number of button repeats if visible, the time from release until the Remote display reaches the receiver's final volume, and whether any `Receiver state mismatch after transaction` messages appear.
3. Repeat with volume-down to confirm symmetric behaviour.
4. For the silent-update check, change volume externally on the HTP-1 while the integration does not receive the corresponding WebSocket update. Run the check once after a 0.5-second cache age and once after a 2-second cache age. Confirm the resulting relative step is based on the receiver's externally changed value, not the stale cached value. Record the raw receiver value, cached/displayed value, command target, and whether a pre-write `getmso` occurred.
5. Restore normal connectivity and verify a full snapshot re-establishes the displayed state before further volume commands.

Do not simulate a dropped WebSocket update by simply pausing all traffic unless the test also preserves the ability to observe the subsequent refresh; the point is to distinguish an actually omitted volume patch from a disconnected or invalid connection, which should already force refresh. If the receiver cannot be made to omit exactly one update while remaining connected, record that limitation rather than treating a normal external volume change as a lost-update test.

The 0.5-second maximum age remains provisional pending those measurements. The 2-second check is a comparison point, not the current production setting. Do not merge until the hardware results are reviewed and the threshold is either confirmed or revised.

