"""Receiver-correlated Dirac switch lifecycle tests."""

import asyncio
import copy
import json
from pathlib import Path

import pytest

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import DiracLifecycleState, HTP1Device, apply_json_patch


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
        if not any(operation.get("path") == "/cal/currentdiracslot" for operation in operations):
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
        slot = operations[0]["value"]
        self.request_id = f"receiver-request-{self.change_count}"
        if self.mode == "disconnect-before-acceptance":
            self.device._on_connection_lost()
            return
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
        elif self.mode == "delayed-standby":
            task = asyncio.create_task(self._delayed_refuse(slot))
            self.tasks.append(task)
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
                    "id": "stale-unrelated-request",
                },
            }
            apply_json_patch(self.state, reply["op"], reply["path"], reply["value"])
            await self.device.handle_message(f"msoupdate {json.dumps([reply])}")
            task = asyncio.create_task(self._complete(slot))
            self.tasks.append(task)

    async def _delayed_refuse(self, slot):
        """Refuse after the integration has had time to acknowledge acceptance."""
        await asyncio.sleep(0.35)
        await self._refuse(slot)

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


def test_dirac_selection_acknowledges_receiver_acceptance_before_completion():
    async def exercise():
        device, receiver = make_device(delay=0.15)
        try:
            original_display = device.dirac_slot_name
            started = asyncio.get_running_loop().time()
            result = await device.select_calibration(device.slot_names[1])
            elapsed = asyncio.get_running_loop().time() - started

            assert result is True
            assert device._dirac_lifecycle_state is DiracLifecycleState.ACCEPTED
            assert elapsed < 0.15
            assert receiver.change_count == 1
            assert receiver.getmso_count == 1
            assert receiver.state["cal"]["diracSwitch"]["id"] == receiver.request_id
            assert receiver.state["cal"]["diracSwitch"]["state"] == "requested"
            # currentdiracslot moves early, but the Remote display remains confirmed.
            assert device.dirac_slot_name == original_display

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            assert receiver.getmso_count == 2
            assert receiver.state["cal"]["diracSwitch"]["state"] == "complete"
            assert receiver.state["cal"]["currentdiracslot"] == 1
            assert device.dirac_slot_name == device.slot_names[1]
            assert device._dirac_lifecycle_state is DiracLifecycleState.COMPLETE
            assert device._dirac_display_held is False
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


def test_delayed_standby_refusal_after_acceptance_keeps_confirmed_display():
    async def exercise():
        device, receiver = make_device(mode="delayed-standby")
        try:
            original_display = device.dirac_slot_name
            result = await device.select_calibration(device.slot_names[1])

            # The receiver first publishes "requested", so the Remote is
            # acknowledged before its delayed standby refusal arrives.
            assert result is True
            assert device._dirac_task is not None
            assert device._dirac_operation_lock.locked()
            assert device.dirac_slot_name == original_display

            task = device._dirac_task
            await asyncio.wait_for(task, timeout=1.0)

            assert receiver.state["cal"]["diracSwitchReply"]["id"] == receiver.request_id
            assert receiver.state["cal"]["diracSwitchReply"]["state"] == "refused"
            assert receiver.state["cal"]["diracSwitch"] == receiver.previous_switch
            assert receiver.state["cal"]["currentdiracslot"] == 0
            assert receiver.getmso_count == 1  # No success readback after refusal.
            assert device.dirac_slot_name == original_display
            assert device._dirac_display_held is True
            assert not device._dirac_operation_lock.locked()
            assert device._dirac_task is None
            assert device._dirac_lifecycle_state is DiracLifecycleState.FAILED
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_unrelated_busy_reply_does_not_fail_accepted_dirac_request():
    async def exercise():
        device, receiver = make_device(mode="busy-reply", delay=0.05)
        try:
            result = await device.select_calibration(device.slot_names[1])

            assert result is True
            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)
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
            assert device._dirac_error.startswith("Dirac is busy")
            assert device._dirac_lifecycle_state is DiracLifecycleState.FAILED
            assert not device._dirac_operation_lock.locked()
            assert device._dirac_task is None
            assert device._dirac_volume_snapshot is None
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



