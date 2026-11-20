import asyncio
import time
from types import SimpleNamespace

from intg_monoprice_htp1 import browser


def _seed_index(monkeypatch):
    entries = [
        {"id": f"{index:016x}", "title": title, "author": "", "year": "2024",
         "audioTypes": [], "content_type": "film", "search_title": title.casefold()}
        for index, title in enumerate(["Alpha", "Alpine", "Beta"])
    ]
    monkeypatch.setattr(browser, "_index", {
        "entries": entries,
        "categories": {"film": [0, 1, 2]},
    })
    monkeypatch.setattr(browser, "_entries_by_id", {entry["id"]: entry for entry in entries})
    monkeypatch.setattr(browser, "_manifest", {"version": "0123456789abcdef"})
    monkeypatch.setattr(browser, "_index_loaded_at", time.monotonic())


def test_search_respects_requested_page_and_limit(monkeypatch):
    _seed_index(monkeypatch)
    options = SimpleNamespace(
        query="al",
        paging=SimpleNamespace(page=2, limit=1),
    )
    result = asyncio.run(browser.search(None, options))
    assert [item.title for item in result.media] == ["Alpine"]
    assert result.pagination.page == 2
    assert result.pagination.limit == 1
    assert result.pagination.count == 2


def test_category_browse_uses_precomputed_offsets_and_limit(monkeypatch):
    _seed_index(monkeypatch)
    result = asyncio.run(browser._browse_category("film", page=2, limit=1))
    assert [item.title for item in result.media.items] == ["Alpine"]
    assert result.pagination.page == 2
    assert result.pagination.limit == 1
    assert result.pagination.count == 3
