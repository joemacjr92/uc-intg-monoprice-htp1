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



def test_addon_inputs_are_not_exposed_or_selectable():
    async def exercise():
        device = HTP1Device(
            HTP1Config("test", "Test HTP-1", "127.0.0.1"),
            loop=asyncio.get_running_loop(),
        )
        device._state = {
            "input": "addon_source",
            "inputs": {
                "hdmi1": {"label": "Movies", "visible": True},
                "hdmi2": {"label": "Hidden HDMI", "visible": False},
                "addon_source": {
                    "label": "Addon Player",
                    "visible": True,
                    "addon": "example-player",
                },
            },
        }
        device._parse_inputs()
        assert device.source_list == ["Movies"]
        # Keep reporting the currently active input, even if it is an
        # add-on-owned source that must not be manually selected.
        assert device.current_source == "Addon Player"

        sent = []

        async def capture(operations):
            sent.append(operations)
            return True

        device._send_transaction = capture
        assert not await device.select_source("Addon Player")
        assert not await device.select_source("Hidden HDMI")
        assert await device.select_source("Movies")
        assert sent == [[
            {"op": "replace", "path": "/input", "value": "hdmi1"}
        ]]

    asyncio.run(exercise())


def test_seat_shaker_trim_enforces_documented_hardware_bounds():
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
        assert await device.set_ss_trim(-24)
        assert await device.set_ss_trim(6)
        assert len(sent) == 2
        assert not await device.set_ss_trim(-25)
        assert not await device.set_ss_trim(7)
        for value in (True, 1.5, "0", None):
            assert not await device.set_ss_trim(value)
        assert len(sent) == 2

    asyncio.run(exercise())


def test_beq_forces_pre_placement_and_only_writes_lfe_path():
    async def exercise():
        device = HTP1Device(
            HTP1Config("test", "Test HTP-1", "127.0.0.1"),
            loop=asyncio.get_running_loop(),
        )
        channels = {
            name: {"Fc": 100, "gaindB": 0, "Q": 1, "FilterType": 0}
            for name in ("sub1", "sub2", "sub3")
        }
        device._state = {
            "peq": {
                "location": "post",
                "peqsw": False,
                "slots": [{"channels": channels} for _ in range(16)],
            },
            "speakers": {"groups": {
                "sub1": {"present": True},
                "sub2": {"present": True},
                "sub3": {"present": True},
            }},
        }
        sent = []

        async def capture(operations):
            sent.append(operations)
            return True

        device._send_transaction = capture
        assert await device.load_beq(
            "Pre-only BEQ",
            [{"type": "PeakingEQ", "freq": 30, "gain": 4, "q": 1}],
        )
        operations = sent[0]
        assert {"op": "replace", "path": "/peq/location", "value": "pre"} in operations
        assert {
            "op": "replace",
            "path": "/peq/slots/0/channels/sub1/Fc",
            "value": 30,
        } in operations
        assert {
            "op": "add",
            "path": "/peq/slots/0/channels/sub1/beq",
            "value": True,
        } in operations
        assert not any(
            "/channels/sub2/" in op["path"] or "/channels/sub3/" in op["path"]
            for op in operations
            if op["op"] in ("add", "replace")
        )

    asyncio.run(exercise())


def test_beq_rejects_unknown_peq_placement_without_sending():
    async def exercise():
        device = HTP1Device(
            HTP1Config("test", "Test HTP-1", "127.0.0.1"),
            loop=asyncio.get_running_loop(),
        )
        device._state = {
            "peq": {
                "peqsw": False,
                "slots": [{
                    "channels": {
                        "sub1": {"Fc": 100, "gaindB": 0, "Q": 1, "FilterType": 0}
                    }
                }],
            }
        }
        sent = []

        async def capture(operations):
            sent.append(operations)
            return True

        device._send_transaction = capture
        assert not await device.load_beq(
            "Unknown placement",
            [{"freq": 30, "gain": 4, "q": 1}],
        )
        assert sent == []

    asyncio.run(exercise())


def test_catalogue_entry_locks_are_removed_after_requests(monkeypatch):
    from collections import OrderedDict
    from intg_monoprice_htp1 import browser

    monkeypatch.setattr(browser, "_entry_cache", OrderedDict())
    monkeypatch.setattr(browser, "_entry_locks", {})
    monkeypatch.setattr(browser, "_manifest", {"version": "0123456789abcdef"})

    async def load_index():
        return True

    async def fetch(version, key):
        await asyncio.sleep(0)
        return {
            "title": key,
            "underlying": key,
            "filters": [{"type": "PeakingEQ", "freq": 100, "gain": 1, "q": 1}],
        }

    monkeypatch.setattr(browser, "_load_index", load_index)
    monkeypatch.setattr(browser, "_fetch_entry_payload", fetch)

    async def exercise():
        keys = [f"{index:016x}" for index in range(100)]
        results = await asyncio.gather(
            *(browser.get_beq_entry(key) for key in keys)
        )
        assert all(result is not None for result in results)
        assert len(browser._entry_cache) <= browser.ENTRY_CACHE_MAX
        assert browser._entry_locks == {}

    asyncio.run(exercise())