def test_dirac_captures_volume_and_rejects_second_dirac_request():
    async def exercise():
        device, receiver = make_device(delay=0.3)
        try:
            original_display = device.dirac_slot_name
            current_volume = device._state["volume"]
            first = await device.select_calibration(device.slot_names[1])
            assert first is True

            # A second calibration selection is rejected immediately.
            second = await device.select_calibration(device.slot_names[0])
            assert second is False
            assert receiver.change_count == 1

            # Volume intent is acknowledged promptly but not written during DSP.
            volume_result = await asyncio.wait_for(
                device.set_volume(current_volume - 1), timeout=0.2
            )
            assert volume_result is True
            assert receiver.state["volume"] == current_volume
            assert _volume_writes(receiver) == []
            assert device.dirac_slot_name == original_display

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=2.0)
            assert device.dirac_slot_name == device.slot_names[1]
            assert receiver.state["cal"]["currentdiracslot"] == 1
            assert receiver.state["volume"] == current_volume - 1
            assert _volume_writes(receiver) == [current_volume - 1]
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_switch_timeout_does_not_claim_success():
    async def exercise():
        device, receiver = make_device(mode="never")
        device._dirac_switch_timeout = 0.0
        try:
            original_display = device.dirac_slot_name
            result = await device.select_calibration(device.slot_names[1])

            assert result is True  # Receiver accepted; lifecycle timeout is asynchronous.
            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=0.1)
            assert receiver.change_count == 1
            assert receiver.getmso_count == 1
            assert device.dirac_slot_name == original_display
            assert not device._dirac_operation_lock.locked()
            assert device._dirac_lifecycle_state is DiracLifecycleState.FAILED
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_acceptance_and_concurrent_volume_stress():
    """Repeat the asynchronous handoff to expose timing-sensitive early failures."""
    async def exercise():
        for attempt in range(20):
            device, receiver = make_device(delay=0.5)
            try:
                original_display = device.dirac_slot_name
                started = asyncio.get_running_loop().time()
                result = await device.select_calibration(device.slot_names[1])
                elapsed = asyncio.get_running_loop().time() - started

                assert result is True, (
                    f"attempt={attempt + 1}/20 elapsed={elapsed:.3f}s "
                    f"dirac_error={device._dirac_error!r} "
                    f"transaction_error={device._transaction_error!r} "
                    f"request_id={device._dirac_request_id!r} "
                    f"request_slot={device._dirac_request_slot!r} "
                    f"getmso_count={receiver.getmso_count} "
                    f"change_count={receiver.change_count} "
                    f"switch={receiver.state['cal'].get('diracSwitch')!r} "
                    f"reply={receiver.state['cal'].get('diracSwitchReply')!r} "
                    f"messages={receiver.messages!r}"
                )
                assert elapsed < 0.5
                assert receiver.change_count == 1

                second = await device.select_calibration(device.slot_names[0])
                assert second is False
                current_volume = device._state["volume"]
                volume_result = await asyncio.wait_for(
                    device.set_volume(current_volume - 1), timeout=0.2
                )
                assert volume_result is True
                assert receiver.state["volume"] == current_volume
                assert _volume_writes(receiver) == []
                assert device.dirac_slot_name == original_display

                task = device._dirac_task
                assert task is not None
                await asyncio.wait_for(task, timeout=2.0)
                assert device.dirac_slot_name == device.slot_names[1]
                assert receiver.state["volume"] == current_volume - 1
                assert _volume_writes(receiver) == [current_volume - 1]
            finally:
                await receiver.cleanup()

    asyncio.run(exercise())

def _volume_writes(receiver):
    """Return receiver volume patches sent by the integration."""
    writes = []
    for message in receiver.messages:
        if not message.startswith("changemso "):
            continue
        operations = json.loads(message.partition(" ")[2])
        writes.extend(
            operation["value"]
            for operation in operations
            if operation.get("path") == "/volume"
        )
    return writes


