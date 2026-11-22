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


def test_probe_times_out_when_server_never_returns_state():
    async def exercise():
        async def endpoint(websocket):
            async for _message in websocket:
                pass

        async with websockets.serve(endpoint, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            result = await probe_htp1("127.0.0.1", timeout=1.0, port=port)
            assert result == f"No response from 127.0.0.1:{port} within 1 seconds"

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
