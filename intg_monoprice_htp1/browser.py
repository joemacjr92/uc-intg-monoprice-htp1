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
import math
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
_index_loaded_at: float = 0.0
_index_lock = asyncio.Lock()
_entry_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()


async def _get_json(url: str) -> Any:
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json(content_type=None)


async def _load_index() -> bool:
    """Load and validate the compact index, retaining a last-known-good copy."""
    global _index, _manifest, _index_loaded_at
    if _index is not None and time.monotonic() - _index_loaded_at < INDEX_CACHE_LIFE:
        return True

    async with _index_lock:
        if _index is not None and time.monotonic() - _index_loaded_at < INDEX_CACHE_LIFE:
            return True
        try:
            manifest = await _get_json(CATALOGUE_BASE_URL + "manifest.json")
            if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
                raise ValueError("unsupported BEQ manifest schema")
            version = manifest.get("version")
            index_path = manifest.get("index")
            if (not isinstance(version, str) or len(version) != 16
                    or any(char not in "0123456789abcdef" for char in version)
                    or not isinstance(index_path, str)):
                raise ValueError("invalid BEQ manifest")
            if not index_path.startswith(version + "/") or ".." in index_path.split("/"):
                raise ValueError("unsafe BEQ index path")

            async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
                async with session.get(CATALOGUE_BASE_URL + index_path) as response:
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
            if any(
                not isinstance(entry, dict)
                or not isinstance(entry.get("id"), str)
                or len(entry["id"]) != 16
                or any(char not in "0123456789abcdef" for char in entry["id"])
                for entry in index["entries"]
            ):
                raise ValueError("BEQ index contains an invalid entry ID")
            # Legacy media IDs intentionally collapse identical filter records
            # even if catalogue metadata such as author differs.
            entry_count = len(index["entries"])
            if any(not isinstance(indexes, list) or any(
                not isinstance(index_value, int) or index_value < 0 or index_value >= entry_count
                for index_value in indexes
            ) for indexes in index["categories"].values()):
                raise ValueError("BEQ index contains invalid category offsets")

            previous_version = _manifest.get("version") if _manifest else None
            _manifest, _index = manifest, index
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
            if _index is not None:
                # Avoid hammering a failed endpoint; retry after five minutes.
                _index_loaded_at = time.monotonic() - INDEX_CACHE_LIFE + 300
                return True
            return False


async def _fetch_entry_payload(version: str, key: str) -> dict[str, Any]:
    url = f"{CATALOGUE_BASE_URL}{version}/entries/{key}.json"
    payload = await _get_json(url)
    if (not isinstance(payload, dict) or not isinstance(payload.get("title"), str)
            or not isinstance(payload.get("underlying"), str)
            or not isinstance(payload.get("filters"), list)):
        raise ValueError("invalid BEQ entry payload")
    filters = payload["filters"]
    if not filters or len(filters) > 16:
        raise ValueError("BEQ entry filter count is outside the HTP-1's 1-16 slot range")
    for item in filters:
        if not isinstance(item, dict) or item.get("type") not in {
            "PeakingEQ", "LowShelf", "HighShelf"
        }:
            raise ValueError("BEQ entry contains an unsupported filter type")
        for field in ("freq", "gain", "q"):
            value = item.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"BEQ entry contains an invalid {field}")
            try:
                finite = math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError(f"BEQ entry contains a non-finite {field}")
        if item["freq"] <= 0 or item["q"] <= 0:
            raise ValueError("BEQ entry frequency and Q must be positive")
    return payload


async def get_beq_entry(key: str) -> dict[str, Any] | None:
    """Fetch a selected payload, retrying once if a Pages deployment changed."""
    global _index_loaded_at
    if not await _load_index() or _manifest is None:
        return None
    if len(key) != 16 or any(char not in "0123456789abcdef" for char in key):
        return None
    if key in _entry_cache:
        _entry_cache.move_to_end(key)
        return _entry_cache[key]

    version = _manifest["version"]
    try:
        payload = await _fetch_entry_payload(version, key)
    except aiohttp.ClientResponseError as err:
        if err.status != 404:
            _LOG.error("Unable to load BEQ entry %s: %s", key, err)
            return None
        # A Pages deployment may replace the previous version while an old
        # browse result is still open. Refresh and retry if this ID survived.
        _index_loaded_at = time.monotonic() - INDEX_CACHE_LIFE - 1
        if not await _load_index() or _manifest is None or _manifest["version"] == version:
            return None
        try:
            payload = await _fetch_entry_payload(_manifest["version"], key)
        except asyncio.CancelledError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError, json.JSONDecodeError) as retry_err:
            _LOG.error("Unable to load BEQ entry %s after catalogue refresh: %s", key, retry_err)
            return None
    except asyncio.CancelledError:
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError, json.JSONDecodeError) as err:
        _LOG.error("Unable to load BEQ entry %s: %s", key, err)
        return None

    _entry_cache[key] = payload
    _entry_cache.move_to_end(key)
    while len(_entry_cache) > ENTRY_CACHE_MAX:
        _entry_cache.popitem(last=False)
    return payload


async def clear_cache() -> bool:
    """Clear index and payloads; next browse reloads the latest published version."""
    global _index, _manifest, _index_loaded_at
    if _index_lock.locked():
        _LOG.debug("BEQ index load in progress; cache clear deferred")
        return False
    _index = None
    _manifest = None
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
        can_play=entry.get("has_filters", True),
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
    start = (page - 1) * limit
    items: list[SearchMediaItem] = []
    total_matches = 0
    for entry in _index["entries"]:
        if query in entry.get("title", "").casefold():
            if start <= total_matches < start + limit:
                items.append(_entry_to_item(entry))
            total_matches += 1
    return SearchResults(
        media=items,
        pagination=Pagination(page=page, limit=len(items), count=total_matches),
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
    entry_indexes = _index["categories"].get(content_type, [])
    start = (page - 1) * limit
    page_entries = (_index["entries"][entry_index]
                    for entry_index in entry_indexes[start:start + limit])
    items = [_entry_to_item(entry) for entry in page_entries]

    return BrowseResults(
        media=BrowseMediaItem(
            title=content_type.title(), media_class=MediaClass.DIRECTORY,
            media_type="beq_category", media_id=content_type,
            can_browse=True, can_search=True, items=items,
        ),
        pagination=Pagination(page=page, limit=len(items), count=len(entry_indexes)),
    )
