"""Tests for configurable HTP-1 connection ports."""

import asyncio
import json

import pytest

from intg_monoprice_htp1.config import HTP1Config, HTP1ConfigManager
from intg_monoprice_htp1.device import HTP1Device, probe_htp1


def test_config_port_defaults_to_http_default():
    config = HTP1Config("test", "Test HTP-1", "127.0.0.1")
    assert config.port == 80


@pytest.mark.parametrize("port", [1, 80, 8080, 65535])
def test_config_accepts_valid_port(port):
    config = HTP1Config("test", "Test HTP-1", "127.0.0.1", port)
    assert config.port == port


@pytest.mark.parametrize("port", [0, 65536, -1, True, False, "8080", 80.5, None])
def test_config_rejects_invalid_port(port):
    with pytest.raises(ValueError):
        HTP1Config("test", "Test HTP-1", "127.0.0.1", port)


def test_legacy_config_without_port_uses_default():
    legacy = {
        "identifier": "test",
        "name": "Test HTP-1",
        "host": "127.0.0.1",
    }
    config = HTP1Config(**legacy)
    assert config.port == 80


def test_device_websocket_url_uses_configured_port():
    config = HTP1Config("test", "Test HTP-1", "192.0.2.10", 8088)
    device = HTP1Device(config)
    assert device.websocket_url == "ws://192.0.2.10:8088/ws/controller"


def test_device_websocket_url_keeps_default_port_for_old_configs():
    device = HTP1Device(HTP1Config("test", "Test HTP-1", "192.0.2.10"))
    assert device.websocket_url == "ws://192.0.2.10:80/ws/controller"


def test_probe_uses_configured_port(monkeypatch):
    calls = []

    class FakeWebSocket:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def send(self, message):
            calls.append(("send", message))

        async def recv(self):
            return "mso {}"

    def fake_connect(url, **kwargs):
        calls.append(("connect", url, kwargs))
        return FakeWebSocket()

    monkeypatch.setattr("intg_monoprice_htp1.device.websockets.connect", fake_connect)
    result = asyncio.run(probe_htp1("192.0.2.10", port=8088))

    assert result is None
    assert calls[0][0:2] == ("connect", "ws://192.0.2.10:8088/ws/controller")
    assert calls[1] == ("send", "getmso")


def test_backup_and_restore_preserve_configured_port(tmp_path):
    source = HTP1ConfigManager(str(tmp_path / "source.json"))
    source.add_or_update(HTP1Config("test", "Test HTP-1", "192.0.2.10", 8088))

    backup = source.get_backup_json()
    assert json.loads(backup)[0]["port"] == 8088

    restored = HTP1ConfigManager(str(tmp_path / "restored.json"))
    assert restored.restore_from_backup_json(backup)
    assert restored.get("test").port == 8088


def test_legacy_backup_without_port_restores_default_port(tmp_path):
    legacy_backup = json.dumps([
        {
            "identifier": "legacy",
            "name": "Legacy HTP-1",
            "host": "192.0.2.20",
        }
    ])
    manager = HTP1ConfigManager(str(tmp_path / "restored.json"))

    assert manager.restore_from_backup_json(legacy_backup)
    restored = manager.get("legacy")
    assert restored is not None
    assert restored.port == 80


def test_setup_form_exposes_port_field_with_default(monkeypatch):
    from intg_monoprice_htp1.setup_flow import HTP1SetupFlow

    flow = HTP1SetupFlow.__new__(HTP1SetupFlow)
    flow._add_mode = True
    form = flow.get_manual_entry_form()
    fields = {item["id"]: item for item in form.settings}

    assert fields["port"]["field"]["text"]["value"] == "80"


def test_setup_form_prefills_saved_port(monkeypatch):
    from intg_monoprice_htp1.setup_flow import HTP1SetupFlow

    flow = HTP1SetupFlow.__new__(HTP1SetupFlow)
    existing = HTP1Config("test", "Test HTP-1", "192.0.2.10", 8088)
    monkeypatch.setattr(flow, "_existing_config", lambda: existing)
    form = flow.get_manual_entry_form()
    fields = {item["id"]: item for item in form.settings}

    assert fields["port"]["field"]["text"]["value"] == "8088"


def test_setup_parses_port_and_passes_it_to_probe(monkeypatch):
    from intg_monoprice_htp1 import setup_flow

    flow = setup_flow.HTP1SetupFlow.__new__(setup_flow.HTP1SetupFlow)
    flow._add_mode = True
    seen = []

    async def fake_probe(host, port=80):
        seen.append((host, port))
        return None

    monkeypatch.setattr(setup_flow, "probe_htp1", fake_probe)
    config = asyncio.run(
        flow.query_device({"name": "Receiver", "host": "192.0.2.10", "port": "8088"})
    )

    assert isinstance(config, HTP1Config)
    assert config.port == 8088
    assert seen == [("192.0.2.10", 8088)]


@pytest.mark.parametrize("port", ["0", "65536", "-1", "80.5", "abc", ""])
def test_setup_rejects_invalid_port_without_probing(monkeypatch, port):
    from intg_monoprice_htp1 import setup_flow

    flow = setup_flow.HTP1SetupFlow.__new__(setup_flow.HTP1SetupFlow)
    flow._add_mode = True

    async def unexpected_probe(*args, **kwargs):
        pytest.fail("probe must not run for an invalid port")

    monkeypatch.setattr(setup_flow, "probe_htp1", unexpected_probe)
    result = asyncio.run(
        flow.query_device({"name": "Receiver", "host": "192.0.2.10", "port": port})
    )

    assert not isinstance(result, HTP1Config)

def test_http_ir_command_uses_configured_port(monkeypatch):
    from intg_monoprice_htp1 import device as device_module

    calls = []

    class FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def get(self, url, timeout):
            calls.append((url, timeout))
            return FakeResponse()

    monkeypatch.setattr(device_module.aiohttp, "ClientSession", FakeSession)
    receiver = HTP1Device.__new__(HTP1Device)
    receiver._device_config = HTP1Config(
        "test", "Test HTP-1", "192.0.2.10", 8088
    )

    assert asyncio.run(receiver.send_http_command("0BF4"))
    assert calls == [("http://192.0.2.10:8088/ircmd?code=0BF4", 5)]
