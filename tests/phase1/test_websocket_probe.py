"""WebSocket connection-probe tests against local simulated endpoints."""

import asyncio
import socket

import websockets

from intg_monoprice_htp1.device import probe_htp1


def test_probe_succeeds_on_configured_port_and_requests_state():
    async def exercise():
        received = []

        async def endpoint(websocket):
            async for message in websocket:
                received.append(message)
                if message == "getmso":
                    await websocket.send("mso {}")

        async with websockets.serve(endpoint, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            assert await probe_htp1("127.0.0.1", timeout=1, port=port) is None

        assert received == ["getmso"]

    asyncio.run(exercise())


def test_probe_ignores_non_state_messages_until_valid_state_marker():
    async def exercise():
        async def endpoint(websocket):
            async for message in websocket:
                if message == "getmso":
                    await websocket.send("connected")
                    await websocket.send("mso {}")

        async with websockets.serve(endpoint, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            assert await probe_htp1("127.0.0.1", timeout=1, port=port) is None

    asyncio.run(exercise())


def test_probe_times_out_when_server_never_returns_state(monkeypatch):
    async def exercise():
        sent = []

        class SilentWebSocket:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def send(self, message):
                sent.append(message)

            async def recv(self):
                await asyncio.Event().wait()

        websocket = SilentWebSocket()
        monkeypatch.setattr(websockets, "connect", lambda *_args, **_kwargs: websocket)

        result = await probe_htp1("127.0.0.1", timeout=0.01, port=12345)

        assert result == "No response from 127.0.0.1:12345 within 0 seconds"
        assert sent == ["getmso"]

    asyncio.run(exercise())

def test_probe_reports_connection_refused():
    async def exercise():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        result = await probe_htp1("127.0.0.1", timeout=0.2, port=port)
        assert result is not None
        assert result.startswith(f"Could not connect to 127.0.0.1:{port}:")

    asyncio.run(exercise())
