"""Phase 1 correctness and safety regression tests."""

import asyncio
import json
from collections import OrderedDict
from pathlib import Path

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device


BEQ_FIXTURE = Path(__file__).parents[1] / "fixtures" / "mso_beq_pre_active.json"


def make_device():
    return HTP1Device(HTP1Config("phase1", "Phase 1 HTP-1", "127.0.0.1"))


def test_addon_and_hidden_inputs_are_not_offered_or_selectable():
    async def exercise():
        device = make_device()
        device._state = {
            "input": "addon_player",
            "inputs": {
                "hdmi1": {"label": "Movies", "visible": True},
                "addon_player": {"label": "Streaming App", "visible": True, "addon": True},
                "hidden": {"label": "Hidden Input", "visible": False},
                "malformed": ["not", "an", "input"],
                "legacy": {"label": "Legacy Add-on", "visible": True, "addon": "audio"},
            },
        }
        device._parse_inputs()

        # Keep the actual active source visible as current state, but do not
        # offer add-on-owned sources as manually selectable inputs.
        assert device.current_source == "Streaming App"
        assert device.source_list == ["Movies"]

        sent = []

        async def capture(operations):
            sent.append(operations)
            return True

        device._send_transaction = capture
        assert not await device.select_source("Streaming App")
        assert not await device.select_source("Hidden Input")
        assert await device.select_source("Movies")
        assert sent == [[{"op": "replace", "path": "/input", "value": "hdmi1"}]]

    asyncio.run(exercise())


def test_beq_post_peq_is_rejected_without_writes():
    async def exercise():
        device = make_device()
        state = json.loads(BEQ_FIXTURE.read_text(encoding="utf-8"))
        state["peq"]["location"] = "post"
        state["peq"]["peqsw"] = False
        device._state = state
        sent = []

        async def capture(operations):
            sent.append(operations)
            return True

        device._send_transaction = capture
        filters = [
            {"type": "PeakingEQ", "freq": 25, "gain": 3.5, "q": 1.2},
            {"type": "LowShelf", "freq": 30, "gain": -2.0, "q": 0.8},
        ]

        assert not await device.load_beq("Phase 1 test BEQ", filters)
        assert sent == []
        assert device.beq_active == ""

    asyncio.run(exercise())


def test_beq_preflight_failure_does_not_send_partial_or_clear_existing_beq():
    async def exercise():
        device = make_device()
        state = json.loads(BEQ_FIXTURE.read_text(encoding="utf-8"))
        state["peq"]["slots"] = state["peq"]["slots"][:1]
        device._state = state
        sent = []

        async def capture(operations):
            sent.append(operations)
            return True

        device._send_transaction = capture
        # The fixture has only one available slot after this truncation, so
        # asking for two filters must fail before any transaction is sent.
        assert not await device.load_beq(
            "Cannot fit", [
                {"type": "PeakingEQ", "freq": 25, "gain": 3, "q": 1},
                {"type": "PeakingEQ", "freq": 30, "gain": 2, "q": 1},
            ]
        )
        assert sent == []
        assert device._state["peq"]["beqActive"] == state["peq"]["beqActive"]

    asyncio.run(exercise())


def test_seat_shaker_trim_accepts_hardware_bounds_and_rejects_outside():
    async def exercise():
        device = make_device()
        sent = []

        async def capture(operations):
            sent.append(operations)
            return True

        device._send_transaction = capture
        assert await device.set_ss_trim(-24)
        assert await device.set_ss_trim(6)
        assert sent == [
            [{"op": "replace", "path": "/shaker/trim", "value": -24}],
            [{"op": "replace", "path": "/shaker/trim", "value": 6}],
        ]

        before = len(sent)
        for invalid in (-25, 7, True, 6.5, "0", None):
            assert not await device.set_ss_trim(invalid)
        assert len(sent) == before

    asyncio.run(exercise())


def test_beq_entry_lock_registry_is_reclaimed_after_many_distinct_requests(monkeypatch):
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
        keys = [f"{index:016x}" for index in range(40)]
        results = await asyncio.gather(*(browser.get_beq_entry(key) for key in keys))
        assert all(result is not None for result in results)
        assert len(browser._entry_cache) <= browser.ENTRY_CACHE_MAX
        assert browser._entry_locks == {}

    asyncio.run(exercise())


def test_beq_entry_lock_registry_is_reclaimed_when_fetch_is_cancelled(monkeypatch):
    import pytest
    from intg_monoprice_htp1 import browser

    monkeypatch.setattr(browser, "_entry_cache", OrderedDict())
    monkeypatch.setattr(browser, "_entry_locks", {})
    monkeypatch.setattr(browser, "_manifest", {"version": "0123456789abcdef"})

    async def exercise():
        started = asyncio.Event()

        async def load_index():
            return True

        async def fetch(version, key):
            started.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(browser, "_load_index", load_index)
        monkeypatch.setattr(browser, "_fetch_entry_payload", fetch)
        task = asyncio.create_task(browser.get_beq_entry("0123456789abcdef"))
        await started.wait()
        assert browser._entry_locks
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            pytest.fail("cancelled BEQ fetch unexpectedly completed")
        assert browser._entry_locks == {}

    asyncio.run(exercise())
