# Phase 1 — Correctness and Safety Validation

## Scope

Phase 1 implementation covers:

- Serialize persistent HTP-1 WebSocket writes through a shared async lock.
- Require PEQ Pre for BEQ application and route new BEQ filters through the pre-Dirac LFE path (sub1) only.
- Remove legacy BEQ tags during replacement without writing independent post-Dirac subwoofer filters.
- Exclude hidden and add-on-owned inputs from manual input selection; validate requested sources against the eligible input list.
- Require an HTP-1 connection before entity registration and clear stale device state when the connection is lost.
- Bound the BEQ catalogue entry-lock registry by reference-counting in-flight requests and reclaiming locks after completion or cancellation.
- Validate volume state before adjustments and enforce the HTP-1 Seat Shaker Trim range of -24 to +6 dB.

## Production implementation

- Feature branch: feature/phase-1-websocket-safety
- Feature head: d218f8a21fbe22576316305307b99330d3cb4368
- Validation PR: [#3 — Complete Phase 1 correctness and safety hardening](https://github.com/joemacjr92/uc-intg-monoprice-htp1/pull/3)
- PR merged into feature-validation: f59e4945e92a46cdbfbd766c04302ffec2f90402
- Production diff against the Phase 0 validation baseline: intg_monoprice_htp1/device.py and intg_monoprice_htp1/browser.py only.

No changes were made to main.

## Automated validation

Phase 1 QA workflow: [run 44977615939](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44977615939)

| Test group | Result |
|---|---:|
| Existing regression suite | 91 passed, 1 skipped |
| Phase 0 compatibility tests | 33 passed |
| Phase 1 regression tests | 11 passed |

Regular Tests workflow: [run 44977640978](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44977640978) — 91 passed, 1 skipped.

The Phase 1 regression tests cover WebSocket write serialization, write failure recovery, disconnected sends, add-on/hidden input eligibility, BEQ Pre/LFE-only routing, BEQ preflight failure safety, Seat Shaker Trim bounds, and catalogue lock cleanup after successful, concurrent, and cancelled requests.

## ARM64 validation build

- Workflow: [ARM64 Test Build run 44977763697](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44977763697)
- Branch: feature-validation
- Commit: f59e4945e92a46cdbfbd766c04302ffec2f90402
- Result: success
- Version: 2.4.2
- Artifact: uc-intg-monoprice_htp1-2.4.2-aarch64
- Packaged tarball size: 24,300,475 bytes
- Artifact download: [GitHub Actions artifact](https://github.com/joemacjr92/uc-intg-monoprice-htp1/actions/runs/44977763697/artifacts/14736830431)

The workflow builds and uploads an artifact only. It does not publish a Docker image, release, or tag and does not deploy to a Remote.

## Hardware acceptance

Pending

The ARM64 artifact has not yet been installed on the Remote for Phase 1 hardware acceptance. Keep Phase 1 open until the user confirms the Remote and actual HTP-1 behavior.

Suggested hardware checks:

1. Confirm the integration starts and registers its entities after the HTP-1 connection is established.
2. Exercise multiple state-changing commands close together and confirm the receiver remains responsive and state remains coherent.
3. Load a BEQ and confirm PEQ placement is Pre, new BEQ filters are applied only to the intended LFE path, and post-Dirac subwoofer outputs are not independently modified.
4. Confirm add-on-owned inputs are not offered as manually selectable sources and invalid source requests are rejected.
5. Confirm volume and Seat Shaker Trim controls remain within receiver-reported/hardware limits.
6. Disconnect and reconnect the HTP-1 and confirm stale state is cleared and entities recover correctly.
7. Browse/select BEQ entries repeatedly and confirm catalogue requests continue working without lock-registry growth.

Record actual Remote/HTP-1 observations separately from automated test and build results. Do not include private addresses, hostnames, endpoints, tunnel configuration, or proxy topology in this record.
