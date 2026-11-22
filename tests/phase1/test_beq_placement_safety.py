"""Regression tests for BEQ PEQ-placement safety and browser availability."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from intg_monoprice_htp1 import browser
from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device


BEQ_FIXTURE = Path(__file__).parents[1] / "fixtures" / "mso_beq_pre_active.json"


class RecordingWebSocket:
    def __init__(self):
        self.messages = []

    async def send(self, message):
        self.messages.append(message)


def make_device(location):
    device = HTP1Device(
        HTP1Config("beq-placement", "BEQ Placement Test", "127.0.0.1"),
        loop=asyncio.get_running_loop(),
    )
    device._is_connected = True
    device._state = json.loads(BEQ_FIXTURE.read_text(encoding="utf-8"))
    device._state["peq"]["location"] = location
    device._parse_state()
    device._ws = RecordingWebSocket()
    return device


def _browser_device(location, active=""):
    return SimpleNamespace(
        name="BEQ Placement Test",
        beq_active=active,
        _state={"peq": {"location": location}},
    )


def _browse_options(media_type="root", media_id=None):
    return SimpleNamespace(media_type=media_type, media_id=media_id, paging=None)


def _assert_unavailable_item(result):
    items = result.media.items
    assert len(items) == 1
    item = items[0]
    assert item.title == "BEQ Unavailable"
    assert item.subtitle == (
        "BEQ loading requires PEQ Location to be set to Pre-Dirac."
    )
    assert item.can_play is False
    assert item.can_browse is False
    assert result.media.can_search is False


def test_beq_load_in_pre_placement_never_writes_peq_location():
    async def exercise():
        device = make_device("pre")
        assert await device.load_beq(
            "Pre placement test",
            [{"type": "PeakingEQ", "freq": 25, "gain": 3.5, "q": 1.2}],
        )

        message = device._ws.messages[-1]
        assert message.startswith("changemso ")
        operations = json.loads(message.partition(" ")[2])
        assert not any(operation.get("path") == "/peq/location" for operation in operations)
        assert any(operation.get("path") == "/peq/beqActive" for operation in operations)
        assert all(
            "/sub1/" in operation.get("path", "")
            for operation in operations
            if "/channels/" in operation.get("path", "")
        )

    asyncio.run(exercise())


def test_beq_load_in_post_placement_is_rejected_without_any_write():
    async def exercise():
        device = make_device("post")
        assert not await device.load_beq(
            "Post placement test",
            [{"type": "PeakingEQ", "freq": 25, "gain": 3.5, "q": 1.2}],
        )
        assert device._ws.messages == []

    asyncio.run(exercise())


@pytest.mark.parametrize("location", [None, "unknown", ""])
def test_beq_load_with_unknown_placement_fails_closed_without_write(location):
    async def exercise():
        device = make_device(location)
        assert not await device.load_beq(
            "Unknown placement test",
            [{"type": "PeakingEQ", "freq": 25, "gain": 3.5, "q": 1.2}],
        )
        assert device._ws.messages == []

    asyncio.run(exercise())


def test_beq_root_browse_shows_catalogue_when_peq_is_pre():
    async def exercise():
        result = await browser.browse(
            _browser_device("pre"), _browse_options()
        )
        assert [item.title for item in result.media.items] == ["BEQ Catalogue"]
        assert result.media.items[0].can_browse is True

    asyncio.run(exercise())


@pytest.mark.parametrize("location", ["post", None, "unknown", ""])
@pytest.mark.parametrize(
    ("media_type", "media_id"),
    [("root", None), ("beq_categories", None), ("beq_category", "film")],
)
def test_beq_browse_with_non_pre_placement_shows_only_unavailable_item(
    monkeypatch, location, media_type, media_id
):
    async def exercise():
        async def index_must_not_load():
            raise AssertionError("BEQ catalogue must not load unless PEQ is Pre")

        monkeypatch.setattr(browser, "_load_index", index_must_not_load)
        result = await browser.browse(
            _browser_device(location),
            _browse_options(media_type=media_type, media_id=media_id),
        )
        _assert_unavailable_item(result)

    asyncio.run(exercise())



def test_unavailable_beq_browser_keeps_existing_clear_action_available(monkeypatch):
    async def exercise():
        async def index_must_not_load():
            raise AssertionError("BEQ catalogue must not load unless PEQ is Pre")

        monkeypatch.setattr(browser, "_load_index", index_must_not_load)
        result = await browser.browse(
            _browser_device("post", active="Previously loaded BEQ"),
            _browse_options(),
        )

        assert [item.title for item in result.media.items] == [
            "BEQ Unavailable",
            "Clear BEQ: Previously loaded BEQ",
        ]
        assert result.media.items[0].can_play is False
        assert result.media.items[1].can_play is True
        assert result.media.can_search is False

    asyncio.run(exercise())
