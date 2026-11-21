# HTP-1 Integration — Project Handoff

> **Purpose:** This is the continuity document for future development chats. Read it before proposing or making changes. This project is the Monoprice HTP-1 integration in this repository. It is not CouchOS development and must not be confused with the separate Fire TV or hosted BEQ catalogue workstreams.

## New-chat instructions

1. Read this document before continuing project work.
2. Verify the live GitHub state (branches, commits, open PRs, checks, and working changes) before assuming a task is complete or starting new work. This document records decisions and intended scope; live repository state is authoritative for implementation status.
3. Preserve the agreed branch strategy below. Do not develop production code directly on `main` or `tests-and-docs`.
4. Keep the six development phases in order unless the user explicitly changes the plan. Phase 0 is the remote reverse-proxy access prerequisite.
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

The phases below are the approved plan. Phase 0 is added as the prerequisite for remote testing through the user's existing reverse-proxy setup. Phases 1–6 retain the user's specified scope.

### Phase 0 — Remote access through the existing reverse proxy

**Goal:** Make the user's existing private reverse-proxy route a supported, documented, repeatable way to reach and test the remote HTP-1. Do not replace or redesign the network.

- Use the existing Synology reverse proxy and Tailscale/Caddy route described below.
- Ensure the HTP-1 controller WebSocket endpoint is reachable through the proxy, including the required WebSocket upgrade/forwarding headers.
- Ensure the test environment resolves `htp1-remote` to the Synology reverse-proxy host as required.
- Verify both the HTP-1 web interface route and the controller WebSocket route through the proxy.
- Document the endpoint, hostname-resolution prerequisite, and troubleshooting/verification steps in the QA documentation.
- Use this route for remote HTP-1 integration testing instead of enabling public port forwarding or inventing another tunnel.
- Keep credentials and private access details out of logs and public documentation.

**Acceptance:** The remote test environment can consistently resolve and connect through the existing proxy to the HTP-1 web interface and controller WebSocket endpoint, and the setup is documented on `tests-and-docs`. Network reachability alone does not count as HTP-1 hardware acceptance for later phases.

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

## Existing remote HTP-1 access topology

This is the user's existing private route. Use it as the default remote test path; do not enable public port forwarding or replace it without explicit approval.

```text
HTP-1 integration / remote test client
    |
    |  htp1-remote:18081
    v
Synology reverse proxy — 10.0.0.56
    |  WebSocket forwarding enabled
    |
    |  Tailscale private route
    v
UGREEN host — Caddy
    |  100.125.151.26:18080
    v
Monoprice HTP-1
       10.0.0.141:80
```

Known connection details:

| Purpose | Address |
|---|---|
| Proxy hostname | `htp1-remote` |
| Synology reverse-proxy host | `10.0.0.56` |
| Proxy port | `18081` |
| Controller WebSocket | `ws://htp1-remote:18081/ws/controller` |
| HTP-1 web interface | `http://htp1-remote:18081/#/` |
| IR command path | `/ircmd` |
| UGREEN host's Tailscale address | `100.125.151.26` |
| UGREEN Caddy listener | `100.125.151.26:18080` |
| HTP-1 local endpoint | `10.0.0.141:80` |

Operational notes:

- The Synology reverse proxy has WebSocket support/headers enabled.
- The route passes through Tailscale to Caddy on the UGREEN host, which forwards to the HTP-1.
- The client/test environment must resolve `htp1-remote` to `10.0.0.56`. A hosts-file entry was used previously; verify it exists in the current test environment rather than assuming it does.
- The topology and addresses are operational context for private development. Do not copy them into public upstream documentation or expose credentials.
- If the connection fails, verify hostname resolution, Tailscale reachability, Caddy forwarding, and WebSocket upgrade handling in that order. Do not change multiple network layers at once.
- The previously successful SSH/Tailscale connectivity test confirmed the private route was working at that time; always re-check current connectivity when troubleshooting.

## Separate workstreams — do not conflate

The following are not phases in the roadmap above:

1. **Hosted BEQ catalogue work:** catalogue publishing/compatibility, its own hardening tasks, and related CI. Keep it distinct from the HTP-1 feature roadmap.
2. **Generic performance/hardening investigations:** treat these as separately scoped tasks unless the user explicitly maps an item into one of the phases above.
3. **Other integrations or CouchOS development:** outside the scope of this HTP-1 project handoff.

## Current status tracking

Update this section as work progresses. Record verified facts only.

| Item | Status |
|---|---|
| Branch strategy | Agreed: `main` mirrors upstream; `tests-and-docs` holds QA/docs; `feature/*` holds production development. |
| Phase 0 | Added to the approved roadmap; verify/document the existing proxy path and its prerequisites. |
| Phases 1–6 | Approved scope; implementation status must be verified against current commits, PRs, tests, and hardware checks before being marked complete. |
| Handoff location | `docs/PROJECT_HANDOFF.md` on `tests-and-docs` only. |

**When updating status:** include the relevant branch, commit SHA, PR link (if applicable), CI run/result, and whether real HTP-1 hardware was tested. Do not mark a phase complete based only on an implementation commit.
