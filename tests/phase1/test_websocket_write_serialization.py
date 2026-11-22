"""Concurrency tests for persistent HTP-1 WebSocket writes."""

import asyncio

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device


def test_concurrent_websocket_writes_are_serialized():
    async def exercise():
        device = HTP1Device(
            HTP1Config("test", "Test HTP-1", "127.0.0.1"),
            loop=asyncio.get_running_loop(),
        )

        class FakeWebSocket:
            def __init__(self):
                self.active_sends = 0
                self.max_active_sends = 0
                self.messages = []

            async def send(self, message):
                self.active_sends += 1
                self.max_active_sends = max(
                    self.max_active_sends, self.active_sends
                )
                try:
                    # Yield while a write is in progress. Without the shared
                    # lock, concurrent callers overlap in this section.
                    await asyncio.sleep(0)
                    self.messages.append(message)
                finally:
                    self.active_sends -= 1

        websocket = FakeWebSocket()
        device._ws = websocket
        device._is_connected = True
        messages = [f"command-{index}" for index in range(20)]

        results = await asyncio.gather(
            *(device.send_message(message) for message in messages)
        )

        assert results == [True] * len(messages)
        assert websocket.max_active_sends == 1
        assert websocket.messages == messages
        assert websocket.active_sends == 0

    asyncio.run(exercise())


def test_send_failure_releases_lock_for_later_writes():
    async def exercise():
        device = HTP1Device(
            HTP1Config("test", "Test HTP-1", "127.0.0.1"),
            loop=asyncio.get_running_loop(),
        )

        class FakeWebSocket:
            def __init__(self):
                self.calls = 0

            async def send(self, message):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("simulated write failure")

        websocket = FakeWebSocket()
        device._ws = websocket
        device._is_connected = True

        assert await device.send_message("first") is False
        assert await device.send_message("second") is True
        assert websocket.calls == 2

    asyncio.run(exercise())


def test_disconnected_device_does_not_attempt_websocket_write():
    async def exercise():
        device = HTP1Device(
            HTP1Config("test", "Test HTP-1", "127.0.0.1"),
            loop=asyncio.get_running_loop(),
        )

        class FakeWebSocket:
            def __init__(self):
                self.calls = 0

            async def send(self, message):
                self.calls += 1

        websocket = FakeWebSocket()
        device._ws = websocket
        device._is_connected = False

        assert await device.send_message("not-sent") is False
        assert websocket.calls == 0

    asyncio.run(exercise())


def test_volume_step_controls_reject_malformed_receiver_values():
    async def exercise():
        device = HTP1Device(
            HTP1Config("test", "Test HTP-1", "127.0.0.1"),
            loop=asyncio.get_running_loop(),
        )
        sent = []

        async def capture(operations):
            sent.append(operations)
            return True

        device._send_transaction = capture
        device.vph = 12
        device.vpl = -80
        device.zp = 0
        for bad_value in (True, "0", None, float("nan"), float("inf")):
            device._state = {"volume": bad_value}
            assert not await device.volume_up()
            assert not await device.volume_down()
        assert sent == []

    asyncio.run(exercise())


def test_all_entity_types_report_unavailable_when_device_disconnects():
    from intg_monoprice_htp1.media_player import HTP1MediaPlayer
    from intg_monoprice_htp1.remote import HTP1Remote
    from intg_monoprice_htp1.sensor import HTP1Sensor
    from intg_monoprice_htp1.selector import HTP1Select
    from ucapi.media_player import Attributes as MediaAttributes, States as MediaStates
    from ucapi.remote import Attributes as RemoteAttributes, States as RemoteStates
    from ucapi.sensor import Attributes as SensorAttributes, States as SensorStates
    from ucapi.select import Attributes as SelectAttributes, States as SelectStates

    class Device:
        is_connected = False

    device = Device()

    async def exercise():
        player = HTP1MediaPlayer.__new__(HTP1MediaPlayer)
        player._device = device
        player_updates = []
        player.update = lambda values: player_updates.append(values)
        await player.sync_state()
        assert player_updates == [{MediaAttributes.STATE: MediaStates.UNAVAILABLE}]

        remote = HTP1Remote.__new__(HTP1Remote)
        remote._device = device
        remote_updates = []
        remote.update = lambda values: remote_updates.append(values)
        await remote.sync_state()
        assert remote_updates == [{RemoteAttributes.STATE: RemoteStates.UNAVAILABLE}]

        sensor = HTP1Sensor.__new__(HTP1Sensor)
        sensor._device = device
        sensor._sensor_key = "volume"
        sensor_updates = []
        sensor.update = lambda values: sensor_updates.append(values)
        await sensor.sync_state()
        assert sensor_updates == [{SensorAttributes.STATE: SensorStates.UNAVAILABLE}]

        selector = HTP1Select.__new__(HTP1Select)
        selector._device = device
        selector_updates = []
        selector.update = lambda values: selector_updates.append(values)
        await selector.sync_state()
        assert selector_updates == [{SelectAttributes.STATE: SelectStates.UNAVAILABLE}]

    asyncio.run(exercise())
