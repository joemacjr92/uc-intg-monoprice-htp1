"""Verified TLS configuration for the hosted BEQ catalogue."""

import ssl

from intg_monoprice_htp1 import browser


def test_catalogue_session_uses_certifi_and_verified_tls(monkeypatch):
    captured = {}

    class FakeConnector:
        def __init__(self, **kwargs):
            captured["connector_kwargs"] = kwargs

    class FakeSession:
        def __init__(self, **kwargs):
            captured["session_kwargs"] = kwargs

    monkeypatch.setattr(browser.aiohttp, "TCPConnector", FakeConnector)
    monkeypatch.setattr(browser.aiohttp, "ClientSession", FakeSession)

    result = browser._new_session()

    assert isinstance(result, FakeSession)
    context = captured["connector_kwargs"]["ssl"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert captured["session_kwargs"]["connector"].__class__ is FakeConnector
    assert captured["session_kwargs"]["timeout"] == browser.REQUEST_TIMEOUT


def test_catalogue_uses_only_github_pages_host():
    assert browser.CATALOGUE_BASE_URL == (
        "https://mase1981.github.io/uc-intg-monoprice-htp1/beq/"
    )
