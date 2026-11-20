"""
Memory-conscious BEQ media browser backed by the hosted compact catalogue.

The browse index contains metadata only. Individual filter payloads are fetched
only when a BEQ is selected and retained in a bounded in-memory LRU.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

import aiohttp

from ucapi import StatusCodes
from ucapi.api_definitions import Pagination
from ucapi.media_player import (
    BrowseMediaItem, BrowseOptions, BrowseResults, MediaClass,
    SearchMediaItem, SearchOptions, SearchResults,
)

if TYPE_CHECKING:
    from intg_monoprice_htp1.device import HTP1Device

_LOG = logging.getLogger(__name__)

CATALOGUE_BASE_URL = (
    "https://joemacjr92.github.io/uc-intg-monoprice-htp1/beq/"
)
ITEMS_PER_PAGE = 50
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20, connect=5, sock_read=15)
ENTRY_CACHE_MAX = 12
INDEX_CACHE_LIFE = 86400

_index: dict[str, Any] | None = None
_manifest: dict[str, Any] | None = None
_entries_by_id: dict[str, dict[str, Any]] = {}
_index_loaded_at: float = 0.0
_index_lock = asyncio.Lock()
_entry_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()


async def _get_json(url: str) -> Any:
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json(content_type=None)


async def _load_index() -> bool:
    """Load and validate the small index, retaining a prior good copy on errors."""
    global _index, _manifest
    if _index is not None:
        return True

    async with _index_lock:
        if _index is not None:
            return True
        try:
            manifest = await _get_json(CATALOGUE_BASE_URL + "manifest.json")
            if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
                raise ValueError("unsupported BEQ manifest schema")
            version = manifest.get("version")
            index_path = manifest.get("index")
            if not isinstance(version, str) or not isinstance(index_path, str):
                raise ValueError("invalid BEQ manifest")
            if not index_path.startswith(version + "/") or ".." in index_path.split("/"):
                raise ValueError("unsafe BEQ index path")
            index_bytes_url = CATALOGUE_BASE_URL + index_path
            async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
                async with session.get(index_bytes_url) as response:
                    response.raise_for_status()
                    index_bytes = await response.read()
            if hashlib.sha256(index_bytes).hexdigest() != manifest.get("index_sha256"):
                raise ValueError("BEQ index checksum mismatch")
            index = json.loads(index_bytes)
            if (
                not isinstance(index, dict)
                or index.get("schema_version") != 1
                or index.get("version") != version
                or not isinstance(index.get("entries"), list)
                or not isinstance(index.get("categories"), dict)
            ):
                raise ValueError("invalid BEQ index")
            entries_by_id = {entry["id"]: entry for entry in index["entries"]
                             if isinstance(entry, dict) and isinstance(entry.get("id"), str)}
            if len(entries_by_id) != len(index["entries"]):
                raise ValueError("BEQ index contains invalid or duplicate entry IDs")
            previous_version = _manifest.get("version") if _manifest else None
            _manifest, _index, _entries_by_id = manifest, index, entries_by_id
            _index_loaded_at = time.monotonic()
            if previous_version != version:
                _entry_cache.clear()
            _LOG.info("BEQ index loaded: %d entries (version %s)",
                      len(index["entries"]), version)
            return True
        except asyncio.CancelledError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError, json.JSONDecodeError) as err:
            _LOG.warning("Unable to load hosted BEQ index: %s", err)
            # Continue using the last validated index if the refresh endpoint is down.
            return _index is not None


async def get_beq_entry(key: str) -> dict[str, Any] | None:
    """Fetch a selected BEQ's filter payload; cache at most ENTRY_CACHE_MAX."""
    if key in _entry_cache:
        _entry_cache.move_to_end(key)
        return _entry_cache[key]
    if not await _load_index() or _manifest is None:
        return None

    if key not in _entries_by_id:
        return None

    version = _manifest["version"]
    url = f"{CATALOGUE_BASE_URL}{version}/entries/{key}.json"
    try:
        payload = await _get_json(url)
        if not isinstance(payload, dict) or not isinstance(payload.get("filters"), list):
            raise ValueError("invalid BEQ entry payload")
        if not payload["filters"]:
            raise ValueError("BEQ entry has no filters")
        _entry_cache[key] = payload
        _entry_cache.move_to_end(key)
        while len(_entry_cache) > ENTRY_CACHE_MAX:
            _entry_cache.popitem(last=False)
        return payload
    except asyncio.CancelledError:
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError, json.JSONDecodeError) as err:
        _LOG.error("Unable to load BEQ entry %s: %s", key, err)
        return None


async def clear_cache() -> bool:
    """Clear index and payloads; next browse reloads the latest published version."""
    global _index, _manifest, _entries_by_id, _index_loaded_at
    if _index_lock.locked():
        _LOG.debug("BEQ index load in progress; cache clear deferred")
        return False
    _index = None
    _manifest = None
    _entries_by_id = {}
    _index_loaded_at = 0.0
    _entry_cache.clear()
    return True


