# Phase 1.5 — Integration and State-Flow Test Hardening

## Scope and outcome

Phase 1.5 hardens the integration's connection lifecycle, entity synchronization, command/state round trips, BEQ browser behavior, and state-changing WebSocket transactions. It is a test-hardening phase; QA-only tests, fixtures, and workflow changes remain on `tests-and-docs`. Production corrections remain on `feature-validation`.

**Status: Automated implementation and validation complete; real HTP-1 hardware acceptance remains pending.**

## Production implementation

Production source branch: `feature-validation`  
Latest verified production head: `366fad4a8457dc0c9895ce37156573236eae20e2`

Relevant production commits:

- `5b44cd47143407401cd6bf471e5a77c855d4bf04` — serialize full state-changing operations, refresh current receiver state before decisions and read/modify/write, then verify touched JSON paths against a fresh `getmso` snapshot.
- `d2bd00c` — refresh source, preset, and calibration selections before choosing values.
- `58d93e1` and `f44c4f4` — validate absolute volume against fresh calibration bounds and fail safely when required state is missing.
- `366fad4a8457dc0c9895ce37156573236eae20e2` — bound state refresh with a cancellable event waiter.

The existing PEQ placement and BEQ browser behavior are also on `feature-validation`:

- `d45043e` requires PEQ Pre for BEQ without changing receiver placement.
- `6eb1d78` gates catalogue browsing when placement is not confirmed as Pre-Dirac, displays the non-playable **BEQ Unavailable** information item, and preserves Clear BEQ when a filter is already active.

The seat-shaker trim readback correction from PR #4 is merged into `feature-validation` at `652f8c4fc8bebd88701f7d96975824a3ca528657`.

## Transaction safety contract

- Serialize the complete state-changing transaction, not only an individual WebSocket frame.
- Refresh receiver state before read/modify/write and before deriving source, calibration, seat-shaker preset, or absolute-volume decisions.
- Do not assume `changemso` has an acknowledgement. Follow writes with a fresh `getmso` snapshot and verify every touched JSON path.
- Abort on refresh timeout, disconnect, connection-generation change, or mismatched/partial readback.
- Never blindly replay an incomplete transaction after reconnect.
- Preserve the last state actually reported by the receiver. Do not report an unverified operation as successful or fabricate a rollback after the receiver has echoed a change.
- Never write `/peq/location`. BEQ is allowed only when current receiver state explicitly reports `peq.location == "pre"`; post, missing, malformed, or unknown placement fails closed.
- BEQ filters remain on the LFE `sub1` path; do not write independent post-Dirac subwoofer filters.

## QA-only coverage and results

QA branch: `tests-and-docs`  
Latest verified QA branch head at documentation review: `e461e7be7ca0203f90260643af1581ea03356c57`  
Latest test-hardening commit before the handoff update: `49f59ff43610a2f16aa6d58bf7625df7edb32a46`

Failure-injection coverage includes:

- stale cached PEQ Pre versus actual receiver PEQ Post, aborting before writes;
- receiver ignoring a BEQ patch and readback detecting the mismatch;
- partial BEQ application and mismatch detection;
- state-refresh timeout aborting before writes;
- disconnect after a BEQ write without claiming success or replaying;
- concurrent relative volume increments serializing correctly.

The broader Phase 1.5 QA scope also covers fake-WebSocket initial-state retrieval, entity synchronization, command/state round trips, BEQ index validation, and browser behavior.

Verified CI results against the intended `feature-validation` production source:

| Workflow | Run | Result |
|---|---|---:|
| Regular Tests | [44990210124](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44990210124) | 94 passed, 1 skipped |
| Phase 0 QA | [44990210207](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44990210207) | 33 passed |
| Phase 1 QA | [44990210163](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44990210163) | 71 passed |

Phase 1 QA coverage report: `device.py` 76%, `browser.py` 57%, combined 70%.

## ARM64 build artifact

- Workflow: [ARM64 Test Build run 44990201038](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44990201038)
- Branch/commit: `feature-validation` / `366fad4a8457dc0c9895ce37156573236eae20e2`
- Artifact: `uc-intg-monoprice_htp1-2.4.2-aarch64`
- Artifact ID: `14741452934`
- Size: 24,304,499 bytes
- SHA-256: `94a0ce851c63ac589611bf9dd1858190ad3f0e5189257b1c9dba5136729b6e44`
- Expiration at time checked: 2026-11-29 05:38:03 UTC

This is a successful ARM64 integration build artifact, not a published release. It has not been deployed or installed for hardware acceptance.

## Hardware acceptance — outstanding

Automated tests and CI do not prove behavior on the actual Remote and HTP-1. Keep Phase 1.5 open until hardware acceptance is completed and recorded.

