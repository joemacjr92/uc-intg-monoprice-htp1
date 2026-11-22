# HTP-1 Integration — Project Handoff

> **Purpose:** This is the continuity document for future development chats. Read it before proposing or making changes. This repository contains the **Unfolded Circle integration for the Monoprice HTP-1**. Keep that integration/platform context distinct from the user's separate Couch device and Couch-related project context, as well as from the Fire TV and hosted BEQ catalogue workstreams.
>
> **Critical device distinction:** The remote test client at `10.0.0.25` is the **Couch device**. It is used as a client/test host in the remote access setup; it is **not** the Unfolded Circle Remote and it is **not** the Monoprice HTP-1. Do not call it an Unfolded Circle device or confuse its identity/operating environment with the integration target. The integration target is the HTP-1; the integration platform is Unfolded Circle. Refer to each system by its actual role. If any device identity or role is unclear, verify it or ask rather than importing assumptions from another project or chat.

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

### Phase 0 — Configurable HTP-1 port and private reverse-proxy access

**Goal:** Support a configurable HTP-1 HTTP/WebSocket port so the integration can use the user's private IP-based Synology Caddy route, while preserving the default local connection.

- Add a port field to setup; default to `80`.
- Validate ports as integers in the range 1–65535.
- Persist the configured port with each device entry.
- Use the configured port for controller WebSocket connections, setup probing, and HTTP IR commands.
- Preserve compatibility with existing configuration and backup data that do not contain a port; these entries default to `80`.
- Preserve configured ports through backup and restore.
- Use the preferred Synology Caddy route at `10.0.0.56:18082` for remote integration testing; retain the existing DSM hostname route at `htp1-remote:18081` as a fallback.
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

There are now two private routes from the remote test environment to the HTP-1. Keep both available: the original Synology DSM reverse-proxy route remains the fallback, while the separately deployed Synology Caddy route is the validated IP-based route for the HTP-1 integration. Do not enable public port forwarding or remove either route without explicit approval.

### Preferred integration test route — Synology Caddy

```text
Unfolded Circle Remote / integration
    |
    |  10.0.0.56:18082
    v
Synology Caddy — Docker, host networking
    |
    |  Synology host's Tailscale route
    v
UGREEN host — Caddy
    |  100.125.151.26:18080
    v
Monoprice HTP-1
       10.0.0.141:80
```

Synology Caddy deployment details:

