# Phase 0 — Configurable Port and Reverse-Proxy QA

## Scope

Verify the configurable HTP-1 connection port and remote operation through the user's private reverse-proxy path. Private endpoint and network-topology details are intentionally omitted. The implementation is on `feature/configurable-htp1-port`; this branch holds QA material and the test record.

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
| Private reverse-proxy connectivity | Pass | User confirmed the HTP-1 interface is reachable through the established private proxy path. Endpoint details intentionally omitted. |
| Unfolded Circle Remote connection | Pass | User confirmed the integration connects through the established private proxy path using the configured non-default port. |
| Sensor operation | Pass | User confirmed the sensors are working on the Remote through this connection. |
| Backup includes local port | Pass | User inspected the backup and confirmed the local entry contains port `80`. |
| Backup includes non-default port | Pass | User inspected the backup and confirmed the remote entry preserves its configured non-default port. |
| Legacy default | Automated coverage | Regression tests cover legacy configuration and backup records without a port defaulting to `80`. |

The backup inspection confirms serialization of both configured entries. The automated backup/restore test additionally covers restoring a non-default port and restoring legacy data without a port.

## Remote connectivity validation

The integration was tested through the user's established private reverse-proxy path. The Remote connected successfully and sensors operated as expected. Private addresses, hostnames, ports associated with private infrastructure, tunnel technology, proxy topology, and service deployment details are intentionally not recorded here.

## Completion decision

Phase 0 acceptance is met. The integration uses the configured port for WebSocket and HTTP command paths; regression tests cover those paths and backward compatibility; the Remote is connected through the established private proxy; sensors are working; and the backup contains both entries' correct ports.

This does not claim that every possible HTP-1 command has been individually exercised through the proxy. It records the observed Remote sensor operation and the automated HTTP command URL coverage without overstating the hardware test.