Suggested checks:

1. Install the ARM64 artifact on the test Remote when ready and confirm the integration starts and connects.
2. Exercise volume, mute, input, trim, and other state-changing controls; compare results with receiver state.
3. Test concurrent commands and confirm receiver state remains coherent.
4. With PEQ explicitly set to Pre, load and clear a BEQ; verify the intended LFE path and receiver filters.
5. With PEQ Post, missing, or unreadable, verify BEQ browsing/loading is unavailable and no placement write occurs.
6. Exercise disconnect/reconnect during normal operation and during a state-changing command; confirm no blind replay and accurate readback.
7. Confirm Clear BEQ remains available when a BEQ is already active but placement is no longer eligible.

Record actual Remote/HTP-1 observations separately from automated test and build results. No merge, release, tag, or deployment has been performed as part of this validation record.


## Later implementation and validation addendum — 2026-11-22

This addendum supersedes the earlier "latest verified" commit and CI references above for the newer Dirac lifecycle and deferred-volume work. The earlier Phase 1.5 results remain as historical baseline evidence.

### Current branch state

- Production implementation commit: 282bf486d4ac6ddc5068b57168177b75e5ccf1b3 on feature-validation. The branch has one later log-only update to dumps/integration.log; no later production source change was found during this review.
- QA/documentation head before this documentation update: 7c5ed4c66e7126ddfed106a6cbde89b598c613c0 on tests-and-docs.
- QA-only test files and workflows remain isolated on tests-and-docs.

### Dirac asynchronous lifecycle and apply-window behavior

- Dirac selection acknowledges the Remote after receiver acceptance, then monitors the matching receiver-generated request asynchronously until completion or failure.
- While Dirac is applying, volume requests are captured and consolidated; at most one volume write is applied after successful completion and confirming receiver readback.
- The shared volume helper applies calibration bounds, zero-point translation, and the existing 5 dB maximum-change limiter.
- Other state-changing commands—including power, mute, input, surround mode, BEQ, Seat Shaker, menu, and IR commands—are rejected during the apply window. A second Dirac selection is also rejected.
- Refusal, timeout, disconnect, or invalid volume/calibration metadata discards pending volume intent. The last confirmed calibration remains displayed until completion is confirmed.
- QA coverage includes relative/absolute volume aggregation, high-frequency bursts, calibration bounds, zero-point changes, the 5 dB limiter, queued commands across the lock boundary, refusal, timeout, disconnect, and release of the operation lock.

### Latest automated validation

- Phase 1 WebSocket Safety QA [run 45070175008](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070175008): passed, 132 Phase 1 tests; Phase 0/general/TLS checks passed; five isolated Dirac stress repetitions × 20 attempts (100 total) passed; focused Ruff checks passed.
- Phase 0 and Full QA [run 45070175100](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070175100): passed.
- Standard Tests [run 45070175088](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070175088): passed.
- ARM64 Test Build [run 45070154233](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/45070154233): passed against production commit 282bf486d4ac6ddc5068b57168177b75e5ccf1b3.
- Latest explicitly recorded coverage percentage remains 79% combined for the measured device.py and browser.py modules (run 45058395723). The later coverage-enabled run 45070175008 passed, but the exact percentage was not recorded in the handoff. The workflow emits terminal and XML coverage reports but does not enforce a minimum threshold. Do not represent 79% as a freshly measured value for run 45070175008.

### Limited physical HTP-1 verification

Two tests used the integration debug/simulator session connected to the physical HTP-1; no actual Unfolded Circle Remote was involved.

- Volume up: from displayed -20 dB, a +13 dB accumulated request resulted in one consolidated write and final displayed volume -15 dB, limited to +5 dB.
- Volume down: from displayed -15 dB, 30 accumulated down requests resulted in one consolidated write and final displayed volume -20 dB, limited to -5 dB.

These tests support the deferred-volume aggregation, calibration translation/bounds, and shared limiter for the tested cases. Both also logged "Receiver state mismatch after transaction at /volume" immediately after the write, followed by a later state event showing the expected displayed volume. The cause remains unresolved; treat it as an outstanding verification timing/race investigation, not as a confirmed harmless warning or a confirmed failed volume operation. Do not add automatic retries without proving the cause.

### Remaining hardware scope

- Full actual Remote plus HTP-1 acceptance remains pending.
- The user explicitly deferred on-device testing for the power/Dirac slow-response and other regression-gap scenarios to a larger testing effort; those cases are covered by automated tests only.
- Continue to distinguish fake-receiver/CI results from physical HTP-1 tests and actual Remote acceptance.
- No deployment, release, merge, tag, or upstream PR has been performed.
