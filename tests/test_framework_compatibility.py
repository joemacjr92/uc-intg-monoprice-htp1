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
