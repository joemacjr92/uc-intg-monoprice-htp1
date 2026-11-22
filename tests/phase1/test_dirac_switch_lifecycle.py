"""Receiver-correlated Dirac switch lifecycle tests."""

import asyncio
import copy
import json
from pathlib import Path

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device, apply_json_patch


FIXTURE = Path(__file__).parents[1] / "fixtures" / "htp1_full_mso.json"


class DiracReceiver:
    """Fake the observed HTP-1 request, running, complete and refusal updates."""

    def __init__(self, device, state, *, mode="complete", delay=0.25):
        self.device = device
        self.state = copy.deepcopy(state)
        self.mode = mode
        self.delay = delay
        self.messages = []
        self.change_count = 0
        self.getmso_count = 0
        self.tasks = []
        self.request_id = "receiver-request-1"
        self.previous_switch = copy.deepcopy(self.state["cal"]["diracSwitch"])

    async def send(self, message):
        self.messages.append(message)
        if message == "getmso":
            self.getmso_count += 1
            await self.device.handle_message(f"mso {json.dumps(self.state)}")
            return
        if not message.startswith("changemso "):
            return

        self.change_count += 1
        operations = json.loads(message.partition(" ")[2])
        slot = operations[0]["value"]
        if self.mode == "busy":
            await self.device.handle_message("error Dirac is busy. Wait for it to finish; this change was not applied.")
            return

        candidate = copy.deepcopy(self.state)
        for operation in operations:
            apply_json_patch(
                candidate,
                operation["op"],
                operation["path"],
                operation.get("value"),
            )
        requested = {
            "version": 1,
            "id": self.request_id,
            "slot": slot,
            "state": "requested",
            "locked": True,
            "message": "Changing Dirac slot.",
        }
        patch = {"op": "replace", "path": "/cal/diracSwitch", "value": requested}
        apply_json_patch(candidate, patch["op"], patch["path"], patch["value"])
        self.state = candidate
        await self.device.handle_message(f"msoupdate {json.dumps(operations + [patch])}")

        if self.mode == "standby":
            await self._refuse(slot)
        elif self.mode == "complete":
            task = asyncio.create_task(self._complete(slot))
            self.tasks.append(task)
        elif self.mode == "busy-reply":
            await self.device.handle_message(
                "error Dirac is busy. Wait for it to finish; this change was not applied."
            )
            reply = {
                "op": "replace",
                "path": "/cal/diracSwitchReply",
                "value": {
                    "state": "refused",
                    "message": "Dirac is busy. Wait for it to finish; this change was not applied.",
                    "id": "nr-unrelated-request",
                },
            }
            apply_json_patch(self.state, reply["op"], reply["path"], reply["value"])
            await self.device.handle_message(f"msoupdate {json.dumps([reply])}")
            task = asyncio.create_task(self._complete(slot))
            self.tasks.append(task)

    async def _complete(self, slot):
        await asyncio.sleep(self.delay)
        running = {
            "op": "replace",
            "path": "/cal/diracSwitch",
            "value": {
                "version": 1,
                "id": self.request_id,
                "slot": slot,
                "state": "running",
                "locked": True,
                "message": "Changing Dirac slot.",
            },
        }
        apply_json_patch(self.state, running["op"], running["path"], running["value"])
        await self.device.handle_message(f"msoupdate {json.dumps([running])}")
        await asyncio.sleep(self.delay)
        complete = {
            "op": "replace",
            "path": "/cal/diracSwitch",
            "value": {
                "version": 1,
                "id": self.request_id,
                "slot": slot,
                "state": "complete",
                "locked": False,
                "message": "Slot change verified.",
            },
        }
        apply_json_patch(self.state, complete["op"], complete["path"], complete["value"])
        await self.device.handle_message(f"msoupdate {json.dumps([complete])}")

    async def _refuse(self, slot):
        reply = {
            "op": "replace",
            "path": "/cal/diracSwitchReply",
            "value": {
                "version": 1,
                "id": self.request_id,
                "slot": 0,
                "state": "refused",
                "locked": False,
                "message": "Dirac slot changes are unavailable in standby and while the processor starts.",
            },
        }
        apply_json_patch(self.state, reply["op"], reply["path"], reply["value"])
        await self.device.handle_message(f"msoupdate {json.dumps([reply])}")
        revert = [
            {"op": "replace", "path": "/cal/currentdiracslot", "value": 0},
            {"op": "replace", "path": "/cal/diracSwitch", "value": self.previous_switch},
        ]
        for operation in revert:
            apply_json_patch(
                self.state, operation["op"], operation["path"], operation["value"]
            )
        await self.device.handle_message(f"msoupdate {json.dumps(revert)}")

    async def cleanup(self):
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)


