"""Integration tests for the HTP-1 WebSocket connection and state flow."""

import asyncio
import copy
import json
from pathlib import Path

import websockets

from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device, apply_json_patch


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "htp1_full_mso.json"


def test_websocket_connection_loads_state_and_applies_device_command():
    async def exercise():
        initial_state = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        receiver_state = copy.deepcopy(initial_state)
        received_commands = []
        state_changed = asyncio.Event()

        async def fake_htp1(websocket, *_args):
            nonlocal receiver_state
            async for message in websocket:
                if message == "getmso":
                    await websocket.send(f"mso {json.dumps(receiver_state)}")
                    continue

                if message.startswith("changemso "):
                    received_commands.append(message)
                    operations = json.loads(message.partition(" ")[2])
                    for operation in operations:
                        apply_json_patch(
                            receiver_state,
                            operation["op"],
                            operation["path"],
                            operation.get("value"),
                        )
                    await websocket.send(f"msoupdate {json.dumps(operations)}")

        async with websockets.serve(fake_htp1, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            device = HTP1Device(
                HTP1Config("test", "Test HTP-1", "127.0.0.1", port),
                loop=asyncio.get_running_loop(),
            )
            updates = []
            device.push_update = lambda: updates.append(device._state)
            device._is_connected = True
            websocket = await device.create_websocket()
            assert websocket is device._ws
            assert device.websocket_url == f"ws://127.0.0.1:{port}/ws/controller"

            async def receive_messages():
                while True:
                    message = await device.receive_message()
                    if message is None:
                        return
                    await device.handle_message(message)
                    if device._state is not None and device._state.get("powerIsOn") is False:
                        state_changed.set()

            receiver = asyncio.create_task(receive_messages())
            try:
                await asyncio.wait_for(device._on_connected(device.identifier), timeout=2)

                assert device._state == initial_state
                assert device.power is True
                assert device.current_source
                assert device.get_sensor_value("volume") == str(device.volume_db)
                assert updates

                assert await device.turn_off() is True
                await asyncio.wait_for(state_changed.wait(), timeout=2)

                assert len(received_commands) == 1
                assert json.loads(received_commands[0].partition(" ")[2]) == [
                    {"op": "replace", "path": "/powerIsOn", "value": False}
                ]
                assert device._state["powerIsOn"] is False
                assert device.power is False
            finally:
                receiver.cancel()
                await asyncio.gather(receiver, return_exceptions=True)
                await device.close_websocket()
                device._is_connected = False

    asyncio.run(exercise())
