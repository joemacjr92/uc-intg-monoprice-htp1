"""Deterministic tests for hosted BEQ manifest and index loading."""

import asyncio
import hashlib
import json
import time

import aiohttp
import pytest

from intg_monoprice_htp1 import browser


VERSION = "0123456789abcdef"
INDEX = {
    "schema_version": 1,
    "version": VERSION,
    "entries": [
        {
            "id": "abcdef0123456789",
            "title": "Example Film",
            "author": "Example Author",
            "year": "2024",
            "audioTypes": ["Atmos"],
        }
    ],
    "categories": {"film": [0]},
}


class FakeResponse:
    def __init__(self, body=None, error=None):
        self.body = body
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def raise_for_status(self):
        if self.error:
            raise self.error

    async def read(self):
        return self.body


class FakeSession:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def get(self, _url):
        return self.response


def manifest_for(index_bytes):
    return {
        "schema_version": 1,
        "version": VERSION,
        "index": f"{VERSION}/index.json",
        "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
        "entry_count": len(INDEX["entries"]),
    }


def install_responses(monkeypatch, manifest, index_response):
    async def get_json(_url):
        return manifest

    monkeypatch.setattr(browser, "_get_json", get_json)
    monkeypatch.setattr(
        browser, "_new_session", lambda: FakeSession(index_response)
    )


@pytest.fixture(autouse=True)
def reset_browser_cache():
    browser._index = None
    browser._manifest = None
    browser._index_loaded_at = 0
    browser._entry_cache.clear()
    yield
    browser._index = None
    browser._manifest = None
    browser._index_loaded_at = 0
    browser._entry_cache.clear()


def test_load_index_accepts_valid_manifest_and_verified_index(monkeypatch):
    async def exercise():
        index_bytes = json.dumps(INDEX, separators=(",", ":")).encode()
        manifest = manifest_for(index_bytes)
        install_responses(
            monkeypatch, manifest, FakeResponse(body=index_bytes)
        )

        assert await browser._load_index() is True
        assert browser._index == INDEX
        assert browser._manifest == manifest

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "manifest",
    [
        None,
        [],
        {"schema_version": 2},
        {"schema_version": 1, "version": "invalid"},
        {
            "schema_version": 1,
            "version": VERSION,
            "index": "other/index.json",
            "index_sha256": "0" * 64,
            "entry_count": 1,
        },
        {
            "schema_version": 1,
            "version": VERSION,
            "index": f"{VERSION}/index.json",
            "index_sha256": "not-a-checksum",
            "entry_count": 1,
        },
    ],
)
def test_load_index_rejects_invalid_manifests_without_caching(monkeypatch, manifest):
    async def exercise():
        async def get_json(_url):
            return manifest

        monkeypatch.setattr(browser, "_get_json", get_json)
        assert await browser._load_index() is False
        assert browser._index is None
        assert browser._manifest is None

    asyncio.run(exercise())


def test_load_index_rejects_checksum_mismatch(monkeypatch):
    async def exercise():
        index_bytes = json.dumps(INDEX).encode()
        manifest = manifest_for(index_bytes)
        manifest["index_sha256"] = "0" * 64
        install_responses(
            monkeypatch, manifest, FakeResponse(body=index_bytes)
        )

        assert await browser._load_index() is False
        assert browser._index is None

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "index",
    [
        {"schema_version": 2},
        {**INDEX, "version": "fedcba9876543210"},
        {**INDEX, "categories": {"film": [1]}},
    ],
)
def test_load_index_rejects_invalid_index_structure(monkeypatch, index):
    async def exercise():
        index_bytes = json.dumps(index).encode()
        manifest = manifest_for(index_bytes)
        install_responses(
            monkeypatch, manifest, FakeResponse(body=index_bytes)
        )

        assert await browser._load_index() is False
        assert browser._index is None

    asyncio.run(exercise())


def test_load_index_rejects_manifest_entry_count_mismatch(monkeypatch):
    async def exercise():
        index_bytes = json.dumps(INDEX).encode()
        manifest = manifest_for(index_bytes)
        manifest["entry_count"] = 99
        install_responses(
            monkeypatch, manifest, FakeResponse(body=index_bytes)
        )

        assert await browser._load_index() is False
        assert browser._index is None

    asyncio.run(exercise())


def test_load_index_returns_false_for_http_failure(monkeypatch):
    async def exercise():
        index_bytes = json.dumps(INDEX).encode()
        manifest = manifest_for(index_bytes)
        error = aiohttp.ClientResponseError(
            request_info=type("RequestInfo", (), {"real_url": "https://example.invalid/index.json"})(), history=(), status=503
        )
        install_responses(
            monkeypatch, manifest, FakeResponse(error=error)
        )

        assert await browser._load_index() is False
        assert browser._index is None

    asyncio.run(exercise())


@pytest.mark.parametrize("failure", [aiohttp.ClientError("offline"), asyncio.TimeoutError()])
def test_load_index_returns_false_for_manifest_network_failure(monkeypatch, failure):
    async def exercise():
        async def get_json(_url):
            raise failure

        monkeypatch.setattr(browser, "_get_json", get_json)
        assert await browser._load_index() is False
        assert browser._index is None

    asyncio.run(exercise())


def test_load_index_recovers_after_initial_network_failure(monkeypatch):
    async def exercise():
        calls = 0
        index_bytes = json.dumps(INDEX).encode()
        manifest = manifest_for(index_bytes)

        async def get_json(_url):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise aiohttp.ClientError("temporary outage")
            return manifest

        monkeypatch.setattr(browser, "_get_json", get_json)
        monkeypatch.setattr(
            browser, "_new_session",
            lambda: FakeSession(FakeResponse(body=index_bytes)),
        )

        assert await browser._load_index() is False
        assert await browser._load_index() is True
        assert calls == 2
        assert browser._index == INDEX

    asyncio.run(exercise())


def test_load_index_retains_last_known_good_index_on_refresh_failure(monkeypatch):
    async def exercise():
        old_index = {"version": "old"}
        old_manifest = {"version": "old"}
        browser._index = old_index
        browser._manifest = old_manifest
        browser._index_loaded_at = time.monotonic() - browser.INDEX_CACHE_LIFE - 1

        async def get_json(_url):
            raise asyncio.TimeoutError()

        monkeypatch.setattr(browser, "_get_json", get_json)

        assert await browser._load_index() is True
        assert browser._index is old_index
        assert browser._manifest is old_manifest
        # Failed refresh is deferred for five minutes, avoiding request storms.
        assert browser._index_loaded_at > time.monotonic() - browser.INDEX_CACHE_LIFE

    asyncio.run(exercise())
