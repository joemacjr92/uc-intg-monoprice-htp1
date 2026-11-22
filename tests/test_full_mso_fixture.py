"""Integration parsing tests using the sanitized full HTP-1 MSO capture."""

import asyncio
import json
from pathlib import Path

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device


FIXTURE = Path(__file__).parent / "fixtures" / "htp1_full_mso.json"


def load_full_mso():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_sanitized_full_mso_fixture_is_valid_and_retains_real_device_sections():
    state = load_full_mso()

    # The full capture remains representative while identifying network and
    # device identity fields are removed or redacted.
    assert "hostip" not in state
    assert "ipInfo" not in state
    assert state["versions"]["SerialNumber"] == "REDACTED"
    assert state["mdns"]["hostname"] == "HTP1-REDACTED.local"

    assert state["volume"] == -27
    assert state["input"] == "h1"
    assert state["muted"] is False
    assert state["powerIsOn"] is True
    assert state["shaker"]["enabled"] is True
    assert state["shaker"]["trim"] == -3
    assert state["shaker"]["delay"] == 10
    assert state["shaker"]["lfegain"] == 10
    assert state["shaker"]["content"] == "lfe"
    assert len(state["cal"]["slots"]) == 6
    assert len(state["peq"]["slots"]) == 16
    assert isinstance(state["speakers"], dict)
    assert isinstance(state["speakers"]["mapping"], list)
    assert len(state["speakers"]["mapping"]) == 16


def test_full_mso_fixture_parses_into_device_state_and_sensors():
    loop = asyncio.new_event_loop()
    try:
        device = HTP1Device(
            HTP1Config("fixture", "Fixture HTP-1", "127.0.0.1"),
            loop=loop,
        )
        device._state = load_full_mso()

        device._parse_state()

        assert device.power is True
        assert device.muted is False
        assert device.volume_db == -20
        assert device.zp == -7
        assert device.vpl == -80
        assert device.vph == -14

        assert device.current_source == "Movies"
        assert device.source_list == ["Movies", "Streaming", "Disc", "HTPC"]
        assert device.surround_mode == "native"
        assert device.sound_mode_display == "NATIVE"
        assert device.audio_format == "Object Audio Dolby Digital Plus (ATMOS)"
        assert device.output_audio_format == "7.3.6h Native Dolby ATMOS"
        assert device.dirac_slot_name == "6 Point Tweaked"
        assert device.video_mode == "4k24Hz HDR10 BT2020 4:2:2"

        assert device.ss_mute == "off"
        assert device.ss_preset == 1
        assert device.ss_trim == -3

        assert device.get_sensor_value("input") == "Movies"
        assert device.get_sensor_value("volume") == "-20"
        assert device.get_sensor_value("mute") == "Off"
        assert device.get_sensor_value("peq") == "On"
        assert device.get_sensor_value("ss_trim") == "-3"
        assert device.get_sensor_value("dirac_slot") == "6 Point Tweaked"
    finally:
        loop.close()


def test_full_mso_message_and_incremental_update_keep_parsed_state_in_sync():
    loop = asyncio.new_event_loop()
    try:
        device = HTP1Device(
            HTP1Config("fixture", "Fixture HTP-1", "127.0.0.1"),
            loop=loop,
        )
        device.push_update = lambda: None
        state = load_full_mso()

        async def exercise():
            await device.handle_message("mso " + json.dumps(state))
            assert device.volume_db == -20
            assert device.current_source == "Movies"
            assert device.ss_trim == -3

            await device.handle_message(
                'msoupdate [{"op":"replace","path":"/volume","value":-30},'
                '{"op":"replace","path":"/input","value":"h2"},'
                '{"op":"replace","path":"/muted","value":true}]'
            )
            assert device.volume_db == -23
            assert device.current_source == "Streaming"
            assert device.muted is True

        loop.run_until_complete(exercise())
    finally:
        loop.close()
