"""Opt-in compatibility smoke test against Mase's published GitHub Pages catalogue.

Run with HTP1_LIVE_BEQ_CATALOGUE=1. Normal unit-test runs remain deterministic
and do not depend on GitHub Pages availability.
"""
import asyncio
import os
from collections import OrderedDict

import pytest

from intg_monoprice_htp1 import browser


@pytest.mark.skipif(
    os.environ.get("HTP1_LIVE_BEQ_CATALOGUE") != "1",
    reason="set HTP1_LIVE_BEQ_CATALOGUE=1 to check the live published catalogue",
)
def test_published_catalogue_matches_browser_contract(monkeypatch):
    monkeypatch.setattr(browser, "_index", None)
    monkeypatch.setattr(browser, "_manifest", None)
    monkeypatch.setattr(browser, "_index_loaded_at", 0.0)
    monkeypatch.setattr(browser, "_index_lock", asyncio.Lock())
    monkeypatch.setattr(browser, "_entry_cache", OrderedDict())
    monkeypatch.setattr(browser, "_entry_locks", {})

    async def exercise():
        assert await browser._load_index(), (
            "Could not load or validate Mase's published BEQ manifest/index"
        )
        assert browser._manifest is not None
        assert browser._index is not None

        manifest = browser._manifest
        index = browser._index
        assert manifest["index"] == f'{manifest["version"]}/index.json'
        assert manifest["entry_count"] == len(index["entries"])
        assert index["version"] == manifest["version"]
        assert index["entries"], "Published catalogue contains no entries"

        # Fetch a real versioned payload, exercising the exact URL and payload
        # shape used when the integration applies a selected BEQ.
        entry = index["entries"][0]
        payload = await browser.get_beq_entry(entry["id"])
        assert payload is not None, f'Could not fetch published BEQ entry {entry["id"]}'
        assert isinstance(payload.get("title"), str) and payload["title"]
        assert isinstance(payload.get("underlying"), str)
        assert isinstance(payload.get("filters"), list) and payload["filters"]

    asyncio.run(exercise())
