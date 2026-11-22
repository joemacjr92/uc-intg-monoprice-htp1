"""Seat-shaker and PEQ/BEQ command-to-state round-trip tests."""

import asyncio
import copy
import json
from pathlib import Path

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device, apply_json_patch


FULL_FIXTURE = Path(__file__).parents[1] / "fixtures" / "htp1_full_mso.json"
BEQ_FIXTURE = Path(__file__).parents[1] / "fixtures" / "mso_beq_pre_active.json"


class RecordingWebSocket:
    def __init__(self):
        self.messages = []

    async def send(self, message):
        self.messages.append(message)


def make_device(fixture=FULL_FIXTURE):
    device = HTP1Device(
        HTP1Config("audio-roundtrip", "Audio Round Trip", "127.0.0.1"),
        loop=asyncio.get_running_loop(),
    )
    device._is_connected = True
    device._state = json.loads(fixture.read_text(encoding="utf-8"))
    device._parse_state()
    device._ws = RecordingWebSocket()
    return device


async def apply_last_transaction(device, extra_echo_operations=None):
    message = device._ws.messages[-1]
    assert message.startswith("changemso ")
    operations = json.loads(message.partition(" ")[2])
    echoed = operations + (extra_echo_operations or [])
    candidate = copy.deepcopy(device._state)
    for operation in echoed:
        apply_json_patch(
            candidate,
            operation["op"],
            operation["path"],
            operation.get("value"),
        )
    await device.handle_message(f"msoupdate {json.dumps(echoed)}")
    assert device._state == candidate
    return operations


def test_seat_shaker_mute_command_round_trips_to_parsed_state():
    async def exercise():
        device = make_device()
        assert await device.ss_mute_toggle(True)
        operations = await apply_last_transaction(device)

        assert operations == [
            {"op": "replace", "path": "/shaker/mute", "value": "on"}
        ]
        assert device._state["shaker"]["mute"] == "on"
        assert device.ss_mute == "on"
        assert device.get_sensor_value("ss_mute") == "On"

    asyncio.run(exercise())


def test_seat_shaker_preset_selection_round_trips_to_parsed_state():
    async def exercise():
        device = make_device()
        assert await device.select_ss_preset(2)
        operations = await apply_last_transaction(device)

        assert operations == [
            {"op": "replace", "path": "/shaker/activePreset", "value": 2}
        ]
        assert device._state["shaker"]["activePreset"] == 2
        assert device.ss_preset == 3
        # The parser reports the selected preset's saved trim.
        assert device.ss_trim == device._state["shaker"]["presets"]["2"]["trim"]
        assert device.get_sensor_value("ss_preset") == 3

    asyncio.run(exercise())


def test_seat_shaker_trim_command_round_trips_to_current_trim_readback():
    async def exercise():
        device = make_device()
        requested_trim = 4
        assert await device.set_ss_trim(requested_trim)
        operations = await apply_last_transaction(device)

        assert operations == [
            {"op": "replace", "path": "/shaker/trim", "value": requested_trim}
        ]
        assert device._state["shaker"]["trim"] == requested_trim
        assert device.ss_trim == requested_trim
        assert device.get_sensor_value("ss_trim") == str(requested_trim)

    asyncio.run(exercise())


def test_beq_load_command_round_trips_to_lfe_pre_peq_state():
    async def exercise():
        device = make_device(BEQ_FIXTURE)
        filters = [
            {"type": "PeakingEQ", "freq": 25, "gain": 3.5, "q": 1.2},
            {"type": "LowShelf", "freq": 30, "gain": -2.0, "q": 0.8},
        ]
        title = "Phase 1.5 round-trip BEQ"

        assert await device.load_beq(title, filters)
        operations = await apply_last_transaction(device)

        assert operations
        assert device._state["peq"]["location"] == "pre"
        assert device._state["peq"]["peqsw"] is True
        assert device._state["peq"]["beqActive"] == title
        assert device.beq_active == title
        assert device.get_sensor_value("beq_active") == title

        tagged = []
        for slot_index, slot in enumerate(device._state["peq"]["slots"]):
            for channel, values in slot.get("channels", {}).items():
                if values.get("beq") is True:
                    tagged.append((slot_index, channel, values))
        assert len(tagged) == len(filters)
        assert all(channel == "sub1" for _, channel, _ in tagged)
        assert tagged[0][2]["Fc"] == 25
        assert tagged[0][2]["gaindB"] == 3.5
        assert tagged[1][2]["Fc"] == 30
        assert tagged[1][2]["gaindB"] == -2.0

    asyncio.run(exercise())


def test_beq_clear_command_round_trips_to_inactive_state():
    async def exercise():
        device = make_device(BEQ_FIXTURE)
        assert device.beq_active
        assert await device.clear_beq()
        operations = await apply_last_transaction(device)

        assert operations
        assert "beqActive" not in device._state["peq"]
        assert device.beq_active == ""
        assert device.get_sensor_value("beq_active") == "None"
        assert all(
            values.get("beq") is not True
            for slot in device._state["peq"]["slots"]
            for values in slot.get("channels", {}).values()
        )

    asyncio.run(exercise())
