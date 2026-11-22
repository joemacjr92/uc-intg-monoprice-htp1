# Phase 0 — Configurable Port and Reverse-Proxy QA

## Scope

Verify the configurable HTP-1 connection port and the private reverse-proxy path used by the Unfolded Circle Remote. The implementation is on `feature/configurable-htp1-port`; this branch holds QA material and the test record.

## Automated regression coverage

`tests/phase0/test_configurable_port.py` contains the Phase 0 regression tests. It covers:

- Default port 80 and valid/invalid port bounds.
- Legacy dataclass/config-file data without a port defaulting to 80.
- Configured port in WebSocket URL construction and actual WebSocket connection creation.
- Setup form default and saved-port prefill.
- Setup parsing, probing, update behavior, and invalid-port rejection.
- Configured port in the HTTP IR command URL.
- Backup/restore preserving a configured port.
- Legacy backup restore defaulting to port 80.

The Phase 0 tests were rerun from this QA branch against the actual implementation checkout using the dedicated **Phase 0 and Full QA Tests** workflow. GitHub Actions run **44974796280** completed successfully:

- Existing regression suite on `tests-and-docs`: **92 passed, 1 skipped**.
- Phase 0 regression suite against `feature/configurable-htp1-port`: **33 passed**.
- Combined: **125 passed, 1 skipped**.

The workflow runs the two suites separately so Phase 0 tests import the implementation branch rather than the QA branch's source tree. The two BEQ fixture tests also now supply explicit event loops, avoiding dependence on implicit event-loop creation in Python 3.11. The earlier feature-branch run **44965976353** also passed 33 tests at feature commit `6e2a2ee8a6170b4123b71e033cdfdb53934c6f01`.

## Remote and backup verification

| Check | Result | Evidence |
|---|---|---|
| Synology Caddy route | Pass | User confirmed the HTP-1 interface is reachable through `http://10.0.0.56:18082`. |
| Unfolded Circle Remote connection | Pass | User confirmed the integration connects using host `10.0.0.56`, port `18082`. |
| Sensor operation | Pass | User confirmed the sensors are working on the Remote through this connection. |
| Backup includes local port | Pass | User inspected the backup and confirmed the local entry contains port `80`. |
| Backup includes proxy port | Pass | User inspected the backup and confirmed the proxy entry contains port `18082`. |
| Legacy default | Automated coverage | Regression tests cover legacy configuration and backup records without a port defaulting to `80`. |

The backup inspection confirms serialization of both configured entries. The automated backup/restore test additionally covers restoring a non-default port and restoring legacy data without a port.

## Network routes

Preferred integration route:

```text
Unfolded Circle Remote
  -> Synology Caddy 10.0.0.56:18082
  -> Tailscale
  -> UGREEN Caddy 100.125.151.26:18080
  -> HTP-1 10.0.0.141:80
```

Fallback route: Synology DSM reverse proxy at `htp1-remote:18081`. The existing DSM rule was left in place.

## Completion decision

Phase 0 acceptance is met. The integration uses the configured port for WebSocket and HTTP command paths; regression tests cover those paths and backward compatibility; the Remote is connected through the preferred private proxy; sensors are working; and the backup contains both entries' correct ports.

This does not claim that every possible HTP-1 command has been individually exercised through the proxy. It records the observed Remote sensor operation and the automated HTTP command URL coverage without overstating the hardware test.
