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
            await self.device.handle_message(f"msoupdate {json.dumps([matching])}")
            if self.change_event_mode == "duplicate_match":
                await self.device.handle_message(f"msoupdate {json.dumps([matching])}")
            elif self.change_event_mode == "out_of_order":
                await self.device.handle_message(f"msoupdate {json.dumps([stale])}")
            return

        raise AssertionError(f"unknown change_event_mode: {self.change_event_mode}")


def make_volume_device(*, receiver_state=None, reply_to_getmso=True, change_event_mode="apply"):
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
    device._parse_state()
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


@pytest.mark.parametrize("gap_seconds", [0.5, 2.0, 5.0, 10.0])
def test_lost_external_volume_update_is_reconciled_before_relative_write(gap_seconds):
    """A silent external change must not be overwritten from the stale cache."""
    async def exercise():
        device, receiver = make_volume_device()
        # The receiver changes independently; no msoupdate reaches the client.
        receiver.state["volume"] = -10

        await asyncio.sleep(gap_seconds)
        result = await device.volume_up()

        assert result is True
        assert written_volume_targets(receiver) == [-9]
        assert device._state["volume"] == -9
        # The first receiver interaction must be the authoritative preflight,
        # before the changemso based on the refreshed -10 dB state.
        assert receiver.messages[0] == "getmso"
        assert receiver.messages.index("getmso") < next(
            index for index, message in enumerate(receiver.messages)
            if message.startswith("changemso ")
        )

    asyncio.run(exercise())


def test_delivered_external_volume_update_is_applied_to_cached_state():
    async def exercise():
        device, receiver = make_volume_device()
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

    asyncio.run(exercise())


def test_disconnect_invalidates_state_and_prevents_relative_volume_write():
    async def exercise():
        device, receiver = make_volume_device()

        device._on_connection_lost()

        assert device._state is None
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
