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
