"""Deterministic simulation of a coalescing volume worker.

This is a design-level fake, not production code. It models the proposed
latest-target worker with serialized writes. It compares two candidate write policies: a 5 dB
maximum step (conservative but slow to catch up) and an unbounded latest-target
write (fast but permits a large single jump). The 2.1 s acknowledgement delay is anchored to the observed
15:12:42.632-15:12:45.754 (>2.09 s) HTP-1 full-state response in
dumps/integration.log. It is a stress input, not a claim that every volume
write takes 2.1 s.

The five-second hold uses 10 relative requests per second (50 total), an
explicit stress profile rather than a measured Remote repeat rate.
"""

import asyncio
from dataclasses import dataclass


OBSERVED_SLOW_STATE_RESPONSE_SECONDS = 2.1
HOLD_SECONDS = 5.0
REQUESTS_PER_SECOND = 10
MAX_WRITE_STEP_DB = 5
VOLUME_MIN_DB = -80
VOLUME_MAX_DB = 12


@dataclass
class PendingWrite:
    sequence: int
    target: int
    completion: asyncio.Future


class ControlledReceiver:
    """Fake receiver whose writes complete only when the test acknowledges them."""

    def __init__(self, initial_volume: int):
        self.actual_volume = initial_volume
        self.pending: list[PendingWrite] = []
        self.max_in_flight = 0
        self.write_history: list[tuple[int, int]] = []

    async def write_volume(self, target: int, sequence: int) -> int:
        future = asyncio.get_running_loop().create_future()
        self.pending.append(PendingWrite(sequence, target, future))
        self.write_history.append((sequence, target))
        self.max_in_flight = max(self.max_in_flight, len(self.pending))
        try:
            return await future
        finally:
            self.pending = [item for item in self.pending if item.completion is not future]

    def acknowledge_next(self) -> PendingWrite:
        assert self.pending, "worker has no outstanding write"
        pending = self.pending[0]
        self.actual_volume = pending.target
        pending.completion.set_result(self.actual_volume)
        return pending

    def fail_next(self) -> PendingWrite:
        assert self.pending, "worker has no outstanding write"
        pending = self.pending[0]
        pending.completion.set_exception(ConnectionError("simulated receiver write failure"))
        return pending


class CoalescingVolumeWorkerModel:
    """Small executable model of the proposed single-worker architecture."""

    def __init__(
        self,
        receiver: ControlledReceiver,
        initial_volume: int,
        *,
        minimum: int = VOLUME_MIN_DB,
        maximum: int = VOLUME_MAX_DB,
        max_write_step: int | None = MAX_WRITE_STEP_DB,
    ):
        self.receiver = receiver
        self.confirmed_volume = initial_volume
        self.requested_target = initial_volume
        self.minimum = minimum
        self.maximum = maximum
        self.max_write_step = max_write_step
        self._sequence = 0
        self._last_confirmed_sequence = 0
        self._worker_task: asyncio.Task | None = None
        self.connected = True
        self.corrections: list[int] = []
        self.failures = 0

    def request_step(self, delta: int) -> bool:
        """Record a relative request without awaiting receiver I/O."""
        if not self.connected or delta not in (-1, 1):
            return False
        self.requested_target = max(
            self.minimum, min(self.maximum, self.requested_target + delta)
        )
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._run_worker())
        return True

    async def _run_worker(self) -> None:
        while self.connected and self.confirmed_volume != self.requested_target:
            difference = self.requested_target - self.confirmed_volume
            step = (
                difference
                if self.max_write_step is None
                else max(-self.max_write_step, min(self.max_write_step, difference))
            )
            target = self.confirmed_volume + step
            self._sequence += 1
            sequence = self._sequence
            try:
                actual = await self.receiver.write_volume(target, sequence)
            except (ConnectionError, asyncio.CancelledError):
                if not self.connected:
                    return
                self.failures += 1
                self.requested_target = self.receiver.actual_volume
                self.confirmed_volume = self.receiver.actual_volume
                self.corrections.append(self.confirmed_volume)
                return
            if sequence >= self._last_confirmed_sequence:
                self._last_confirmed_sequence = sequence
                self.confirmed_volume = actual

    def receive_state_event(self, volume: int, sequence: int) -> None:
        """Ignore stale receiver events and never replace newer user intent."""
        if sequence < self._last_confirmed_sequence:
            return
        self._last_confirmed_sequence = sequence
        self.confirmed_volume = volume
        # Deliberately do not assign requested_target from a state event.

    async def wait_for_worker_to_start(self) -> None:
        await asyncio.sleep(0)

    async def finish_all_writes(self) -> None:
        """Acknowledge serialized writes until the latest target is reached."""
        while self.confirmed_volume != self.requested_target:
            await self.wait_for_worker_to_start()
            assert len(self.receiver.pending) == 1
            self.receiver.acknowledge_next()
            await self.wait_for_worker_to_start()
        if self._worker_task is not None:
            await self._worker_task

    async def disconnect(self) -> None:
        self.connected = False
        if self._worker_task is not None and not self._worker_task.done():
            self._worker_task.cancel()
            await asyncio.gather(self._worker_task, return_exceptions=True)
        self.requested_target = self.confirmed_volume


