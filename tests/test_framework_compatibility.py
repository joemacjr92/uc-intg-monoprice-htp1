def test_pinned_ucapi_and_framework_imports():
    # Smoke-test the actual runtime dependencies and the integration's
    # framework-backed classes, not just the standalone catalogue builder.
    from ucapi import StatusCodes
    from ucapi_framework import BaseIntegrationDriver, WebSocketDevice
    from intg_monoprice_htp1.device import HTP1Device
    from intg_monoprice_htp1.driver import HTP1Driver
    from intg_monoprice_htp1.media_player import HTP1MediaPlayer

    assert StatusCodes.OK is not None
    assert issubclass(HTP1Device, WebSocketDevice)
    assert issubclass(HTP1Driver, BaseIntegrationDriver)
    assert HTP1MediaPlayer is not None


def test_static_entities_do_not_wait_for_receiver_connection():
    import asyncio

    async def check():
        from intg_monoprice_htp1.driver import HTP1Driver

        driver = HTP1Driver()
        # ucapi-framework has no public accessor for this constructor option.
        assert driver._require_connection_before_registry is False

    asyncio.run(check())


def test_connection_loss_clears_stale_state_and_notifies_entities():
    import asyncio
    from intg_monoprice_htp1.config import HTP1Config
    from intg_monoprice_htp1.device import HTP1Device

    async def exercise():
        device = HTP1Device(HTP1Config("test", "Test HTP-1", "127.0.0.1"))
        device._is_connected = True
        device._state = {"powerIsOn": True}
        device._sensor_data = {"volume": "-20", "input": "HDMI 1"}
        device._state_ready.set()
        updates = []
        device.push_update = lambda: updates.append(True)

        device._on_connection_lost()

        assert device.is_connected is False
        assert device._state is None
        assert device._sensor_data == {}
        assert not device._state_ready.is_set()
        assert updates == [True]

    asyncio.run(exercise())


def test_invalid_full_state_payload_is_ignored():
    import asyncio
    from intg_monoprice_htp1.config import HTP1Config
    from intg_monoprice_htp1.device import HTP1Device

    async def exercise():
        device = HTP1Device(HTP1Config("test", "Test HTP-1", "127.0.0.1"))
        await device.handle_message("mso []")
        assert device._state is None
        assert not device._state_ready.is_set()

    asyncio.run(exercise())


def test_malformed_patch_entries_do_not_abort_valid_updates():
    import asyncio
    from intg_monoprice_htp1.config import HTP1Config
    from intg_monoprice_htp1.device import HTP1Device

    async def exercise():
        device = HTP1Device(HTP1Config("test", "Test HTP-1", "127.0.0.1"))
        device._state = {"powerIsOn": False}
        updates = []
        device.push_update = lambda: updates.append(True)

        await device.handle_message(
            'msoupdate [42, {"op": "replace", "path": null, "value": true}, '
            '{"op": "replace", "path": "/powerIsOn", "value": true}]'
        )

        assert device._state["powerIsOn"] is True
        assert updates == [True]

    asyncio.run(exercise())


def test_remote_repeat_and_delay_validation():
    from intg_monoprice_htp1.remote import HTP1Remote

    assert HTP1Remote._repeat_delay(None) == (1, 0.0)
    assert HTP1Remote._repeat_delay({"repeat": 3, "delay": 250}) == (3, 0.25)
    assert HTP1Remote._repeat_delay({"repeat": 0}) is None
    assert HTP1Remote._repeat_delay({"repeat": 21}) is None
    assert HTP1Remote._repeat_delay({"repeat": True}) is None
    assert HTP1Remote._repeat_delay({"delay": -1}) is None
    assert HTP1Remote._repeat_delay({"delay": 5001}) is None
    assert HTP1Remote._repeat_delay({"delay": "100"}) is None


def test_device_command_validation_and_requested_mute_state():
    import asyncio
    from intg_monoprice_htp1.config import HTP1Config
    from intg_monoprice_htp1.device import HTP1Device

    async def exercise():
        device = HTP1Device(HTP1Config("test", "Test HTP-1", "127.0.0.1"))
        sent = []

        async def capture(operations):
            sent.append(operations)
            return True

        device._send_transaction = capture

        assert await device.mute_toggle(True)
        assert sent[-1][0]["value"] is True

        assert await device.ss_mute_toggle(False)
        assert sent[-1][0]["value"] == "off"
        assert await device.ss_mute_toggle(True)
        assert sent[-1][0]["value"] == "on"

        assert await device.select_sound_mode("DIRECT")
        assert sent[-1][0]["value"] == "off"
        before = len(sent)
        assert not await device.select_sound_mode("not-a-mode")
        assert len(sent) == before

        device._state = {"shaker": {}}
        assert await device.select_ss_preset(0)
        assert await device.select_ss_preset(5)
        before = len(sent)
        assert not await device.select_ss_preset(6)
        assert not await device.select_ss_preset(-1)
        assert len(sent) == before

        assert not await device.send_http_command("not-hex")
        assert not await device.send_http_command("123")
        assert not await device.send_http_command("12345")

    asyncio.run(exercise())


def test_remote_rejects_unadvertised_commands_as_bad_request():
    from intg_monoprice_htp1.remote import HTP1Remote
    from ucapi import StatusCodes

    remote = HTP1Remote.__new__(HTP1Remote)
    remote.id = "remote.test"

    async def exercise():
        assert await remote._send_single("not-a-command") == StatusCodes.BAD_REQUEST

    import asyncio
    asyncio.run(exercise())



def test_select_commands_validate_advertised_options_and_connection():
    import asyncio
    from intg_monoprice_htp1.selector import HTP1Select
    from ucapi import StatusCodes
    from ucapi.select import Commands

    class Device:
        log_id = "test"
        is_connected = True

    device = Device()
    calls = []

    async def command(option):
        calls.append(option)
        return True

    # Avoid framework registration; exercise the command boundary directly.
    select = HTP1Select.__new__(HTP1Select)
    select._device = device
    select._get_options = lambda: ["Option A", "Option B"]
    select._command_fn = command
    select.name = "Test Select"

    async def exercise():
        assert await select._handle_command(
            select, Commands.SELECT_OPTION, {"option": "Option B"}
        ) == StatusCodes.OK
        assert calls == ["Option B"]
        assert await select._handle_command(
            select, Commands.SELECT_OPTION, {"option": "Not Advertised"}
        ) == StatusCodes.BAD_REQUEST
        assert await select._handle_command(
            select, Commands.SELECT_OPTION, {"option": 1}
        ) == StatusCodes.BAD_REQUEST
        assert calls == ["Option B"]

        device.is_connected = False
        assert await select._handle_command(
            select, Commands.SELECT_OPTION, {"option": "Option A"}
        ) == StatusCodes.SERVER_ERROR
        assert calls == ["Option B"]

    asyncio.run(exercise())
