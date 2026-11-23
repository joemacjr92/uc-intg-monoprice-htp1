"""Fast-response simulation of the proposed coalescing volume worker.

Design-level model only; it is not production code or hardware validation.

The model assumes:
- a five-second hold at 10 one-dB requests/second (50 requests);
- a 5 dB maximum change per device write;
- one serialized write in flight;
- each write completes when a matching post-send /volume msoupdate arrives;
- normal per-write response latency is swept at 0.3, 0.4, and 0.5 seconds,
  based on the earlier capture-derived estimate discussed during design review;
- no pre-write getmso refresh and no full getmso after each write;
- one authoritative full snapshot after the worker becomes idle, with the
  same 0.3-0.5 second latency assumption.

The msoupdate is modeled as a matching completion event for timing purposes.
This does not solve the protocol's untagged-event ABA ambiguity; that remains
a separate completion-correlation design risk.
"""

from dataclasses import dataclass

HOLD_SECONDS = 5.0
REQUESTS_PER_SECOND = 10
REQUEST_COUNT = int(HOLD_SECONDS * REQUESTS_PER_SECOND)
MAX_WRITE_STEP_DB = 5
INITIAL_VOLUME_DB = -40
NORMAL_RESPONSE_SECONDS = (0.3, 0.4, 0.5)


@dataclass(frozen=True)
class Write:
    sent_at: float
    target: int
    completed_at: float


@dataclass(frozen=True)
class SimulationResult:
    response_seconds: float
    requested_target: int
    confirmed_volume: int
    writes: tuple[Write, ...]
    max_in_flight: int
    final_write_completion: float
    snapshot_completion: float
    snapshot_count: int

    @property
    def settle_after_release(self) -> float:
        return self.snapshot_completion - HOLD_SECONDS


def simulate_five_second_hold(response_seconds: float) -> SimulationResult:
    """Run a deterministic event-time simulation with no wall-clock sleeps."""
    request_times = tuple(
        index / REQUESTS_PER_SECOND for index in range(REQUEST_COUNT)
    )
    target = INITIAL_VOLUME_DB
    confirmed = INITIAL_VOLUME_DB
    request_index = 0
    now = 0.0
    in_flight: tuple[float, int, float] | None = None
    writes: list[Write] = []
    max_in_flight = 0

    def start_write(sent_at: float) -> tuple[float, int, float]:
        nonlocal max_in_flight
        difference = target - confirmed
        bounded_difference = max(
            -MAX_WRITE_STEP_DB, min(MAX_WRITE_STEP_DB, difference)
        )
        write_target = confirmed + bounded_difference
        completion_time = sent_at + response_seconds
        writes.append(Write(sent_at, write_target, completion_time))
        max_in_flight = max(max_in_flight, 1)
        return completion_time, write_target, sent_at

    while request_index < REQUEST_COUNT or in_flight is not None:
        next_request = (
            request_times[request_index]
            if request_index < REQUEST_COUNT
            else float("inf")
        )
        next_completion = (
            in_flight[0] if in_flight is not None else float("inf")
        )

        # Process a button press before a completion at the same virtual time.
        if next_request <= next_completion:
            now = next_request
            target += 1
            request_index += 1
            if in_flight is None and target != confirmed:
                in_flight = start_write(now)
        else:
            now = next_completion
            assert in_flight is not None
            confirmed = in_flight[1]
            in_flight = None
            if target != confirmed:
                in_flight = start_write(now)

    # Exactly one authoritative getmso is performed after the worker is idle.
    # No pre-write refresh and no per-write full-state verification are modeled.
    final_write_completion = now
    snapshot_completion = final_write_completion + response_seconds

    return SimulationResult(
        response_seconds=response_seconds,
        requested_target=target,
        confirmed_volume=confirmed,
        writes=tuple(writes),
        max_in_flight=max_in_flight,
        final_write_completion=final_write_completion,
        snapshot_completion=snapshot_completion,
        snapshot_count=1,
    )


def test_normal_response_time_sweep_settles_within_about_one_second_after_release():
    expected = {
        0.3: (18, 5.4, 0.7),
        0.4: (14, 5.6, 1.0),
        0.5: (11, 5.5, 1.0),
    }

    for response_seconds, (write_count, final_completion, settle_time) in expected.items():
        result = simulate_five_second_hold(response_seconds)

        assert result.requested_target == 10
        assert result.confirmed_volume == 10
        assert len(result.writes) == write_count
        assert abs(result.final_write_completion - final_completion) < 1e-9
        assert abs(result.settle_after_release - settle_time) < 1e-9


def test_every_write_preserves_five_db_cap_and_single_in_flight_rule():
    for response_seconds in NORMAL_RESPONSE_SECONDS:
        result = simulate_five_second_hold(response_seconds)
        previous = INITIAL_VOLUME_DB

        for write in result.writes:
            assert abs(write.target - previous) <= MAX_WRITE_STEP_DB
            assert abs(
                (write.completed_at - write.sent_at) - response_seconds
            ) < 1e-9
            previous = write.target

        assert result.max_in_flight == 1
        assert result.confirmed_volume == result.requested_target


def test_full_snapshot_occurs_once_after_idle_not_after_each_write():
    for response_seconds in NORMAL_RESPONSE_SECONDS:
        result = simulate_five_second_hold(response_seconds)

        assert result.snapshot_count == 1
        assert abs(
            result.snapshot_completion
            - (result.final_write_completion + response_seconds)
        ) < 1e-9
        assert len(result.writes) > result.snapshot_count


def test_five_second_hold_coalesces_fifty_presses_into_fewer_writes():
    for response_seconds in NORMAL_RESPONSE_SECONDS:
        result = simulate_five_second_hold(response_seconds)

        assert REQUEST_COUNT == 50
        assert len(result.writes) < REQUEST_COUNT
        assert result.requested_target == INITIAL_VOLUME_DB + REQUEST_COUNT
