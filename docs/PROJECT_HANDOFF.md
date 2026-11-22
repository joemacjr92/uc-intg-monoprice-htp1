# HTP-1 Integration — Project Handoff

> **Purpose:** This is the continuity document for future development chats. Read it before proposing or making changes. This repository contains the **Unfolded Circle integration for the Monoprice HTP-1**. Keep that integration/platform context distinct from the user's separate Couch device and Couch-related project context, as well as from the Fire TV and hosted BEQ catalogue workstreams.
>
> **Device distinction:** The integration target is the Monoprice HTP-1 and the integration platform is Unfolded Circle. Keep those roles distinct from the user's separate Couch device and other project contexts. Do not conflate device identities or operating environments; verify or ask if a role is unclear.

## New-chat instructions

1. Read this document before continuing project work.
2. Verify the live GitHub state (branches, commits, open PRs, checks, and working changes) before assuming a task is complete or starting new work. This document records decisions and intended scope; live repository state is authoritative for implementation status.
3. Preserve the agreed branch strategy below. Do not develop production code directly on `main` or `tests-and-docs`.
4. Keep the approved development phases in order unless the user explicitly changes the plan. Phase 0 is the configurable-port prerequisite for private remote connectivity; Phase 1.5 is the newly approved test-hardening phase between Phases 1 and 2.
5. Do not silently add, remove, or reinterpret requirements. Ask before expanding scope.
6. Preserve existing behavior unless a specific correction is required by the phase. Add regression coverage for each correction.
7. Distinguish automated tests, CI results, remote connectivity checks, and actual HTP-1 hardware acceptance. Never claim one proves another.
8. Do not push to upstream, merge PRs, publish releases, or deploy without explicit user authorization.
9. Update this document on `tests-and-docs` when the user approves a material plan or status change. Keep it out of production feature PRs to upstream.

## Repository and branch strategy

Repository: [joemacjr92/uc-intg-monoprice-htp1](https://github.com/joemacjr92/uc-intg-monoprice-htp1)  
Upstream: [mase1981/uc-intg-monoprice-htp1](https://github.com/mase1981/uc-intg-monoprice-htp1)

| Branch | Purpose |
|---|---|
| `main` | Mirror Mase's upstream production code. Do not develop independent changes here. |
| `tests-and-docs` | QA and documentation workspace: tests, fixtures, project handoff, and branch-specific validation workflows. |
| `feature/*` | Focused production-code development. Branch from the appropriate current baseline and use the QA infrastructure on `tests-and-docs`. |
| Existing specialized branches | Preserve their purpose and history. Do not repurpose or delete without approval. |

### Branch rules

- Keep the fork's `main` aligned with upstream; do not put local product development there.
- Keep tests, fixtures, project documentation, and QA-only workflows on `tests-and-docs`.
- Implement production changes on focused `feature/*` branches.
- Upstream PRs must contain only the intended production changes. Do not include this handoff, QA-only workflows, test fixtures, or unrelated documentation.
- Do not create a new branch when the user has specified an existing branch, and do not rewrite branch history without explicit approval.
- Before creating a feature branch, inspect the current branch heads and choose the correct base. Do not assume that `tests-and-docs` is the production base.

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

**Constraints:** This is a test-focused phase. Preserve production behavior. If tests expose a real defect, isolate the correction, add a regression test, and keep the production change narrowly scoped. Do not bundle unrelated refactoring or feature work. Keep test-only code, fixtures, coverage configuration, and QA workflow changes on `tests-and-docs`; production fixes, if required, belong on a focused `feature/*` branch. Do not include QA-only material in upstream PRs.

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
| Phase 1.5 | **In progress — lifecycle, connected entity sync, and command/state round trips expanded.** `tests/phase1/test_websocket_lifecycle.py` covers fake-server connection and initial state; `test_connected_entity_sync.py` covers connected entity state and missing optional fields; `test_command_state_roundtrips.py` covers volume, mute, and input selection. New `tests/phase1/test_audio_control_roundtrips.py` covers seat-shaker mute, preset selection/current trim readback, trim command readback, BEQ load and clear, including PEQ Pre enablement and LFE-only `sub1` filter writes. The trim readback test exposed a production mismatch: `set_ss_trim()` updates `/shaker/trim`, but the parser read only the saved preset trim. Focused fix is proposed in [PR #4](https://github.com/joemacjr92/uc-intg-monoprice-htp1/pull/4), targeting `feature-validation`; it reads current top-level trim with saved-preset fallback. QA ran against that fix branch: 23 Phase 1 tests passed, 33 Phase 0 tests passed, and 94 regression tests passed with 1 intentional skip ([Phase 1 QA](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44983059653), [Phase 0/full QA](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44983059693), [regular tests](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44983059677)). The PR is open and not merged. Remaining scope: disconnect/reconnect recovery, BEQ index loading, and coverage reporting. QA-only work stays on `tests-and-docs`; production corrections use focused feature branches. |
| Phases 2–6 | Approved scope; implementation status must be verified against current commits, PRs, tests, and hardware checks before being marked complete. |
| Handoff location | `docs/PROJECT_HANDOFF.md` on `tests-and-docs` only. |

**When updating status:** include the relevant branch, commit SHA, PR link (if applicable), CI run/result, and whether real HTP-1 hardware was tested. Do not mark a phase complete based only on an implementation commit.