def _entry_to_item(entry: dict[str, Any]) -> BrowseMediaItem:
    title = entry.get("title", "Unknown")
    audio_types = ", ".join(entry.get("audioTypes", []))
    subtitle = str(entry.get("year", ""))
    if audio_types:
        subtitle += f" | {audio_types}"
    display_title = f"{title} {entry.get('author', '')}".strip()[:255]
    return BrowseMediaItem(
        title=display_title,
        media_class=MediaClass.TRACK,
        media_type="beq_entry",
        media_id=f"beq:{entry['id']}",
        can_play=True,
        can_browse=False,
        subtitle=subtitle[:255] if subtitle else None,
    )


async def browse(device: HTP1Device, options: BrowseOptions) -> BrowseResults | StatusCodes:
    media_type = options.media_type or "root"
    media_id = options.media_id or ""
    if media_type == "root":
        return _browse_root(device)
    if media_type == "beq_categories":
        return await _browse_categories()
    if media_type == "beq_category":
        paging = options.paging
        page = max(1, int(paging.page if paging and paging.page else 1))
        limit = max(1, min(1000, int(paging.limit if paging and paging.limit else ITEMS_PER_PAGE)))
        return await _browse_category(media_id, page, limit)
    return StatusCodes.NOT_FOUND


async def search(device: HTP1Device, options: SearchOptions) -> SearchResults | StatusCodes:
    query = options.query.casefold().strip()
    if not query:
        return SearchResults(media=[], pagination=Pagination(page=1, limit=0, count=0))
    if not await _load_index():
        return StatusCodes.SERVER_ERROR

    paging = options.paging
    page = max(1, int(paging.page if paging and paging.page else 1))
    limit = max(1, min(1000, int(paging.limit if paging and paging.limit else ITEMS_PER_PAGE)))
    matches = [
        entry for entry in _index["entries"]
        if query in entry.get("search_title", "")
    ]
    start = (page - 1) * limit
    items = [_entry_to_item(entry) for entry in matches[start:start + limit]]
    return SearchResults(
        media=items,
        pagination=Pagination(page=page, limit=len(items), count=len(matches)),
    )


def _browse_root(device: HTP1Device) -> BrowseResults:
    items = [
        BrowseMediaItem(
            title="BEQ Catalogue", media_class=MediaClass.DIRECTORY,
            media_type="beq_categories", media_id="beq_categories",
            can_browse=True, can_play=False,
            subtitle="Bass EQ correction filters for movies & TV",
        ),
    ]
    if device.beq_active:
        items.append(BrowseMediaItem(
            title=f"Clear BEQ: {device.beq_active}", media_class=MediaClass.TRACK,
            media_type="beq_clear", media_id="beq:clear",
            can_play=True, can_browse=False,
            subtitle="Remove currently loaded BEQ filter",
        ))
    items.append(BrowseMediaItem(
        title="Refresh BEQ Catalogue", media_class=MediaClass.TRACK,
        media_type="beq_reload", media_id="beq:reload",
        can_play=True, can_browse=False,
        subtitle="Reload the compact hosted catalogue",
    ))
    return BrowseResults(
        media=BrowseMediaItem(
            title=device.name, media_class=MediaClass.DIRECTORY,
            media_type="root", media_id="root", can_browse=True,
            can_search=True, items=items,
        ),
        pagination=Pagination(page=1, limit=len(items), count=len(items)),
    )


async def _browse_categories() -> BrowseResults | StatusCodes:
    if not await _load_index():
        return StatusCodes.SERVER_ERROR
    categories = _index["categories"]
    items = [
        BrowseMediaItem(
            title=category.title(), media_class=MediaClass.DIRECTORY,
            media_type="beq_category", media_id=category,
            can_browse=True, can_play=False,
            subtitle=f"{len(ids)} entries",
        )
        for category, ids in sorted(categories.items())
    ]
    return BrowseResults(
        media=BrowseMediaItem(
            title="BEQ Catalogue", media_class=MediaClass.DIRECTORY,
            media_type="beq_categories", media_id="beq_categories",
            can_browse=True, can_search=True, items=items,
        ),
        pagination=Pagination(page=1, limit=len(items), count=len(items)),
    )


async def _browse_category(
    content_type: str, page: int = 1, limit: int = ITEMS_PER_PAGE
) -> BrowseResults | StatusCodes:
    if not await _load_index():
        return StatusCodes.SERVER_ERROR
    ids = _index["categories"].get(content_type, [])
    start = (page - 1) * limit
    page_entries = (_entries_by_id[entry_id] for entry_id in ids[start:start + limit]
                    if entry_id in _entries_by_id)
    items = [_entry_to_item(entry) for entry in page_entries]
    return BrowseResults(
        media=BrowseMediaItem(
            title=content_type.title(), media_class=MediaClass.DIRECTORY,
            media_type="beq_category", media_id=content_type,
            can_browse=True, can_search=True, items=items,
        ),
        pagination=Pagination(page=page, limit=len(items), count=len(ids)),
    )