def test_dirac_volume_steps_are_captured_and_aggregated_into_one_write():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            starting_volume = receiver.state["volume"]
            result = await device.select_calibration(device.slot_names[1])
            assert result is True

            for _ in range(5):
                assert await device.volume_up() is True
            for _ in range(2):
                assert await device.volume_down() is True

            # No volume transaction is sent while the receiver applies Dirac.
            assert receiver.change_count == 1
            assert _volume_writes(receiver) == []
            assert receiver.state["volume"] == starting_volume
            assert device._dirac_volume_delta == 3

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            assert _volume_writes(receiver) == [starting_volume + 3]
            assert receiver.change_count == 2
            assert receiver.state["volume"] == starting_volume + 3
            assert device._dirac_volume_capture_active is False
            assert device._dirac_volume_snapshot is None
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_volume_capture_preserves_displayed_db_when_zero_point_changes():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            start_display_db = receiver.state["volume"] - receiver.state["cal"]["zeroPoint"]
            assert await device.select_calibration(device.slot_names[1]) is True
            assert await device.volume_up() is True
            assert await device.volume_up() is True

            # Model a calibration whose zero point and raw volume bounds differ
            # after the selected Dirac slot has finished applying.
            receiver.state["cal"]["zeroPoint"] = -10
            receiver.state["cal"]["vpl"] = -70
            receiver.state["cal"]["vph"] = -10

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            expected_display_db = start_display_db + 2
            assert receiver.state["volume"] - receiver.state["cal"]["zeroPoint"] == expected_display_db
            assert _volume_writes(receiver) == [expected_display_db + receiver.state["cal"]["zeroPoint"]]
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_volume_burst_reuses_existing_five_db_jump_limiter():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            starting_volume = receiver.state["volume"]
            assert await device.select_calibration(device.slot_names[1]) is True

            for _ in range(12):
                assert await device.volume_up() is True
            assert device._dirac_volume_delta == 12
            assert _volume_writes(receiver) == []

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            # The desired target is +12 dB, but the existing set-volume
            # limiter allows only a +5 dB write in one operation.
            assert _volume_writes(receiver) == [starting_volume + 5]
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_volume_capture_clamps_pending_delta_at_upper_and_lower_bounds():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            receiver.state["volume"] = -15
            receiver.state["cal"]["vph"] = -14
            device._state["volume"] = -15
            device._state["cal"]["vph"] = -14
            device._parse_state()

            assert await device.select_calibration(device.slot_names[1]) is True
            for _ in range(8):
                assert await device.volume_up() is True
            assert device._dirac_volume_delta == 1
            assert await device.volume_down() is True
            assert device._dirac_volume_delta == 0

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)
            assert _volume_writes(receiver) == []
        finally:
            await receiver.cleanup()

        device, receiver = make_device(delay=0.1)
        try:
            receiver.state["volume"] = -79
            device._state["volume"] = -79
            device._parse_state()

            assert await device.select_calibration(device.slot_names[1]) is True
            for _ in range(8):
                assert await device.volume_down() is True
            assert device._dirac_volume_delta == -1
            assert await device.volume_up() is True
            assert device._dirac_volume_delta == 0

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)
            assert _volume_writes(receiver) == []
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_absolute_raw_volume_request_becomes_base_for_later_steps():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            assert await device.set_volume(-40) is True
            assert await device.volume_up() is True
            assert await device.volume_up() is True

            assert device._dirac_volume_absolute_db == -33
            assert device._dirac_volume_delta == 2
            assert _volume_writes(receiver) == []

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            # The desired raw target is -38 dB; the shared limiter clamps
            # the 11 dB downward jump to 5 dB from the current -27 dB.
            assert _volume_writes(receiver) == [-32]
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_absolute_level_request_uses_captured_bounds_and_last_absolute_wins():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            assert await device.volume_up() is True
            assert await device.set_volume_level(0.5) is True
            assert await device.volume_down() is True
            assert await device.set_volume_level(0.75) is True

            snapshot = device._dirac_volume_snapshot
            assert snapshot is not None
            expected_raw = round(snapshot["vpl"] + 0.75 * (snapshot["vph"] - snapshot["vpl"]))
            assert device._dirac_volume_absolute_db == expected_raw - snapshot["zp"]
            assert device._dirac_volume_delta == 0
            assert _volume_writes(receiver) == []

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            # A 0.75 level maps to raw -30 dB, a 3 dB change from -27 dB.
            # The shared helper therefore does not need to clamp this target.
            assert _volume_writes(receiver) == [-30]
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_rejects_invalid_absolute_volume_without_losing_relative_requests():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            assert await device.volume_up() is True
            assert await device.set_volume(999) is False
            assert await device.set_volume_level(float("nan")) is False
            assert device._dirac_volume_delta == 1
            assert device._dirac_volume_absolute_db is None

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)
            assert _volume_writes(receiver) == [-26]
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_blocks_non_volume_mutations_without_refreshing_receiver():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            messages_before = list(receiver.messages)
            getmso_before = receiver.getmso_count

            assert await device.mute_toggle(True) is False
            assert await device.turn_off() is False
            assert await device.select_source("HDMI 1") is False
            assert await device.select_ss_preset(1) is False
            assert await device.clear_beq() is False
            assert await device.load_beq("test", []) is False
            assert await device.send_command("send_avcui: hpe") is False
            assert await device.send_http_command("0001") is False

            assert receiver.messages == messages_before
            assert receiver.getmso_count == getmso_before
            assert receiver.change_count == 1

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_refusal_discards_captured_volume_requests():
    async def exercise():
        device, receiver = make_device(mode="delayed-standby")
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            assert await device.volume_up() is True
            assert await device.volume_up() is True
            assert receiver.change_count == 1

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            assert _volume_writes(receiver) == []
            assert receiver.state["volume"] == -27
            assert device._dirac_volume_capture_active is False
            assert device._dirac_volume_snapshot is None
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_timeout_discards_captured_volume_requests():
    async def exercise():
        device, receiver = make_device(mode="never")
        device._dirac_switch_timeout = 0.0
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            assert await device.volume_up() is True

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=0.2)

            assert _volume_writes(receiver) == []
            assert device._dirac_volume_capture_active is False
            assert device._dirac_volume_snapshot is None
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_disconnect_discards_captured_volume_requests():
    async def exercise():
        device, receiver = make_device(mode="never")
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            assert await device.volume_up() is True
            device._on_connection_lost()

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=0.2)

            assert _volume_writes(receiver) == []
            assert device._dirac_volume_capture_active is False
            assert device._dirac_volume_snapshot is None
            assert device._dirac_lifecycle_state is DiracLifecycleState.FAILED
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_invalid_start_volume_snapshot_fails_closed():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            receiver.state["cal"]["vph"] = "invalid"
            device._state["cal"]["vph"] = "invalid"
            device._parse_state()

            assert await device.select_calibration(device.slot_names[1]) is True
            assert await device.volume_up() is False

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            assert _volume_writes(receiver) == []
            assert device._dirac_volume_capture_active is False
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_completion_without_volume_requests_does_not_send_volume_write():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            assert receiver.change_count == 1
            assert _volume_writes(receiver) == []
            assert device._dirac_volume_capture_active is False
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())

