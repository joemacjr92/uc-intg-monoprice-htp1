"""Command-to-state round-trip tests using the captured HTP-1 state fixture."""

import asyncio
import copy
import json
from pathlib import Path
from types import SimpleNamespace

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device, apply_json_patch
from intg_monoprice_htp1.media_player import HTP1MediaPlayer
from intg_monoprice_htp1.selector import HTP1Select
from ucapi import StatusCodes
from ucapi.media_player import Commands as MediaCommands
from ucapi.select import Commands as SelectCommands


FIXTURE = Path(__file__).parents[1] / "fixtures" / "htp1_full_mso.json"


class RecordingWebSocket:
    """Simulate receiver snapshots and state patches for verified transactions."""

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
            self.state = candidate
            await self.device.handle_message(f"msoupdate {json.dumps(operations)}")


def make_device():
    device = HTP1Device(
        HTP1Config("roundtrip", "Round Trip HTP-1", "127.0.0.1"),
        loop=asyncio.get_running_loop(),
    )
    device._is_connected = True
    device._state = json.loads(FIXTURE.read_text(encoding="utf-8"))
    device._parse_state()
    device._ws = RecordingWebSocket(device)
    return device


async def apply_recorded_transaction(device):
    """Return the captured write after the fake receiver has verified its readback."""
    messages = [
        message for message in device._ws.messages
        if message.startswith("changemso ")
    ]
    assert messages
    operations = json.loads(messages[-1].partition(" ")[2])
    assert device._state == device._ws.state
    return operations


def test_media_player_volume_command_round_trips_through_receiver_state():
    async def exercise():
        device = make_device()
        entity = SimpleNamespace(_device=device, id="media_player.roundtrip")

        status = await HTP1MediaPlayer._handle_command(
            entity, entity, MediaCommands.VOLUME, {"volume": 50}
        )

        assert status == StatusCodes.OK
        operations = await apply_recorded_transaction(device)
        # The fixture's current raw volume is -27. The existing five-dB
        # safeguard clamps the requested 50% target to -32 raw HTP-1 volume.
        assert operations == [
            {"op": "replace", "path": "/volume", "value": -32}
        ]
        assert device._state["volume"] == -32
        assert device.volume_db == -25
        assert device.get_sensor_value("volume") == "-25"

        updates = []
        player = SimpleNamespace(
            _device=device,
            update=lambda values: updates.append(values),
        )
        await HTP1MediaPlayer.sync_state(player)
        from ucapi.media_player import Attributes

        assert updates[-1][Attributes.VOLUME] == -25

    asyncio.run(exercise())



def test_volume_up_down_respect_fixture_zero_point_and_native_limits():
    async def exercise():
        device = make_device()

        # Use the captured receiver calibration values: zeroPoint=-7,
        # vpl=-80 and vph=-14. Volume limits apply to the raw MSO value;
        # the displayed dB value is raw volume minus zeroPoint.
        assert device.zp == -7
        assert device.vpl == -80
        assert device.vph == -14

        device._state["volume"] = -79
        device._ws.state["volume"] = -79
        device._parse_state()
        assert device.volume_db == -72
        assert await device.volume_down()
        operations = await apply_recorded_transaction(device)
        assert operations == [
            {"op": "replace", "path": "/volume", "value": -80}
        ]
        assert device._state["volume"] == -80
        assert device.volume_db == -73

        writes_before_limit = len([
            message for message in device._ws.messages
            if message.startswith("changemso ")
        ])
        assert await device.volume_down()
        writes_after_limit = len([
            message for message in device._ws.messages
            if message.startswith("changemso ")
        ])
        assert writes_after_limit == writes_before_limit

        device._state["volume"] = -15
        device._ws.state["volume"] = -15
        device._parse_state()
        assert await device.volume_up()
        operations = await apply_recorded_transaction(device)
        assert operations == [
            {"op": "replace", "path": "/volume", "value": -14}
        ]
        assert device._state["volume"] == -14

        writes_before_limit = len([
            message for message in device._ws.messages
            if message.startswith("changemso ")
        ])
        assert await device.volume_up()
        writes_after_limit = len([
            message for message in device._ws.messages
            if message.startswith("changemso ")
        ])
        assert writes_after_limit == writes_before_limit

    asyncio.run(exercise())

def test_media_player_mute_command_round_trips_through_receiver_state():
    async def exercise():
        device = make_device()
        entity = SimpleNamespace(_device=device, id="media_player.roundtrip")

        status = await HTP1MediaPlayer._handle_command(
            entity, entity, MediaCommands.MUTE, None
        )

        assert status == StatusCodes.OK
        operations = await apply_recorded_transaction(device)
        assert operations == [
            {"op": "replace", "path": "/muted", "value": True}
        ]
        assert device._state["muted"] is True
        assert device.muted is True
        assert device.get_sensor_value("mute") == "On"

        updates = []
        player = SimpleNamespace(
            _device=device,
            update=lambda values: updates.append(values),
        )
        await HTP1MediaPlayer.sync_state(player)
        from ucapi.media_player import Attributes

        assert updates[-1][Attributes.MUTED] is True

    asyncio.run(exercise())


def test_input_select_command_round_trips_through_receiver_state():
    async def exercise():
        device = make_device()
        entity = SimpleNamespace(
            _device=device,
            name="Input",
            _get_options=lambda: device.source_list,
            _command_fn=device.select_source,
        )

        status = await HTP1Select._handle_command(
            entity, entity, SelectCommands.SELECT_OPTION, {"option": "Streaming"}
        )

        assert status == StatusCodes.OK
        operations = await apply_recorded_transaction(device)
        assert operations == [
            {"op": "replace", "path": "/input", "value": "h2"}
        ]
        assert device._state["input"] == "h2"
        assert device.current_source == "Streaming"
        assert device.get_sensor_value("input") == "Streaming"

        updates = []
        selector = SimpleNamespace(
            _device=device,
            _get_options=lambda: device.source_list,
            _get_current=lambda: device.current_source,
            update=lambda values: updates.append(values),
        )
        await HTP1Select.sync_state(selector)
        from ucapi.select import Attributes

        assert updates[-1][Attributes.CURRENT_OPTION] == "Streaming"
        assert updates[-1][Attributes.OPTIONS] == device.source_list

    asyncio.run(exercise())


def test_input_select_rejects_source_not_in_current_eligible_options():
    async def exercise():
        device = make_device()
        entity = SimpleNamespace(
            _device=device,
            name="Input",
            _get_options=lambda: device.source_list,
            _command_fn=device.select_source,
        )

        status = await HTP1Select._handle_command(
            entity, entity, SelectCommands.SELECT_OPTION, {"option": "Hidden Input"}
        )

        assert status == StatusCodes.BAD_REQUEST
        assert device._ws.messages == []

    asyncio.run(exercise())