- Docker Compose project directory: `/volume1/docker/caddy` (the user's deployed directory).
- Compose file: `docker-compose.yml`.
- Caddyfile: `Caddyfile`.
- Container name: `caddy-htp1`.
- Image: `caddy:2`.
- Network mode: `host` so the container can use the Synology host's Tailscale route.
- Persistent mounts: `./Caddyfile:/etc/caddy/Caddyfile:ro`, `./data:/data`, and `./config:/config`.
- Restart policy: `unless-stopped`.
- Caddy listens on port `18082` and proxies requests to `100.125.151.26:18080`.
- Caddy automatically handles WebSocket upgrades for reverse-proxied WebSocket connections.

Caddyfile used:

```caddyfile
:18082 {
    reverse_proxy 100.125.151.26:18080
}
```

Compose service used:

```yaml
services:
  caddy:
    image: caddy:2
    container_name: caddy-htp1
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./data:/data
      - ./config:/config
```

Known connection details:

| Purpose | Address |
|---|---|
| Preferred integration host | `10.0.0.56` |
| Preferred integration port | `18082` |
| Synology Caddy URL | `http://10.0.0.56:18082/#/` |
| Synology Caddy upstream | `100.125.151.26:18080` |
| UGREEN host's Tailscale address | `100.125.151.26` |
| HTP-1 local endpoint | `10.0.0.141:80` |

### Original fallback route — Synology DSM reverse proxy

```text
Remote test client
    |
    |  htp1-remote:18081
    v
Synology DSM reverse proxy — 10.0.0.56
    |  WebSocket forwarding headers enabled
    |
    |  Tailscale private route
    v
UGREEN host — Caddy
    |  100.125.151.26:18080
    v
Monoprice HTP-1
       10.0.0.141:80
```

| Purpose | Address |
|---|---|
| Proxy hostname | `htp1-remote` |
| Synology reverse-proxy host | `10.0.0.56` |
| Existing proxy port | `18081` |
| Controller WebSocket | `ws://htp1-remote:18081/ws/controller` |
| HTP-1 web interface | `http://htp1-remote:18081/#/` |
| IR command path | `/ircmd` |
| UGREEN Caddy listener | `100.125.151.26:18080` |

### Verified behavior and operational notes

- The original Synology DSM reverse-proxy route works by hostname, including its HTP-1 web interface and WebSocket. Directly entering the Synology IP in DSM's source Hostname field was rejected by DSM validation, so an IP-based DSM rule was not used.
- The new Synology Caddy instance was deployed separately on port `18082`; the existing DSM reverse-proxy rule on port `18081` was left intact.
- Tailscale is installed as a Synology application on the NAS, not inside a Tailscale Docker container. Synology Caddy uses host networking to access the Synology host's Tailscale route to the UGREEN.
- The user confirmed that `http://10.0.0.56:18082` loads and allows navigation through to the HTP-1 interface. The user then confirmed the Unfolded Circle Remote integration connects successfully using host `10.0.0.56` and port `18082`, and that configurable-port behavior is working.
- Treat the new route as hardware-tested connectivity for this setup, but do not infer that all Phase 0 acceptance checks or later-phase hardware tests are complete.
- The Couch device / remote test client (`10.0.0.25`) is separate from the Unfolded Circle Remote and the HTP-1. Keep each system's identity and role distinct.
- These addresses and configuration details are private operational context. Do not copy them into public upstream documentation or expose credentials.
- If the new route fails, check the Synology Caddy container/logs, host-network access to Tailscale, the UGREEN Caddy listener, and then the HTP-1 backend. Test one network layer at a time.
- Keep the original `htp1-remote:18081` route available as a fallback.

## Separate workstreams — do not conflate

The following are not phases in the roadmap above:

1. **Hosted BEQ catalogue work:** catalogue publishing/compatibility, its own hardening tasks, and related CI. Keep it distinct from the HTP-1 feature roadmap.
2. **Generic performance/hardening investigations:** treat these as separately scoped tasks unless the user explicitly maps an item into one of the phases above.
3. **Couch device / separate Couch-related context:** not the Unfolded Circle integration platform and not the HTP-1. The Couch device at `10.0.0.25` is only the remote test client in the topology above. Keep any separate Couch project or operating-environment details out of HTP-1 implementation assumptions unless the user explicitly asks to work on them.

## Current status tracking

Update this section as work progresses. Record verified facts only.

| Item | Status |
|---|---|
| Branch strategy | Agreed: `main` mirrors upstream; `tests-and-docs` holds QA/docs; `feature/*` holds production development. |
| Phase 0 | **Complete.** Configurable port setup and connection paths implemented; legacy config/backup defaults to port 80; backup preserves per-entry ports. Remote sensors confirmed working through Synology Caddy at `10.0.0.56:18082`; user inspected backup and confirmed local port `80` and proxy port `18082`. Original DSM hostname route at `htp1-remote:18081` remains fallback. See `docs/phase-0-validation.md`. |
| Phases 1–6 | Approved scope; implementation status must be verified against current commits, PRs, tests, and hardware checks before being marked complete. |
| Handoff location | `docs/PROJECT_HANDOFF.md` on `tests-and-docs` only. |

**When updating status:** include the relevant branch, commit SHA, PR link (if applicable), CI run/result, and whether real HTP-1 hardware was tested. Do not mark a phase complete based only on an implementation commit.
