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
    def __init__(self, device):
        self.device = device
        self.state = copy.deepcopy(device._state)
        self.messages = []

    async def send(self, message):
        self.messages.append(message)
        if message == "getmso":
            await self.device.handle_message(f"mso {json.dumps(self.state)}")
        elif message.startswith("changemso "):
            operations = json.loads(message.partition(" ")[2])
            candidate = copy.deepcopy(self.state)
            for operation in operations:
                apply_json_patch(
                    candidate,
                    operation["op"],
                    operation["path"],
                    operation.get("value"),
                )
            side_effects = []
            for operation in operations:
                if operation.get("path") == "/shaker/activePreset":
                    preset = str(operation["value"])
                    trim = candidate["shaker"]["presets"][preset]["trim"]
                    side_effect = {
                        "op": "replace", "path": "/shaker/trim", "value": trim
                    }
                    apply_json_patch(candidate, **{
                        "op": side_effect["op"],
                        "path_str": side_effect["path"],
                        "value": side_effect["value"],
                    })
                    side_effects.append(side_effect)
            self.state = candidate
            await self.device.handle_message(
                f"msoupdate {json.dumps(operations + side_effects)}"
            )


def make_device(fixture=FULL_FIXTURE):
    device = HTP1Device(
        HTP1Config("audio-roundtrip", "Audio Round Trip", "127.0.0.1"),
        loop=asyncio.get_running_loop(),
    )
    device._is_connected = True
    device._state = json.loads(fixture.read_text(encoding="utf-8"))
    device._parse_state()
    device._ws = RecordingWebSocket(device)
    return device


async def apply_last_transaction(device, extra_echo_operations=None):
    messages = [
        message for message in device._ws.messages
        if message.startswith("changemso ")
    ]
    assert messages
    operations = json.loads(messages[-1].partition(" ")[2])
    if extra_echo_operations:
        candidate = copy.deepcopy(device._ws.state)
        for operation in extra_echo_operations:
            apply_json_patch(
                candidate,
                operation["op"],
                operation["path"],
                operation.get("value"),
            )
        device._ws.state = candidate
        await device.handle_message(
            f"msoupdate {json.dumps(extra_echo_operations)}"
        )
    assert device._state == device._ws.state
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
        # Selecting a saved preset changes the receiver's current trim too;
        # model that accompanying state echo separately from the command patch.
        selected_trim = device._state["shaker"]["presets"]["2"]["trim"]
        operations = await apply_last_transaction(
            device,
            extra_echo_operations=[
                {"op": "replace", "path": "/shaker/trim", "value": selected_trim}
            ],
        )

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