def test_dirac_high_frequency_volume_burst_still_produces_one_limited_write():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            starting_volume = receiver.state["volume"]
            assert await device.select_calibration(device.slot_names[1]) is True

            for _ in range(40):
                assert await device.volume_up() is True

            assert device._dirac_volume_delta == 13  # Clamped at the captured VPH.
            assert _volume_writes(receiver) == []
            assert receiver.change_count == 1

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            # The user requested a large increase, but only one 5 dB write
            # is sent after Dirac; the existing limiter remains authoritative.
            assert _volume_writes(receiver) == [starting_volume + 5]
            assert receiver.change_count == 2
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())

def test_dirac_command_gate_releases_after_confirmed_completion():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            assert await device.mute_toggle(True) is False

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            assert device._dirac_commands_blocked() is False
            assert await device.mute_toggle(True) is True
            assert receiver.state["muted"] is True
            assert receiver.change_count == 2
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())

def test_volume_request_queued_before_dirac_start_is_captured_after_lock_release():
    async def exercise():
        device, receiver = make_device()
        try:
            async with device._transaction_lock:
                pending = asyncio.create_task(device.volume_up())
                await asyncio.sleep(0)
                device._begin_dirac_volume_capture()
                device._set_dirac_lifecycle_state(DiracLifecycleState.REQUESTED)

            assert await asyncio.wait_for(pending, timeout=0.2) is True
            assert device._dirac_volume_delta == 1
            assert receiver.change_count == 0
            assert receiver.getmso_count == 0
        finally:
            device._set_dirac_lifecycle_state(DiracLifecycleState.FAILED)
            device._discard_dirac_volume_capture()
            await receiver.cleanup()

    asyncio.run(exercise())


