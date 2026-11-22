"""Slow receiver-response tests for power and Dirac state transactions."""

import asyncio
import copy
import json
from pathlib import Path

import pytest

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1 import device as device_module
from intg_monoprice_htp1.device import HTP1Device, apply_json_patch


FIXTURE = Path(__file__).parents[1] / "fixtures" / "htp1_full_mso.json"


class DelayedStateReceiver:
    """Receiver fake that schedules delayed full-state replies independently."""

    def __init__(self, device, state, *, delayed_getmso_calls):
        self.device = device
        self.state = copy.deepcopy(state)
        self.delayed_getmso_calls = set(delayed_getmso_calls)
        self.getmso_count = 0
        self.change_count = 0
        self.messages = []
        self.reply_tasks = []

    async def send(self, message):
        self.messages.append(message)
        if message == "getmso":
            self.getmso_count += 1
            delay = 0.05 if self.getmso_count in self.delayed_getmso_calls else 0
            task = asyncio.create_task(self._reply_state(delay))
            self.reply_tasks.append(task)
            return

        if message.startswith("changemso "):
            self.change_count += 1
            operations = json.loads(message.partition(" ")[2])
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

    async def _reply_state(self, delay):
        if delay:
            await asyncio.sleep(delay)
        if self.device.is_connected:
            await self.device.handle_message(f"mso {json.dumps(self.state)}")

    async def cleanup(self):
        for task in self.reply_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.reply_tasks, return_exceptions=True)


def make_device(*, delayed_getmso_calls):
    device = HTP1Device(
        HTP1Config("slow-response", "Slow Response HTP-1", "127.0.0.1"),
        loop=asyncio.get_running_loop(),
    )
    state = json.loads(FIXTURE.read_text(encoding="utf-8"))
    device._state = copy.deepcopy(state)
    device._is_connected = True
    device._parse_state()
    receiver = DelayedStateReceiver(
        device, state, delayed_getmso_calls=delayed_getmso_calls
    )
    device._ws = receiver
    return device, receiver


async def run_command(device, command):
    if command == "power":
        return await device.turn_on()
    return await device.select_calibration(device.slot_names[0])


@pytest.mark.parametrize("command", ["power", "dirac"])
def test_slow_preflight_state_response_aborts_power_and_dirac_without_writes(
    monkeypatch, command
):
    async def exercise():
        monkeypatch.setattr(device_module, "STATE_REFRESH_TIMEOUT", 0.01)
        device, receiver = make_device(delayed_getmso_calls={1})
        try:
            result = await run_command(device, command)

            assert result is False
            assert receiver.getmso_count == 1
            assert receiver.change_count == 0
            assert not any(
                message.startswith("changemso ") for message in receiver.messages
            )
            # A timed-out refresh must release the transaction lock.
            await asyncio.wait_for(device._transaction_lock.acquire(), timeout=0.1)
            device._transaction_lock.release()
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


@pytest.mark.parametrize("command", ["power", "dirac"])
def test_slow_post_write_state_response_does_not_claim_power_or_dirac_success(
    monkeypatch, command
):
    async def exercise():
        monkeypatch.setattr(device_module, "STATE_REFRESH_TIMEOUT", 0.01)
        device, receiver = make_device(delayed_getmso_calls={2})
        try:
            result = await run_command(device, command)

            assert result is False
            assert receiver.getmso_count == 2
            assert receiver.change_count == 1
            assert sum(
                message.startswith("changemso ") for message in receiver.messages
            ) == 1
            # The receiver's patch echo is retained, but a delayed full-state
            # verification is not mistaken for a completed transaction.
            assert device._state == receiver.state
            if command == "power":
                assert receiver.state["powerIsOn"] is True
            else:
                assert receiver.state["cal"]["currentdiracslot"] == device._slot_index[
                    device.slot_names[0]
                ]
            await asyncio.wait_for(device._transaction_lock.acquire(), timeout=0.1)
            device._transaction_lock.release()
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())
