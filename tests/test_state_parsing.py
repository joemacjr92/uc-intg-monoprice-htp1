import asyncio
import json

import pytest

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device


@pytest.fixture
def device():
    loop = asyncio.new_event_loop()
    instance = HTP1Device(
        HTP1Config("test", "Test HTP-1", "127.0.0.1"),
        loop=loop,
    )
    yield instance
    loop.close()


def receiver_state(**overrides):
    state = {
        "powerIsOn": True,
        "muted": True,
        "volume": -24,
        "cal": {
            "zeroPoint": -10,
            "vpl": -80,
            "vph": 12,
            "diracactive": "on",
            "currentdiracslot": 1,
            "slots": [
                {"valid": True, "name": "Movie"},
                {"valid": True, "name": "Music"},
                {"valid": False, "name": "Unused"},
                {"valid": True, "name": "Movie"},
            ],
        },
        "inputs": {
            "hdmi1": {"label": "Apple TV", "visible": True},
            "hdmi2": {"label": "Game", "visible": True},
            "hidden": {"label": "Hidden", "visible": False},
            "fallback": {"visible": True},
        },
        "input": "hdmi1",
        "upmix": {"select": "dolby"},
        "status": {
            "DECSourceProgram": "Dolby TrueHD",
            "DECProgramFormat": "7.1",
            "SurroundMode": "DTS Neural:X",
            "ENCListeningFormat": "7.1.4",
        },
        "videostat": {
            "VideoResolution": "3840x2160",
            "HDRstatus": "HDR10",
            "VideoColorSpace": "YCbCr",
            "VideoMode": "2160p",
            "VideoBitDepth": "10bit",
        },
        "peq": {"peqsw": True, "location": "pre", "beqActive": "Example BEQ"},
        "shaker": {
            "mute": "on",
            "activePreset": 2,
            "presets": {"2": {"trim": 4}},
        },
        "loudness": "on",
        "night": "off",
    }
    state.update(overrides)
    return state


def test_parses_power_volume_mute_inputs_modes_and_audio_formats(device):
    device._state = receiver_state()

    device._parse_state()

    assert device.power is True
    assert device.muted is True
    # Display volume is offset from the receiver's raw volume by zeroPoint.
    assert device.volume_db == -14
    assert device.zp == -10
    assert device.vpl == -80
    assert device.vph == 12

    assert device.current_source == "Apple TV"
    assert device.source_list == ["Apple TV", "Game"]
    assert device.surround_mode == "dolby"
    assert device.sound_mode_display == "DOLBY SURROUND"
    assert device.audio_format == "7.1 Dolby TrueHD"
    assert device.output_audio_format == "7.1.4 DTS Neural:X"
    assert device.video_mode == "3840x2160 HDR10 YCbCr 2160p 10bit"

    assert device.get_sensor_value("input") == "Apple TV"
    assert device.get_sensor_value("volume") == "-14"
    assert device.get_sensor_value("mute") == "On"
    assert device.get_sensor_value("peq") == "On"
    assert device.get_sensor_value("beq_active") == "Example BEQ"
    assert device.get_sensor_value("loudness") == "On"
    assert device.get_sensor_value("night_mode") == "Off"


def test_dirac_slot_parsing_filters_invalid_slots_and_handles_modes(device):
    state = receiver_state()
    device._state = state

    device._parse_state()
    assert device.slot_names == ["Movie", "Music", "Movie"]
    assert device._slot_index == {"Movie": 0, "Music": 1}
    assert device.dirac_slot_name == "Music"

    state["cal"]["diracactive"] = "bypass"
    device._parse_state()
    assert device.dirac_slot_name == "Dirac Bypass"

    state["cal"]["diracactive"] = "off"
    device._parse_state()
    assert device.dirac_slot_name == "Dirac Off"

    state["cal"]["diracactive"] = "on"
    state["cal"]["currentdiracslot"] = 99
    device._parse_state()
    assert device.dirac_slot_name == "Dirac Off"


def test_seat_shaker_preset_trim_and_mute_parsing(device):
    device._state = receiver_state()
    device._parse_state()

    assert device.ss_mute == "on"
    assert device.ss_preset == 3
    assert device.ss_trim == 4
    assert device.get_sensor_value("ss_mute") == "On"
    assert device.get_sensor_value("ss_preset") == 3
    assert device.get_sensor_value("ss_trim") == "4"


def test_mso_and_incremental_patch_update_power_volume_mute_and_input(device):
    async def exercise():
        device.push_update = lambda: None
        await device.handle_message("mso " + json.dumps(receiver_state()))
        assert device.power is True
        assert device.volume_db == -14
        assert device.current_source == "Apple TV"

        await device.handle_message(
            'msoupdate [{"op":"replace","path":"/powerIsOn","value":false},'
            '{"op":"replace","path":"/muted","value":false},'
            '{"op":"replace","path":"/volume","value":-30},'
            '{"op":"replace","path":"/input","value":"hdmi2"}]'
        )
        assert device.power is False
        assert device.muted is False
        assert device.volume_db == -20
        assert device.current_source == "Game"

    device._loop.run_until_complete(exercise())


def test_malformed_or_missing_state_sections_reset_to_safe_defaults(device):
    device._state = receiver_state()
    device._parse_state()

    device._state = {
        "powerIsOn": "yes",
        "muted": 1,
        "volume": float("inf"),
        "cal": [],
        "inputs": [],
        "upmix": [],
        "status": [],
        "videostat": [],
        "peq": [],
        "shaker": [],
    }
    device._parse_state()

    assert device.power is False
    assert device.muted is False
    assert device.volume_db == 0
    assert device.current_source == ""
    assert device.source_list == []
    assert device.slot_names == []
    assert device._slot_index == {}
    assert device.dirac_slot_name == "Dirac Off"
    assert device.sound_mode_display == ""
    assert device.audio_format == "none"
    assert device.output_audio_format == ""
    assert device.video_mode == "-----"