def test_non_volume_mutation_queued_before_dirac_start_is_rejected_after_lock_release():
    async def exercise():
        device, receiver = make_device()
        try:
            async with device._transaction_lock:
                pending = asyncio.create_task(device.mute_toggle(True))
                await asyncio.sleep(0)
                device._set_dirac_lifecycle_state(DiracLifecycleState.REQUESTED)

            assert await asyncio.wait_for(pending, timeout=0.2) is False
            assert receiver.messages == []
            assert receiver.change_count == 0
            assert receiver.getmso_count == 0
        finally:
            device._set_dirac_lifecycle_state(DiracLifecycleState.FAILED)
            await receiver.cleanup()

    asyncio.run(exercise())

def test_absolute_volume_requests_queued_before_dirac_start_are_captured_after_lock_release():
    async def exercise():
        device, receiver = make_device()
        try:
            async with device._transaction_lock:
                pending = asyncio.create_task(device.set_volume(-40))
                await asyncio.sleep(0)
                device._begin_dirac_volume_capture()
                device._set_dirac_lifecycle_state(DiracLifecycleState.REQUESTED)

            assert await asyncio.wait_for(pending, timeout=0.2) is True
            assert device._dirac_volume_absolute_db == -33
            assert device._dirac_volume_delta == 0
            assert receiver.messages == []
        finally:
            device._set_dirac_lifecycle_state(DiracLifecycleState.FAILED)
            device._discard_dirac_volume_capture()
            await receiver.cleanup()

        device, receiver = make_device()
        try:
            async with device._transaction_lock:
                pending = asyncio.create_task(device.set_volume_level(0.5))
                await asyncio.sleep(0)
                device._begin_dirac_volume_capture()
                device._set_dirac_lifecycle_state(DiracLifecycleState.REQUESTED)

            assert await asyncio.wait_for(pending, timeout=0.2) is True
            snapshot = device._dirac_volume_snapshot
            assert snapshot is not None
            expected_raw = round(snapshot["vpl"] + 0.5 * (snapshot["vph"] - snapshot["vpl"]))
            assert device._dirac_volume_absolute_db == expected_raw - snapshot["zp"]
            assert device._dirac_volume_delta == 0
            assert receiver.messages == []
        finally:
            device._set_dirac_lifecycle_state(DiracLifecycleState.FAILED)
            device._discard_dirac_volume_capture()
            await receiver.cleanup()

    asyncio.run(exercise())




