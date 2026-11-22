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
