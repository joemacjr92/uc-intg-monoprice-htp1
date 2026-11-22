"""HTTP/IR command tests using local HTTP fixtures and controlled failures."""

import asyncio
import socket

from aiohttp import web
import aiohttp
import pytest

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device


def make_device(port):
    return HTP1Device(
        HTP1Config("http-ir", "HTTP IR HTP-1", "127.0.0.1", port),
        loop=asyncio.get_running_loop(),
    )


async def start_server(handler):
    app = web.Application()
    app.router.add_get("/ircmd", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, port


def test_http_ir_command_sends_code_to_configured_port():
    async def exercise():
        requests = []

        async def handler(request):
            requests.append((request.path, request.query.get("code")))
            return web.Response(status=200)

        runner, port = await start_server(handler)
        try:
            device = make_device(port)
            assert await device.send_http_command("4ab5") is True
            assert requests == [("/ircmd", "4ab5")]
        finally:
            await runner.cleanup()

    asyncio.run(exercise())


def test_http_ir_command_returns_false_for_non_success_status():
    async def exercise():
        async def handler(_request):
            return web.Response(status=503)

        runner, port = await start_server(handler)
        try:
            assert await make_device(port).send_http_command("4ab5") is False
        finally:
            await runner.cleanup()

    asyncio.run(exercise())


@pytest.mark.parametrize("command", ["", "123", "12345", "zzzz", "12 4", None, 1234])
def test_http_ir_command_rejects_invalid_codes_without_network(command):
    async def exercise():
        device = make_device(1)
        assert await device.send_http_command(command) is False

    asyncio.run(exercise())


def test_http_ir_command_handles_connection_refused():
    async def exercise():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            unused_port = sock.getsockname()[1]
        assert await make_device(unused_port).send_http_command("4ab5") is False

    asyncio.run(exercise())


def test_http_ir_command_handles_timeout(monkeypatch):
    class TimeoutRequest:
        async def __aenter__(self):
            raise asyncio.TimeoutError

        async def __aexit__(self, *_args):
            return False

    class TimeoutSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        def get(self, *_args, **_kwargs):
            return TimeoutRequest()

    async def exercise():
        monkeypatch.setattr(aiohttp, "ClientSession", TimeoutSession)
        assert await make_device(80).send_http_command("4ab5") is False

    asyncio.run(exercise())
