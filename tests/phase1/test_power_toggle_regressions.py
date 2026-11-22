"""Power-toggle regression tests using a simulated HTP-1 receiver."""

import asyncio
import copy
import json
from pathlib import Path

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device, apply_json_patch
from intg_monoprice_htp1 import device as device_module


FIXTURE = Path(__file__).parents[1] / "fixtures" / "htp1_full_mso.json"


class PowerReceiver:
    def __init__(self, device, state, first_change_gate=None, reply=True):
        self.device = device
        self.state = copy.deepcopy(state)
        self.first_change_gate = first_change_gate
        self.first_change_started = asyncio.Event()
        self.reply = reply
        self.messages = []
        self.changes = []

    async def send(self, message):
        self.messages.append(message)
        if message == "getmso":
            if self.reply and self.device.is_connected:
                await self.device.handle_message(f"mso {json.dumps(self.state)}")
            return
        if not message.startswith("changemso "):
            return

        operations = json.loads(message.partition(" ")[2])
        self.changes.append(operations)
        if len(self.changes) == 1:
            self.first_change_started.set()
            if self.first_change_gate is not None:
                await self.first_change_gate.wait()

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


def make_device(cached_state, receiver_state=None, **receiver_options):
    device = HTP1Device(
        HTP1Config("power-toggle", "Power Toggle HTP-1", "127.0.0.1"),
        loop=asyncio.get_running_loop(),
    )
    device._state = copy.deepcopy(cached_state)
    device._is_connected = True
    device._parse_state()
    receiver = PowerReceiver(
        device,
        receiver_state if receiver_state is not None else cached_state,
        **receiver_options,
    )
    device._ws = receiver
    return device, receiver


def test_toggle_uses_fresh_receiver_state_instead_of_cached_power():
    async def exercise():
        cached = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cached["powerIsOn"] = True
        actual = copy.deepcopy(cached)
        actual["powerIsOn"] = False
        device, receiver = make_device(cached, actual)

        assert device.power is True  # Deliberately stale before the command.
        assert await device.toggle_power() is True
        assert receiver.state["powerIsOn"] is True
        assert device.power is True
        assert receiver.changes == [[
            {"op": "replace", "path": "/powerIsOn", "value": True}
        ]]

    asyncio.run(exercise())


def test_concurrent_toggles_serialize_and_each_use_the_latest_state():
    async def exercise():
        state = json.loads(FIXTURE.read_text(encoding="utf-8"))
        state["powerIsOn"] = False
        gate = asyncio.Event()
        device, receiver = make_device(state, first_change_gate=gate)

        first = asyncio.create_task(device.toggle_power())
        await asyncio.wait_for(receiver.first_change_started.wait(), timeout=1)
        second = asyncio.create_task(device.toggle_power())
        await asyncio.sleep(0)
        gate.set()

        assert await asyncio.wait_for(asyncio.gather(first, second), timeout=2) == [True, True]
        assert receiver.state["powerIsOn"] is False
        assert [patch[0]["value"] for patch in receiver.changes] == [True, False]
        assert device.power is False

    asyncio.run(exercise())


def test_toggle_refresh_timeout_aborts_without_writing(monkeypatch):
    async def exercise():
        state = json.loads(FIXTURE.read_text(encoding="utf-8"))
        device, receiver = make_device(state, reply=False)
        monkeypatch.setattr(device_module, "STATE_REFRESH_TIMEOUT", 0.01)

        assert await device.toggle_power() is False
        assert receiver.messages == ["getmso"]
        assert receiver.changes == []

    asyncio.run(exercise())