def make_device(*, mode="complete", delay=0.25):
    state = json.loads(FIXTURE.read_text(encoding="utf-8"))
    device = HTP1Device(
        HTP1Config("dirac-lifecycle", "Dirac Lifecycle HTP-1", "127.0.0.1"),
        loop=asyncio.get_running_loop(),
    )
    device._state = copy.deepcopy(state)
    device._is_connected = True
    device._parse_state()
    receiver = DiracReceiver(device, state, mode=mode, delay=delay)
    device._ws = receiver
    return device, receiver


def test_dirac_selection_waits_for_matching_request_complete_before_readback():
    async def exercise():
        device, receiver = make_device(delay=0.15)
        try:
            started = asyncio.get_running_loop().time()
            result = await device.select_calibration(device.slot_names[1])
            elapsed = asyncio.get_running_loop().time() - started

            assert result is True
            assert elapsed >= 0.25
            assert receiver.change_count == 1
            assert receiver.getmso_count == 2
            assert receiver.state["cal"]["diracSwitch"]["id"] == receiver.request_id
            assert receiver.state["cal"]["diracSwitch"]["state"] == "complete"
            assert receiver.state["cal"]["currentdiracslot"] == 1
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_standby_refusal_with_matching_reply_fails_immediately():
    async def exercise():
        device, receiver = make_device(mode="standby")
        try:
            started = asyncio.get_running_loop().time()
            result = await device.select_calibration(device.slot_names[1])
            elapsed = asyncio.get_running_loop().time() - started

            assert result is False
            assert elapsed < 1.0
            assert receiver.change_count == 1
            assert receiver.getmso_count == 1
            assert receiver.state["cal"]["currentdiracslot"] == 0
            assert receiver.state["cal"]["diracSwitchReply"]["id"] == receiver.request_id
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_unrelated_busy_reply_does_not_fail_accepted_dirac_request():
    async def exercise():
        device, receiver = make_device(mode="busy-reply", delay=0.05)
        try:
            result = await device.select_calibration(device.slot_names[1])

            assert result is True
            assert receiver.state["cal"]["diracSwitch"]["id"] == receiver.request_id
            assert receiver.state["cal"]["diracSwitch"]["state"] == "complete"
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_busy_error_without_accepted_request_is_reported():
    async def exercise():
        device, receiver = make_device(mode="busy")
        try:
            started = asyncio.get_running_loop().time()
            result = await device.select_calibration(device.slot_names[1])
            elapsed = asyncio.get_running_loop().time() - started

            assert result is False
            assert elapsed < 1.5
            assert receiver.change_count == 1
            assert receiver.getmso_count == 1
            assert device._transaction_error.startswith("Dirac is busy")
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_busy_lock_preflight_does_not_send_another_slot_change():
    async def exercise():
        device, receiver = make_device()
        try:
            receiver.state["cal"]["diracSwitch"]["locked"] = True
            result = await device.select_calibration(device.slot_names[1])

            assert result is False
            assert receiver.getmso_count == 1
            assert receiver.change_count == 0
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_switch_timeout_does_not_claim_success(monkeypatch):
    async def exercise():
        device, receiver = make_device(mode="never")
        device._dirac_switch_timeout = 0.05
        try:
            result = await device.select_calibration(device.slot_names[1])

            assert result is False
            assert receiver.change_count == 1
            assert receiver.getmso_count == 1
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())