def test_five_second_hold_coalesces_intent_and_serializes_slow_writes():
    async def exercise():
        initial = -40
        receiver = ControlledReceiver(initial)
        worker = CoalescingVolumeWorkerModel(receiver, initial)

        # A five-second hold at 10 requests/second: 50 logical +1 dB requests.
        # Advance a virtual timeline and acknowledge writes at 2.1 s and 4.2 s.
        request_times = [index / REQUESTS_PER_SECOND for index in range(50)]
        assert request_times[-1] < HOLD_SECONDS
        completed_during_hold = 0
        for index, _timestamp in enumerate(request_times):
            assert worker.request_step(+1)
            await worker.wait_for_worker_to_start()
            if index in (20, 41):
                receiver.acknowledge_next()
                completed_during_hold += 1
                await worker.wait_for_worker_to_start()

        assert worker.requested_target == 10
        assert completed_during_hold == 2
        assert worker.confirmed_volume == -30
        assert len(receiver.pending) == 1
        assert receiver.pending[0].target == -25

        # The third write began at 4.2 s; at release (5.0 s), 1.3 s of its
        # 2.1 s acknowledgement remains, followed by seven more round trips.
        await worker.finish_all_writes()

        assert worker.confirmed_volume == 10
        assert receiver.actual_volume == 10
        assert receiver.max_in_flight == 1
        assert len(receiver.write_history) == 10
        assert all(
            abs(target - (initial if index == 0 else receiver.write_history[index - 1][1])) <= MAX_WRITE_STEP_DB
            for index, (_sequence, target) in enumerate(receiver.write_history)
        )

        simulated_total_ack_time = len(receiver.write_history) * OBSERVED_SLOW_STATE_RESPONSE_SECONDS
        simulated_after_release = (
            (len(receiver.write_history) - completed_during_hold) * OBSERVED_SLOW_STATE_RESPONSE_SECONDS
            - (HOLD_SECONDS - 2 * OBSERVED_SLOW_STATE_RESPONSE_SECONDS)
        )
        assert simulated_total_ack_time == 21.0
        assert simulated_after_release == 16.0
        # Under this bounded-write policy and observed slow-response stress
        # input, the final target does NOT settle within one RTT after release.

    asyncio.run(exercise())


