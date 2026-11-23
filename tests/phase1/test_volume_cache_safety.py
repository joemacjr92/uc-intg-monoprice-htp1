"""Volume cache freshness and untagged WebSocket event regression tests.

These tests run against the production implementation checked out by the
Phase 1 workflow. They deliberately model receiver state separately from the
integration cache so an external change can occur without its msoupdate being
delivered.

The gap sweep is a safety baseline for the current pre-write getmso behavior.
It does not select a future cache-age threshold. A later optimization may
replace the unconditional refresh with an invalidity/age policy, but it must
preserve the lost-update protection demonstrated here.
"""

import asyncio
import copy
import json
from pathlib import Path

import pytest

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device, apply_json_patch
import intg_monoprice_htp1.device as device_module


FULL_FIXTURE = Path(__file__).parents[1] / "fixtures" / "htp1_full_mso.json"


class FakeClock:
    """Deterministic monotonic clock for cache-age boundary tests."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def record_volume_observation_if_supported(device):
    """Seed freshness metadata when testing the implementation that has it."""
    recorder = getattr(device, "_record_volume_state_observation", None)
    if recorder is not None:
        recorder()


class VolumeReceiver:
    """Receiver double with independent authoritative and integration state."""

    def __init__(
        self,
        device,
        state,
        *,
        reply_to_getmso=True,
        change_event_mode="apply",
    ):
        self.device = device
        self.state = copy.deepcopy(state)
        self.reply_to_getmso = reply_to_getmso
        self.change_event_mode = change_event_mode
        self.messages = []
        self.writes = []

    async def send(self, message):
        self.messages.append(message)

        if message == "getmso":
            if self.reply_to_getmso and self.device.is_connected:
                await self.device.handle_message(f"mso {json.dumps(self.state)}")
            return

        if not message.startswith("changemso "):
            return

        operations = json.loads(message.partition(" ")[2])
        self.writes.append(copy.deepcopy(operations))

        if self.change_event_mode == "apply":
            candidate = copy.deepcopy(self.state)
            for operation in operations:
                apply_json_patch(
                    candidate,
                    operation["op"],
                    operation["path"],
                    operation.get("value"),
                )
            self.state = candidate
            await self.device.handle_message(f"msoupdate {json.dumps(operations)}")
            return

        if self.change_event_mode in {"duplicate_match", "out_of_order", "aba_replay"}:
            volume_operation = next(
                operation for operation in operations
                if operation.get("path") == "/volume"
            )
            requested = volume_operation["value"]
            old_value = self.state["volume"]
            matching = {"op": "replace", "path": "/volume", "value": requested}
            stale = {"op": "replace", "path": "/volume", "value": old_value}

            # These are deliberately uncorrelated, post-send events. The fake
            # receiver's authoritative state does not change, so only the
            # subsequent full mso snapshot can determine the final outcome.
            if self.change_event_mode == "aba_replay":
                # Replay an event that was queued before this write. It is
                # delivered after send and is indistinguishable from a new
                # matching echo because the protocol has no transaction ID.
                queued = getattr(self, "queued_events", [])
                for event in queued:
                    await self.device.handle_message(
                        f"msoupdate {json.dumps([event])}"
                    )
                self.queued_events = []
            else:
                await self.device.handle_message(f"msoupdate {json.dumps([matching])}")
                if self.change_event_mode == "duplicate_match":
                    await self.device.handle_message(f"msoupdate {json.dumps([matching])}")
                elif self.change_event_mode == "out_of_order":
                    await self.device.handle_message(f"msoupdate {json.dumps([stale])}")
            return

        raise AssertionError(f"unknown change_event_mode: {self.change_event_mode}")


def make_volume_device(
    *, receiver_state=None, reply_to_getmso=True, change_event_mode="apply", clock=None
):
    device = HTP1Device(
        HTP1Config("volume-cache-safety", "Volume Cache Safety HTP-1", "127.0.0.1"),
        loop=asyncio.get_running_loop(),
    )
    cached = json.loads(FULL_FIXTURE.read_text(encoding="utf-8"))
    cached["volume"] = -20
    cached["cal"]["vpl"] = -80
    cached["cal"]["vph"] = 12
    cached["cal"]["zeroPoint"] = 0
    device._state = copy.deepcopy(cached)
    device._is_connected = True
    if clock is not None:
        device._clock = clock
    device._parse_state()
    record_volume_observation_if_supported(device)
    receiver = VolumeReceiver(
        device,
        receiver_state if receiver_state is not None else cached,
        reply_to_getmso=reply_to_getmso,
        change_event_mode=change_event_mode,
    )
    device._ws = receiver
    return device, receiver


def written_volume_targets(receiver):
    return [
        operation["value"]
        for write in receiver.writes
        for operation in write
        if operation.get("path") == "/volume"
    ]


@pytest.mark.parametrize("gap_seconds", [0.5, 2, 5, 10])
def test_lost_external_volume_update_is_reconciled_after_freshness_gap(gap_seconds):
    """A silent update at or beyond the cache-age bound must be refreshed."""
    async def exercise():
        clock = FakeClock()
        device, receiver = make_volume_device(clock=clock)
        # The receiver changes independently; no msoupdate reaches the client.
        receiver.state["volume"] = -10
        clock.advance(gap_seconds)

        result = await device.volume_up()

        assert result is True
        assert written_volume_targets(receiver) == [-9]
        assert device._state["volume"] == -9
        # A stale dependency forces a pre-write snapshot, so the write is based
        # on the receiver's -10 dB value rather than the cached -20 dB value.
        assert receiver.messages[0] == "getmso"
        assert receiver.messages.index("getmso") < next(
            index for index, message in enumerate(receiver.messages)
            if message.startswith("changemso ")
        )

    asyncio.run(exercise())


def test_delivered_external_volume_update_is_applied_to_cached_state():
    async def exercise():
        clock = FakeClock()
        device, receiver = make_volume_device(clock=clock)
        receiver.state["volume"] = -10

        await device.handle_message(
            'msoupdate [{"op":"replace","path":"/volume","value":-10}]'
        )

        assert device._state["volume"] == -10
        assert device.volume_db == -10

        result = await device.volume_up()

        assert result is True
        assert written_volume_targets(receiver) == [-9]
        assert receiver.state["volume"] == -9
        # The delivered update made the relevant cache entry fresh, so the
        # command starts with changemso and does not issue a pre-write getmso.
        assert receiver.messages[0].startswith("changemso ")

    asyncio.run(exercise())


def test_disconnect_invalidates_state_and_prevents_relative_volume_write():
    async def exercise():
        device, receiver = make_volume_device()

        device._on_connection_lost()

        assert device._state is None
        assert device._volume_state_timestamps == {}
        assert await device.volume_up() is False
        assert receiver.writes == []
        assert not any(message.startswith("changemso ") for message in receiver.messages)

    asyncio.run(exercise())


def test_malformed_patch_without_recovery_snapshot_prevents_relative_volume_write(monkeypatch):
    async def exercise():
        monkeypatch.setattr(device_module, "STATE_REFRESH_TIMEOUT", 0.01)
        device, receiver = make_volume_device(reply_to_getmso=False)

        await device.handle_message(
            'msoupdate [{"op":"replace","path":"/not-present/child","value":1}]'
        )

        # The malformed patch is rejected and a recovery snapshot is requested.
        assert receiver.messages == ["getmso"]
        assert device._state is None
        assert device._volume_state_timestamps == {}

        # A subsequent relative command must not proceed on the old cache when
        # the required fresh snapshot is unavailable.
        result = await device.volume_up()

        assert result is False
        assert receiver.writes == []
        assert receiver.messages.count("getmso") >= 2

    asyncio.run(exercise())


@pytest.mark.parametrize("event_mode", ["duplicate_match", "out_of_order", "aba_replay"])
def test_untagged_duplicate_or_out_of_order_volume_patch_is_not_final_confirmation(event_mode):
    """A matching live patch is only provisional; full mso readback is decisive."""
    async def exercise():
        device, receiver = make_volume_device(change_event_mode=event_mode)
        if event_mode == "aba_replay":
            # The same target value existed before the transaction and then
            # disappeared. A delayed replay of that old value is an ABA event:
            # it looks like a match but has no transaction identity.
            await device.handle_message('msoupdate [{"op":"replace","path":"/volume","value":-19}]')
            await device.handle_message('msoupdate [{"op":"replace","path":"/volume","value":-20}]')
            receiver.queued_events = [
                {"op": "replace", "path": "/volume", "value": -19}
            ]
        device._write_convergence_timeout = 0.0

        result = await device._execute_transaction_locked(
            [{"op": "replace", "path": "/volume", "value": -19}]
        )

        # The fake emits one or more post-send patches that appear to match,
        # but its authoritative receiver state remains -20. The final mso
        # readback must reject the transaction rather than trust the event.
        assert result is False
        assert written_volume_targets(receiver) == [-19]
        assert receiver.state["volume"] == -20
        assert device._state["volume"] == -20
        assert receiver.messages[-1] == "getmso"

    asyncio.run(exercise())



def test_delivered_calibration_update_refreshes_relative_volume_dependencies():
    async def exercise():
        device, receiver = make_volume_device()
        receiver.state["volume"] = -20
        receiver.state["cal"]["vph"] = -20
        receiver.state["cal"]["vpl"] = -30
        receiver.state["cal"]["zeroPoint"] = 2

        await device.handle_message(
            'msoupdate [{"op":"replace","path":"/cal/vph","value":-20},'
            '{"op":"replace","path":"/cal/vpl","value":-30},'
            '{"op":"replace","path":"/cal/zeroPoint","value":2}]'
        )

        assert device.vph == -20
        assert device.vpl == -30
        assert device.zp == 2
        # At the updated upper bound, volume_up must be a no-op.
        assert await device.volume_up() is True
        assert written_volume_targets(receiver) == []

        # The lower-bound calculation must use the updated zero point.
        receiver.state["volume"] = -28
        await device.handle_message(
            'msoupdate [{"op":"replace","path":"/volume","value":-28}]'
        )
        assert await device.volume_down() is True
        assert written_volume_targets(receiver) == [-29]

    asyncio.run(exercise())


def test_malformed_json_msoupdate_invalidates_cache_and_requests_snapshot(monkeypatch):
    monkeypatch.setattr(device_module, "STATE_REFRESH_TIMEOUT", 0.01)

    async def exercise():
        device, receiver = make_volume_device(reply_to_getmso=False)

        await device.handle_message('msoupdate [{"op":"replace","path":"/volume"')

        assert receiver.messages == ["getmso"]
        assert device._state is None

        # A partial patch cannot restore a discarded full-state baseline.
        await device.handle_message(
            'msoupdate [{"op":"replace","path":"/volume","value":-19}]'
        )
        assert device._state is None
        assert await device.volume_up() is False
        assert receiver.writes == []
        assert receiver.messages.count("getmso") >= 2

    asyncio.run(exercise())


def test_malformed_json_msoupdate_recovers_only_from_a_full_snapshot():
    async def exercise():
        device, receiver = make_volume_device()

        await device.handle_message('msoupdate [{"op":"replace","path":"/volume"')

        # The fake receiver answers the recovery getmso with a complete mso.
        assert device._state == receiver.state
        assert await device.volume_up() is True
        assert written_volume_targets(receiver) == [-19]

    asyncio.run(exercise())


def test_incomplete_full_snapshot_fails_closed_for_relative_volume():
    async def exercise():
        receiver_state = json.loads(FULL_FIXTURE.read_text(encoding="utf-8"))
        receiver_state["volume"] = -20
        receiver_state.pop("cal", None)
        device, receiver = make_volume_device(receiver_state=receiver_state)
        device._state = copy.deepcopy(receiver_state)
        device._parse_state()
        record_volume_observation_if_supported(device)

        assert await device.volume_up() is False
        assert receiver.writes == []

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("volume", True),
        ("volume", -20.5),
        ("vpl", None),
        ("vph", float("nan")),
        ("zeroPoint", float("inf")),
        ("zeroPoint", "0"),
    ],
)
def test_invalid_relative_volume_inputs_fail_closed(field, value):
    async def exercise():
        receiver_state = json.loads(FULL_FIXTURE.read_text(encoding="utf-8"))
        receiver_state["volume"] = -20
        if field == "volume":
            receiver_state["volume"] = value
        else:
            receiver_state["cal"][field] = value
        device, receiver = make_volume_device(receiver_state=receiver_state)
        device._state = copy.deepcopy(receiver_state)
        device._parse_state()
        record_volume_observation_if_supported(device)

        assert await device.volume_up() is False
        assert await device.volume_down() is False
        assert receiver.writes == []

    asyncio.run(exercise())


def test_inverted_volume_bounds_fail_closed():
    async def exercise():
        receiver_state = json.loads(FULL_FIXTURE.read_text(encoding="utf-8"))
        receiver_state["volume"] = -20
        receiver_state["cal"]["vpl"] = -10
        receiver_state["cal"]["vph"] = -30
        device, receiver = make_volume_device(receiver_state=receiver_state)
        device._state = copy.deepcopy(receiver_state)
        device._parse_state()
        record_volume_observation_if_supported(device)

        assert await device.volume_up() is False
        assert await device.volume_down() is False
        assert receiver.writes == []

    asyncio.run(exercise())


@pytest.mark.parametrize("field", ["volume", "vpl", "vph", "zeroPoint"])
def test_missing_relative_volume_dependency_fails_closed(field):
    async def exercise():
        receiver_state = json.loads(FULL_FIXTURE.read_text(encoding="utf-8"))
        if field == "volume":
            receiver_state.pop("volume", None)
        else:
            receiver_state["cal"].pop(field, None)
        device, receiver = make_volume_device(receiver_state=receiver_state)
        device._state = copy.deepcopy(receiver_state)
        device._parse_state()
        record_volume_observation_if_supported(device)

        assert await device.volume_up() is False
        assert await device.volume_down() is False
        assert receiver.writes == []

    asyncio.run(exercise())


def test_volume_down_reconciles_silent_external_change_after_cache_age():
    async def exercise():
        clock = FakeClock()
        device, receiver = make_volume_device(clock=clock)
        receiver.state["volume"] = -30
        clock.advance(0.5)

        assert await device.volume_down() is True
        assert written_volume_targets(receiver) == [-31]
        assert receiver.messages[0] == "getmso"

    asyncio.run(exercise())


def test_unrelated_patch_does_not_make_volume_dependencies_fresh():
    async def exercise():
        clock = FakeClock()
        device, receiver = make_volume_device(clock=clock)
        receiver.state["volume"] = -10
        receiver.state["powerIsOn"] = True

        clock.advance(0.49)
        await device.handle_message(
            'msoupdate [{"op":"replace","path":"/powerIsOn","value":true}]'
        )
        assert device._volume_state_timestamps == {
            "/volume": 0.0,
            "/cal/vpl": 0.0,
            "/cal/vph": 0.0,
            "/cal/zeroPoint": 0.0,
        }

        clock.advance(0.01)
        assert await device.volume_up() is True
        assert written_volume_targets(receiver) == [-9]
        assert receiver.messages[0] == "getmso"

    asyncio.run(exercise())


def test_freshness_is_checked_after_waiting_for_transaction_lock():
    async def exercise():
        clock = FakeClock()
        device, receiver = make_volume_device(clock=clock)
        receiver.state["volume"] = -10

        await device._transaction_lock.acquire()
        try:
            pending = asyncio.create_task(device.volume_up())
            await asyncio.sleep(0)
            clock.advance(0.5)
        finally:
            device._transaction_lock.release()

        assert await pending is True
        assert written_volume_targets(receiver) == [-9]
        assert receiver.messages[0] == "getmso"

    asyncio.run(exercise())


def test_calibration_parent_patch_refreshes_all_calibration_dependencies():
    async def exercise():
        clock = FakeClock()
        device, _receiver = make_volume_device(clock=clock)
        clock.advance(0.2)
        await device.handle_message(
            'msoupdate [{"op":"replace","path":"/cal","value":'
            + json.dumps(device._state["cal"])
            + "}]"
        )

        assert device._volume_state_timestamps["/volume"] == 0.0
        for path in ("/cal/vpl", "/cal/vph", "/cal/zeroPoint"):
            assert device._volume_state_timestamps[path] == 0.2

    asyncio.run(exercise())

def test_failed_final_snapshot_invalidates_unconfirmed_volume_cache(monkeypatch):
    async def exercise():
        monkeypatch.setattr(device_module, "STATE_REFRESH_TIMEOUT", 0.01)
        clock = FakeClock()
        device, receiver = make_volume_device(
            reply_to_getmso=False,
            clock=clock,
        )
        device._write_convergence_timeout = 0.0

        # The write echo updates the live cache, but the authoritative full
        # snapshot is withheld. The cache must not remain eligible for reuse.
        assert await device.volume_up() is False
        assert written_volume_targets(receiver) == [-19]
        assert device._state is None
        assert device._volume_state_timestamps == {}

        # A subsequent command cannot issue another write using the
        # unconfirmed echo; it must first obtain a complete mso snapshot.
        assert await device.volume_up() is False
        assert written_volume_targets(receiver) == [-19]

    asyncio.run(exercise())

@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("/volume", -21),
        ("/cal/vpl", -79),
        ("/cal/vph", 11),
        ("/cal/zeroPoint", -6),
    ],
)
def test_each_volume_dependency_patch_refreshes_only_its_own_timestamp(path, value):
    async def exercise():
        clock = FakeClock()
        device, _receiver = make_volume_device(clock=clock)
        clock.advance(0.2)

        await device.handle_message(
            "msoupdate "
            + json.dumps([{"op": "replace", "path": path, "value": value}])
        )

        for dependency in device._volume_state_timestamps:
            expected = 0.2 if dependency == path else 0.0
            assert device._volume_state_timestamps[dependency] == expected

    asyncio.run(exercise())


def test_full_snapshot_refreshes_all_volume_dependency_timestamps():
    async def exercise():
        clock = FakeClock()
        device, receiver = make_volume_device(clock=clock)
        receiver.state["volume"] = -15
        clock.advance(0.2)

        await device.handle_message(f"mso {json.dumps(receiver.state)}")

        assert device._state["volume"] == -15
        assert set(device._volume_state_timestamps) == {
            "/volume",
            "/cal/vpl",
            "/cal/vph",
            "/cal/zeroPoint",
        }
        assert set(device._volume_state_timestamps.values()) == {0.2}

    asyncio.run(exercise())

def test_silent_update_just_below_age_limit_documents_bounded_exposure():
    async def exercise():
        clock = FakeClock()
        device, receiver = make_volume_device(clock=clock)
        receiver.state["volume"] = -10
        clock.advance(0.49)

        # With no sequence/gap signal, a silent change younger than the
        # configured age bound is indistinguishable from an unchanged cache.
        # The test records this explicit protocol limitation.
        assert await device.volume_up() is True
        assert written_volume_targets(receiver) == [-19]
        assert receiver.state["volume"] == -19
        assert receiver.messages[0].startswith("changemso ")

    asyncio.run(exercise())

