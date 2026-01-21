"""
Monoprice HTP-1 Remote entity.

:copyright: (c) 2026 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any
from ucapi import StatusCodes
from ucapi.remote import (
    Attributes,
    Commands,
    Features,
    Remote,
)
from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device

_LOG = logging.getLogger(__name__)

# Simple command IDs for activities and macros
SIMPLE_COMMANDS = [
    "POWER",
    "VOLUME_UP",
    "VOLUME_DOWN",
    "MUTE",
    "CURSOR_UP",
    "CURSOR_DOWN",
    "CURSOR_LEFT",
    "CURSOR_RIGHT",
    "CURSOR_ENTER",
    "BACK",
    "HOME",
]


class HTP1Remote(Remote):
    """Remote entity for Monoprice HTP-1."""

    def __init__(self, device_config: HTP1Config, device: HTP1Device):
        """Initialize with device reference."""
        self._device = device
        self._device_config = device_config

        entity_id = f"remote.{device_config.identifier}"
        entity_name = f"{device_config.name} Remote"

        features = [Features.SEND_CMD]
        attributes = {Attributes.STATE: "UNAVAILABLE"}

        # Define user interface with button layout
        user_interface = {
            "pages": [
                {
                    "page_id": "main",
                    "name": "Main",
                    "grid": {"width": 4, "height": 6},
                    "items": [
                        # Row 1: Power
                        {"type": "text", "text": "Power", "command": {"cmd_id": "POWER"}, "location": {"x": 1, "y": 0}, "size": {"width": 2, "height": 1}},
                        # Row 2: Volume controls
                        {"type": "icon", "icon": "uc:up-arrow", "command": {"cmd_id": "VOLUME_UP"}, "location": {"x": 0, "y": 1}},
                        {"type": "icon", "icon": "uc:mute", "command": {"cmd_id": "MUTE"}, "location": {"x": 1, "y": 1}, "size": {"width": 2, "height": 1}},
                        {"type": "icon", "icon": "uc:down-arrow", "command": {"cmd_id": "VOLUME_DOWN"}, "location": {"x": 3, "y": 1}},
                        # Row 3-4: D-Pad
                        {"type": "icon", "icon": "uc:up-arrow", "command": {"cmd_id": "CURSOR_UP"}, "location": {"x": 1, "y": 2}},
                        {"type": "icon", "icon": "uc:left-arrow", "command": {"cmd_id": "CURSOR_LEFT"}, "location": {"x": 0, "y": 3}},
                        {"type": "text", "text": "OK", "command": {"cmd_id": "CURSOR_ENTER"}, "location": {"x": 1, "y": 3}, "size": {"width": 2, "height": 1}},
                        {"type": "icon", "icon": "uc:right-arrow", "command": {"cmd_id": "CURSOR_RIGHT"}, "location": {"x": 3, "y": 3}},
                        {"type": "icon", "icon": "uc:down-arrow", "command": {"cmd_id": "CURSOR_DOWN"}, "location": {"x": 1, "y": 4}},
                        # Row 5: Navigation
                        {"type": "text", "text": "Back", "command": {"cmd_id": "BACK"}, "location": {"x": 0, "y": 5}},
                        {"type": "text", "text": "Home", "command": {"cmd_id": "HOME"}, "location": {"x": 3, "y": 5}},
                    ],
                }
            ]
        }

        # Create remote with UI and simple commands
        super().__init__(
            entity_id,
            entity_name,
            features,
            attributes,
            simple_commands=SIMPLE_COMMANDS,
            ui_pages=user_interface["pages"],
            cmd_handler=self.handle_command,
        )

    async def handle_command(
        self, entity: Remote, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        """Handle remote commands."""
        _LOG.info("[%s] Remote command: %s %s", self.id, cmd_id, params or "")

        try:
            # Map command IDs to device actions
            if cmd_id == "POWER":
                if self._device._state:
                    power_on = self._device._state.get("powerIsOn", False)
                    success = await self._device.turn_off() if power_on else await self._device.turn_on()
                    return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
                return StatusCodes.SERVER_ERROR

            elif cmd_id == "VOLUME_UP":
                success = await self._device.volume_up()
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == "VOLUME_DOWN":
                success = await self._device.volume_down()
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == "MUTE":
                if self._device._state:
                    muted = self._device._state.get("muted", False)
                    success = await self._device.mute(not muted)
                    return StatusCodes.OK if success else StatusCodes.SERVER_ERROR
                return StatusCodes.SERVER_ERROR

            # Navigation commands
            elif cmd_id == "CURSOR_UP":
                success = await self._device.send_menu_command("up")
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == "CURSOR_DOWN":
                success = await self._device.send_menu_command("down")
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == "CURSOR_LEFT":
                success = await self._device.send_menu_command("left")
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == "CURSOR_RIGHT":
                success = await self._device.send_menu_command("right")
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == "CURSOR_ENTER":
                success = await self._device.send_menu_command("enter")
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == "BACK":
                success = await self._device.send_menu_command("back")
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == "HOME":
                success = await self._device.send_menu_command("home")
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            return StatusCodes.NOT_IMPLEMENTED

        except Exception as err:
            _LOG.error("[%s] Remote command error: %s", self.id, err)
            return StatusCodes.SERVER_ERROR