def test_dirac_lifecycle_rejects_illegal_transitions_and_allows_new_requests_after_terminal_states():
    async def exercise():
        device, receiver = make_device()
        try:
            assert device._dirac_lifecycle_state is DiracLifecycleState.IDLE
            assert not hasattr(device, "_dirac_accepting")
            assert not hasattr(device, "_dirac_display_hold")
            assert not hasattr(device, "_dirac_pending_slot_idx")
            with pytest.raises(ValueError, match="idle -> accepted"):
                device._set_dirac_lifecycle_state(DiracLifecycleState.ACCEPTED)

            device._set_dirac_lifecycle_state(DiracLifecycleState.REQUESTED)
            assert device._dirac_commands_blocked() is True
            device._set_dirac_lifecycle_state(DiracLifecycleState.FAILED)
            assert device._dirac_commands_blocked() is False
            # A failed terminal state can begin a fresh request.
            result = await device.select_calibration(device.slot_names[1])
            assert result is True
            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)
            assert device._dirac_lifecycle_state is DiracLifecycleState.COMPLETE

            # A completed terminal state can also begin another request.
            result = await device.select_calibration(device.slot_names[0])
            assert result is True
            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)
            assert device._dirac_lifecycle_state is DiracLifecycleState.COMPLETE
            assert receiver.change_count == 2
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_lifecycle_exposes_applying_then_complete_only_after_final_readback():
    async def exercise():
        device, receiver = make_device(delay=0.05)
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            task = device._dirac_task
            assert task is not None
            deadline = asyncio.get_running_loop().time() + 0.5
            while (
                device._dirac_lifecycle_state is not DiracLifecycleState.APPLYING
                and asyncio.get_running_loop().time() < deadline
            ):
                await asyncio.sleep(0.005)

            assert device._dirac_lifecycle_state is DiracLifecycleState.APPLYING
            await asyncio.wait_for(task, timeout=1.0)
            assert device._dirac_lifecycle_state is DiracLifecycleState.COMPLETE
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_monitor_cancellation_fails_closed_and_releases_owned_resources():
    async def exercise():
        device, receiver = make_device(mode="never")
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            assert await device.volume_up() is True
            task = device._dirac_task
            assert task is not None

            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

            assert device._dirac_lifecycle_state is DiracLifecycleState.FAILED
            assert not device._dirac_operation_lock.locked()
            assert device._dirac_task is None
            assert device._dirac_volume_capture_active is False
            assert device._dirac_volume_snapshot is None
            assert _volume_writes(receiver) == []
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_disconnect_before_receiver_acceptance_fails_promptly():
    async def exercise():
        device, receiver = make_device(mode="disconnect-before-acceptance")
        try:
            started = asyncio.get_running_loop().time()
            assert await device.select_calibration(device.slot_names[1]) is False
            assert asyncio.get_running_loop().time() - started < 0.2
            assert device._dirac_lifecycle_state is DiracLifecycleState.FAILED
            assert not device._dirac_operation_lock.locked()
            assert device._dirac_task is None
            assert device._dirac_volume_capture_active is False
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())



def test_dirac_command_gate_remains_active_until_deferred_volume_finalization():
    async def exercise():
        device, receiver = make_device(delay=0.05)
        apply_started = asyncio.Event()
        allow_apply = asyncio.Event()
        original_apply = device._apply_deferred_dirac_volume_locked

        async def paused_apply():
            apply_started.set()
            await allow_apply.wait()
            return await original_apply()

        device._apply_deferred_dirac_volume_locked = paused_apply
        try:
            assert await device.select_calibration(device.slot_names[1]) is True
            assert await device.volume_up() is True
            task = device._dirac_task
            assert task is not None

            await asyncio.wait_for(apply_started.wait(), timeout=1.0)
            assert device._dirac_lifecycle_state in {
                DiracLifecycleState.ACCEPTED,
                DiracLifecycleState.APPLYING,
            }
            assert device._dirac_commands_blocked() is True
            messages_before = list(receiver.messages)
            assert await device.send_command("send_avcui: hpe") is False
            assert receiver.messages == messages_before

            allow_apply.set()
            await asyncio.wait_for(task, timeout=1.0)
            assert device._dirac_lifecycle_state is DiracLifecycleState.COMPLETE
            assert device._dirac_commands_blocked() is False
            assert _volume_writes(receiver) == [receiver.state["volume"]]
        finally:
            allow_apply.set()
            await receiver.cleanup()

    asyncio.run(exercise())



