"""Connected-state synchronization tests for HTP-1 entities."""

import asyncio
import json
from pathlib import Path

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device
from intg_monoprice_htp1.media_player import HTP1MediaPlayer
from intg_monoprice_htp1.remote import HTP1Remote
from intg_monoprice_htp1.sensor import HTP1Sensor
from intg_monoprice_htp1.selector import HTP1Select
from ucapi.media_player import Attributes as MediaAttributes, States as MediaStates
from ucapi.remote import Attributes as RemoteAttributes, States as RemoteStates
from ucapi.sensor import Attributes as SensorAttributes, States as SensorStates
from ucapi.select import Attributes as SelectAttributes, States as SelectStates


FIXTURE = Path(__file__).parents[1] / "fixtures" / "htp1_full_mso.json"


def make_connected_device():
    device = HTP1Device(
        HTP1Config("sync-test", "Sync Test HTP-1", "127.0.0.1"),
        loop=asyncio.get_running_loop(),
    )
    device._is_connected = True
    device._state = json.loads(FIXTURE.read_text(encoding="utf-8"))
    device._parse_state()
    return device


def test_connected_entities_sync_from_full_captured_mso_state():
    async def exercise():
        device = make_connected_device()

        player = HTP1MediaPlayer.__new__(HTP1MediaPlayer)
        player._device = device
        player_updates = []
        player.update = lambda values: player_updates.append(values)
        await player.sync_state()

        player_state = player_updates[-1]
        assert player_state[MediaAttributes.STATE] == MediaStates.ON
        assert player_state[MediaAttributes.VOLUME] == -20
        assert player_state[MediaAttributes.MUTED] is False
        assert player_state[MediaAttributes.SOURCE] == "Movies"
        assert player_state[MediaAttributes.SOURCE_LIST] == [
            "Movies", "Streaming", "Disc", "HTPC"
        ]
        assert player_state[MediaAttributes.SOUND_MODE] == "NATIVE"
        assert player_state[MediaAttributes.SOUND_MODE_LIST]

        remote = HTP1Remote.__new__(HTP1Remote)
        remote._device = device
        remote_updates = []
        remote.update = lambda values: remote_updates.append(values)
        await remote.sync_state()
        assert remote_updates == [{RemoteAttributes.STATE: RemoteStates.ON}]

        sensor = HTP1Sensor.__new__(HTP1Sensor)
        sensor._device = device
        sensor._sensor_key = "volume"
        sensor_updates = []
        sensor.update = lambda values: sensor_updates.append(values)
        await sensor.sync_state()
        assert sensor_updates == [{
            SensorAttributes.STATE: SensorStates.ON,
            SensorAttributes.VALUE: "-20",
        }]

        selector = HTP1Select.__new__(HTP1Select)
        selector._device = device
        selector._get_options = lambda: device.source_list
        selector._get_current = lambda: device.current_source
        selector_updates = []
        selector.update = lambda values: selector_updates.append(values)
        await selector.sync_state()
        assert selector_updates == [{
            SelectAttributes.STATE: SelectStates.ON,
            SelectAttributes.OPTIONS: ["Movies", "Streaming", "Disc", "HTPC"],
            SelectAttributes.CURRENT_OPTION: "Movies",
        }]

    asyncio.run(exercise())


def test_connected_entities_sync_safely_when_optional_state_is_missing():
    async def exercise():
        device = make_connected_device()
        device._state = {"powerIsOn": False, "muted": False, "volume": -25}
        device._parse_state()

        player = HTP1MediaPlayer.__new__(HTP1MediaPlayer)
        player._device = device
        player_updates = []
        player.update = lambda values: player_updates.append(values)
        await player.sync_state()
        assert player_updates[-1][MediaAttributes.STATE] == MediaStates.OFF
        assert player_updates[-1][MediaAttributes.SOURCE] == ""
        assert player_updates[-1][MediaAttributes.SOURCE_LIST] == []

        sensor = HTP1Sensor.__new__(HTP1Sensor)
        sensor._device = device
        sensor._sensor_key = "not_present"
        sensor_updates = []
        sensor.update = lambda values: sensor_updates.append(values)
        await sensor.sync_state()
        assert sensor_updates == [{
            SensorAttributes.STATE: SensorStates.ON,
            SensorAttributes.VALUE: "Unknown",
        }]

        selector = HTP1Select.__new__(HTP1Select)
        selector._device = device
        selector._get_options = lambda: device.source_list
        selector._get_current = lambda: device.current_source
        selector_updates = []
        selector.update = lambda values: selector_updates.append(values)
        await selector.sync_state()
        assert selector_updates == [{
            SelectAttributes.STATE: SelectStates.ON,
            SelectAttributes.OPTIONS: [],
            SelectAttributes.CURRENT_OPTION: "",
        }]

    asyncio.run(exercise())
