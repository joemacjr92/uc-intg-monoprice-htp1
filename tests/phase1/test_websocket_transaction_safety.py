"""Failure-injection tests for HTP-1 state-changing WebSocket transactions.

The receiver protocol has no documented changemso acknowledgement. These tests
model the established request/write/getmso/readback sequence and verify that a
successful socket write alone is never treated as proof of an applied change.
"""

import asyncio
import copy
import json
from pathlib import Path

import pytest

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device, apply_json_patch


FULL_FIXTURE = Path(__file__).parents[1] / "fixtures" / "htp1_full_mso.json"
BEQ_FIXTURE = Path(__file__).parents[1] / "fixtures" / "mso_beq_pre_active.json"
BEQ_FILTERS = [
    {"type": "PeakingEQ", "freq": 25, "gain": 3.5, "q": 1.2},
    {"type": "LowShelf", "freq": 30, "gain": -2.0, "q": 0.8},
]


class FakeReceiver:
    """Small deterministic receiver that can apply, ignore, or partly apply writes."""

    def __init__(
        self,
        device,
        state,
        *,
        apply_mode="all",
        reply_to_getmso=True,
        disconnect_after_change=False,
        first_change_gate=None,
    ):
        self.device = device
        self.state = copy.deepcopy(state)
        self.apply_mode = apply_mode
        self.reply_to_getmso = reply_to_getmso
        self.disconnect_after_change = disconnect_after_change
        self.first_change_gate = first_change_gate
        self.first_change_started = asyncio.Event()
        self.messages = []
        self.change_count = 0

    async def send(self, message):
        self.messages.append(message)
        if message == "getmso":
            if self.reply_to_getmso and self.device.is_connected:
                await self.device.handle_message(f"mso {json.dumps(self.state)}")
            return

        if not message.startswith("changemso "):
            return

        self.change_count += 1
        operations = json.loads(message.partition(" ")[2])
        if self.change_count == 1:
            self.first_change_started.set()
            if self.first_change_gate is not None:
                await self.first_change_gate.wait()

        if self.apply_mode == "all":
            applied = operations
        elif self.apply_mode == "partial":
            applied = operations[: max(1, len(operations) // 2)]
        elif self.apply_mode == "ignore":
            applied = []
        else:
            raise AssertionError(f"unknown fake receiver apply mode: {self.apply_mode}")

        if applied:
            candidate = copy.deepcopy(self.state)
            for operation in applied:
                apply_json_patch(
                    candidate,
                    operation["op"],
                    operation["path"],
                    operation.get("value"),
                )
            self.state = candidate
            await self.device.handle_message(f"msoupdate {json.dumps(applied)}")

        if self.disconnect_after_change:
            self.device._on_connection_lost()


def _make_device(fixture=BEQ_FIXTURE, receiver_state=None, **receiver_options):
    device = HTP1Device(
        HTP1Config("transaction-safety", "Transaction Safety HTP-1", "127.0.0.1"),
        loop=asyncio.get_running_loop(),
    )
    cached_state = json.loads(fixture.read_text(encoding="utf-8"))
    device._state = cached_state
    device._is_connected = True
    device._parse_state()
    receiver = FakeReceiver(
        device,
        receiver_state if receiver_state is not None else cached_state,
        **receiver_options,
    )
    device._ws = receiver
    return device, receiver


def test_beq_refreshes_state_before_preflight_and_rejects_stale_pre_cache():
    async def exercise():
        cached = json.loads(BEQ_FIXTURE.read_text(encoding="utf-8"))
        actual = copy.deepcopy(cached)
        actual["peq"]["location"] = "post"
        device, receiver = _make_device(receiver_state=actual)

        result = await device.load_beq("Stale PEQ state", BEQ_FILTERS)

        assert result is False
        assert receiver.messages == ["getmso"]
        assert receiver.change_count == 0
        assert device._state["peq"]["location"] == "post"

    asyncio.run(exercise())


def test_beq_receiver_ignoring_patch_is_reported_as_failure_after_readback():
    async def exercise():
        state = json.loads(BEQ_FIXTURE.read_text(encoding="utf-8"))
        original_active = state["peq"]["beqActive"]
        device, receiver = _make_device(
            receiver_state=state,
            apply_mode="ignore",
        )

        result = await device.load_beq("Rejected BEQ", BEQ_FILTERS)

        assert result is False
        assert receiver.change_count == 1
        assert receiver.messages.count("getmso") >= 2
        assert device.beq_active == original_active
        assert device._state["peq"]["beqActive"] == original_active

    asyncio.run(exercise())


def test_partial_beq_application_is_not_reported_as_success():
    async def exercise():
        state = json.loads(BEQ_FIXTURE.read_text(encoding="utf-8"))
        original_active = state["peq"]["beqActive"]
        device, receiver = _make_device(
            receiver_state=state,
            apply_mode="partial",
        )

        result = await device.load_beq("Partially applied BEQ", BEQ_FILTERS)

        assert result is False
        assert receiver.change_count == 1
        assert receiver.messages.count("getmso") >= 2
        assert device.beq_active == original_active
        assert receiver.state != state

    asyncio.run(exercise())


def test_beq_state_refresh_timeout_aborts_before_any_write(monkeypatch):
    original_wait_for = asyncio.wait_for

    async def shorten_refresh_wait(awaitable, timeout=None):
        # Only shorten the production state-refresh wait, not the outer guard.
        if timeout == 5.0:
            timeout = 0.05
        return await original_wait_for(awaitable, timeout=timeout)

    monkeypatch.setattr(asyncio, "wait_for", shorten_refresh_wait)

    async def exercise():
        state = json.loads(BEQ_FIXTURE.read_text(encoding="utf-8"))
        device, receiver = _make_device(
            receiver_state=state,
            reply_to_getmso=False,
        )

        result = await asyncio.wait_for(
            device.load_beq("Timed out preflight", BEQ_FILTERS),
            timeout=1.0,
        )

        assert result is False
        assert receiver.messages == ["getmso"]
        assert receiver.change_count == 0

    asyncio.run(exercise())


def test_disconnect_after_beq_write_does_not_claim_success_or_replay():
    async def exercise():
        state = json.loads(BEQ_FIXTURE.read_text(encoding="utf-8"))
        device, receiver = _make_device(
            receiver_state=state,
            disconnect_after_change=True,
        )

        result = await device.load_beq("Disconnected BEQ", BEQ_FILTERS)

        assert result is False
        assert receiver.change_count == 1
        assert sum(message.startswith("changemso ") for message in receiver.messages) == 1
        # The receiver echoed the complete patch before the socket dropped.
        # The command still returns failure because readback could not complete;
        # retain the last state actually reported by the receiver.
        assert device.beq_active == "Disconnected BEQ"

    asyncio.run(exercise())


def test_concurrent_relative_volume_updates_use_fresh_serialized_state():
    async def exercise():
        state = json.loads(FULL_FIXTURE.read_text(encoding="utf-8"))
        state["volume"] = -20
        state["cal"]["vpl"] = -80
        state["cal"]["vph"] = 12
        state["cal"]["zeroPoint"] = 0
        first_change_gate = asyncio.Event()
        device, receiver = _make_device(
            fixture=FULL_FIXTURE,
            receiver_state=state,
            first_change_gate=first_change_gate,
        )
        device._state["volume"] = -20
        device.vpl = -80
        device.vph = 12
        device.zp = 0

        first = asyncio.create_task(device.volume_up())
        await asyncio.wait_for(receiver.first_change_started.wait(), timeout=1)
        second = asyncio.create_task(device.volume_up())
        await asyncio.sleep(0)
        first_change_gate.set()

        results = await asyncio.gather(first, second)

        assert results == [True, True]
        assert receiver.state["volume"] == -18
        assert device._state["volume"] == -18
        changes = [
            json.loads(message.partition(" ")[2])
            for message in receiver.messages
            if message.startswith("changemso ")
        ]
        assert [change[0]["value"] for change in changes] == [-19, -18]

    asyncio.run(exercise())

def test_source_selection_uses_fresh_visibility_not_stale_cached_inputs():
    async def exercise():
        cached = json.loads(FULL_FIXTURE.read_text(encoding="utf-8"))
        actual = copy.deepcopy(cached)
        actual["inputs"]["h1"]["visible"] = False
        device, receiver = _make_device(
            fixture=FULL_FIXTURE,
            receiver_state=actual,
        )

        result = await device.select_source("Movies")

        assert result is False
        assert receiver.change_count == 0
        assert receiver.state["input"] == cached["input"]

    asyncio.run(exercise())


def test_seat_shaker_preset_selection_requires_fresh_shaker_state():
    async def exercise():
        cached = json.loads(FULL_FIXTURE.read_text(encoding="utf-8"))
        actual = copy.deepcopy(cached)
        actual.pop("shaker")
        device, receiver = _make_device(
            fixture=FULL_FIXTURE,
            receiver_state=actual,
        )

        result = await device.select_ss_preset(1)

        assert result is False
        assert receiver.change_count == 0
        assert "shaker" not in receiver.state

    asyncio.run(exercise())


def test_calibration_selection_uses_fresh_slot_index():
    async def exercise():
        cached = json.loads(FULL_FIXTURE.read_text(encoding="utf-8"))
        actual = copy.deepcopy(cached)
        actual["cal"]["slots"][0], actual["cal"]["slots"][1] = (
            actual["cal"]["slots"][1],
            actual["cal"]["slots"][0],
        )
        device, receiver = _make_device(
            fixture=FULL_FIXTURE,
            receiver_state=actual,
        )

        result = await device.select_calibration("6 Point Tweaked")

        assert result is True
        assert receiver.change_count == 1
        assert receiver.state["cal"]["currentdiracslot"] == 1

    asyncio.run(exercise())

def test_absolute_volume_uses_fresh_receiver_calibration_bounds():
    async def exercise():
        cached = json.loads(FULL_FIXTURE.read_text(encoding="utf-8"))
        cached["cal"]["vpl"] = -80
        cached["cal"]["vph"] = 12
        actual = copy.deepcopy(cached)
        actual["cal"]["vpl"] = -40
        actual["cal"]["vph"] = -10
        device, receiver = _make_device(
            fixture=FULL_FIXTURE,
            receiver_state=actual,
        )

        result = await device.set_volume(0)

        assert result is False
        assert receiver.change_count == 0
        assert receiver.state["volume"] == cached["volume"]

    asyncio.run(exercise())

def test_connection_loss_wakes_state_refresh_waiters():
    async def exercise():
        device, _ = _make_device()
        device._state_ready.clear()

        device._on_connection_lost()

        assert device._state is None
        assert device._state_ready.is_set()

    asyncio.run(exercise())