def test_dirac_sensor_status_reports_loading_then_confirmed_slot():
    async def exercise():
        device, receiver = make_device(delay=0.1)
        try:
            target = device.slot_names[1]
            original = device.dirac_slot_name
            assert device.dirac_status_text == original
            assert device.get_sensor_value("dirac_slot") == original

            assert await device.select_calibration(target) is True
            assert device.dirac_status_text == f"Loading {target}"
            assert device.get_sensor_value("dirac_slot") == f"Loading {target}"
            assert device.dirac_slot_name == original

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)

            assert device.dirac_status_text == target
            assert device.get_sensor_value("dirac_slot") == target
            assert device.dirac_slot_name == target
            assert device._dirac_lifecycle_state is DiracLifecycleState.COMPLETE
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_sensor_status_persists_refusal_until_next_request():
    async def exercise():
        device, receiver = make_device(mode="standby")
        try:
            original = device.dirac_slot_name
            target = device.slot_names[1]

            assert await device.select_calibration(target) is False
            assert device.dirac_status_text == "Not applied: standby"
            assert device.get_sensor_value("dirac_slot") == "Not applied: standby"
            assert device.dirac_slot_name == original
            assert device._dirac_lifecycle_state is DiracLifecycleState.FAILED

            # A new request clears the previous failure and displays its target.
            receiver.mode = "complete"
            assert await device.select_calibration(target) is True
            assert device.dirac_status_text == f"Loading {target}"
            assert device.get_sensor_value("dirac_slot") == f"Loading {target}"

            task = device._dirac_task
            assert task is not None
            await asyncio.wait_for(task, timeout=1.0)
            assert device.dirac_status_text == target
            assert device.get_sensor_value("dirac_slot") == target
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_dirac_sensor_status_uses_short_failure_reasons():
    async def exercise():
        device, receiver = make_device()
        try:
            device._dirac_target_slot_name = device.slot_names[1]
            device._set_dirac_lifecycle_state(DiracLifecycleState.REQUESTED)
            device._dirac_failure_reason = (
                "Timed out waiting for the HTP-1 to complete the Dirac slot change"
            )
            device._set_dirac_lifecycle_state(DiracLifecycleState.FAILED)
            assert device.dirac_status_text == "Not applied: timeout"
            assert device.get_sensor_value("dirac_slot") == "Not applied: timeout"

            device._dirac_target_slot_name = device.slot_names[2]
            device._set_dirac_lifecycle_state(DiracLifecycleState.REQUESTED)
            device._dirac_failure_reason = "HTP-1 is busy applying a correction"
            device._set_dirac_lifecycle_state(DiracLifecycleState.FAILED)
            assert device.dirac_status_text == "Not applied: busy"
            assert device.get_sensor_value("dirac_slot") == "Not applied: busy"
        finally:
            await receiver.cleanup()

    asyncio.run(exercise())


def test_observed_hardware_traces_correlate_refusal_and_ignore_stale_reply():
    trace_path = Path(__file__).parents[1] / "fixtures" / "dirac_hardware_traces.json"
    traces = json.loads(trace_path.read_text(encoding="utf-8"))
    device, receiver = make_device()
    try:
        standby = traces["standby"]
        refusal = standby["reply"]
        assert refusal["id"] == standby["request"]["id"]
        assert device._dirac_refusal(
            standby["request"]["id"], standby["previous_reply"]["id"]
        ) == refusal["message"]

        success = traces["successful_switch"]
        assert success["request"]["id"] == success["running"]["id"]
        assert success["running"]["id"] == success["complete"]["id"]
        assert success["complete"]["state"] == "complete"

        # The standby refusal remains in the receiver snapshot during the later
        # successful operation, but its old request ID cannot fail the new one.
        device._state["cal"]["diracSwitch"] = success["complete"]
        device._state["cal"]["diracSwitchReply"] = refusal
        assert device._dirac_refusal(
            success["request"]["id"], refusal["id"]
        ) is None
    finally:
        asyncio.run(receiver.cleanup())