def test_unbounded_latest_target_policy_catches_up_after_release_in_about_two_rtts():
    async def exercise():
        initial = -40
        receiver = ControlledReceiver(initial)
        worker = CoalescingVolumeWorkerModel(
            receiver, initial, max_write_step=None
        )

        # Same five-second / 50-step hold. The worker starts at t=0, then
        # completes writes at t=2.1 and t=4.2 while requests keep arriving.
        for index in range(50):
            assert worker.request_step(+1)
            await worker.wait_for_worker_to_start()
            if index in (20, 41):
                receiver.acknowledge_next()
                await worker.wait_for_worker_to_start()

        assert worker.requested_target == 10
        assert worker.confirmed_volume == -19
        assert len(receiver.pending) == 1
        assert receiver.pending[0].target == 2

        # The in-flight write has 1.3 s remaining at release. It confirms at
        # 6.3 s, then the final latest-target write confirms at 8.4 s.
        receiver.acknowledge_next()
        await worker.wait_for_worker_to_start()
        assert worker.confirmed_volume == 2
        assert receiver.pending[0].target == 10
        receiver.acknowledge_next()
        await worker.wait_for_worker_to_start()
        await worker._worker_task

        assert worker.confirmed_volume == 10
        assert receiver.actual_volume == 10
        assert len(receiver.write_history) == 4
        assert receiver.max_in_flight == 1
        simulated_after_release = (
            OBSERVED_SLOW_STATE_RESPONSE_SECONDS
            - (HOLD_SECONDS - 2 * OBSERVED_SLOW_STATE_RESPONSE_SECONDS)
            + OBSERVED_SLOW_STATE_RESPONSE_SECONDS
        )
        assert simulated_after_release == 3.4
        # This policy approaches the proposed latency, but it does so by
        # allowing large writes (the final one is +8 dB, earlier ones larger).

    asyncio.run(exercise())


def test_stale_state_event_cannot_erase_newer_requested_target():
    async def exercise():
        receiver = ControlledReceiver(-40)
        worker = CoalescingVolumeWorkerModel(receiver, -40)

        for _ in range(10):
            assert worker.request_step(+1)
        await worker.wait_for_worker_to_start()
        assert receiver.pending[0].target == -35

        receiver.acknowledge_next()
        await worker.wait_for_worker_to_start()
        assert worker.confirmed_volume == -35
        assert receiver.pending[0].target == -30

        for _ in range(10):
            assert worker.request_step(+1)
        assert worker.requested_target == -20

        # A delayed event from the first write arrives after the second write
        # has already been sent. It may not roll back the logical target.
        worker.receive_state_event(-35, sequence=1)
        assert worker.requested_target == -20

        receiver.acknowledge_next()
        await worker.wait_for_worker_to_start()
        assert worker.confirmed_volume == -30
        assert worker.requested_target == -20
        await worker.finish_all_writes()
        assert worker.confirmed_volume == -20

    asyncio.run(exercise())


def test_out_of_order_older_confirmation_is_ignored():
    receiver = ControlledReceiver(-30)
    worker = CoalescingVolumeWorkerModel(receiver, -30)
    worker._last_confirmed_sequence = 2
    worker.confirmed_volume = -28
    worker.requested_target = -25

    worker.receive_state_event(-29, sequence=1)

    assert worker.confirmed_volume == -28
    assert worker.requested_target == -25


def test_write_failure_reconciles_to_actual_state_without_automatic_retry():
    async def exercise():
        receiver = ControlledReceiver(-30)
        worker = CoalescingVolumeWorkerModel(receiver, -30)
        assert worker.request_step(+1)
        await worker.wait_for_worker_to_start()
        assert len(receiver.pending) == 1

        receiver.fail_next()
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert worker.failures == 1
        assert worker.confirmed_volume == -30
        assert worker.requested_target == -30
        assert worker.corrections == [-30]
        assert receiver.write_history == [(1, -29)]
        assert receiver.pending == []

    asyncio.run(exercise())


def test_requested_target_obeys_receiver_volume_bounds():
    async def exercise():
        receiver = ControlledReceiver(11)
        worker = CoalescingVolumeWorkerModel(receiver, 11, maximum=12)

        for _ in range(20):
            assert worker.request_step(+1)
        await worker.wait_for_worker_to_start()

        assert worker.requested_target == 12
        assert len(receiver.pending) == 1
        assert receiver.pending[0].target == 12
        receiver.acknowledge_next()
        await worker.wait_for_worker_to_start()
        assert worker.confirmed_volume == 12

    asyncio.run(exercise())


def test_disconnect_cancels_worker_and_discards_unconfirmed_intent():
    async def exercise():
        receiver = ControlledReceiver(-30)
        worker = CoalescingVolumeWorkerModel(receiver, -30)
        assert worker.request_step(+1)
        await worker.wait_for_worker_to_start()
        assert len(receiver.pending) == 1

        await worker.disconnect()

        assert not worker.connected
        assert worker.requested_target == -30
        assert not worker.request_step(+1)
        assert worker._worker_task.cancelled() or worker._worker_task.done()

    asyncio.run(exercise())
