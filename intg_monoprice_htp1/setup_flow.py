"""
Monoprice HTP-1 setup flow for Unfolded Circle integration.

:copyright: (c) 2026 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any
from ucapi import RequestUserInput
from ucapi_framework import BaseSetupFlow
from intg_monoprice_htp1.config import HTP1Config
from intg_monoprice_htp1.device import HTP1Device

_LOG = logging.getLogger(__name__)


class HTP1SetupFlow(BaseSetupFlow[HTP1Config]):
    """Setup flow for Monoprice HTP-1 integration."""

    def get_manual_entry_form(self) -> RequestUserInput:
        """Define manual entry fields."""
        return RequestUserInput(
            {"en": "Monoprice HTP-1 Setup"},
            [
                {
                    "id": "name",
                    "label": {"en": "Device Name"},
                    "field": {"text": {"value": "Monoprice HTP-1"}},
                },
                {
                    "id": "host",
                    "label": {"en": "IP Address"},
                    "field": {"text": {"value": ""}},
                },
            ],
        )

    async def query_device(
        self, input_values: dict[str, Any]
    ) -> HTP1Config | RequestUserInput:
        """
        Validate connection and create config.
        Called after user provides info.
        """
        host = input_values.get("host", "").strip()
        if not host:
            raise ValueError("IP address is required")

        name = input_values.get("name", f"Monoprice HTP-1 ({host})").strip()

        _LOG.info("Setting up Monoprice HTP-1 at %s", host)

        # Test connection
        try:
            test_config = HTP1Config(
                identifier=f"htp1_{host.replace('.', '_')}",
                name=name,
                host=host
            )

            # Quick connection test
            test_device = HTP1Device(test_config)
            connected = await asyncio.wait_for(
                test_device.connect(),
                timeout=10.0
            )
            await test_device.disconnect()

            if not connected:
                raise ValueError(f"Failed to connect to {host}")

            _LOG.info("Successfully connected to Monoprice HTP-1 at %s", host)
            return test_config

        except asyncio.TimeoutError:
            raise ValueError(
                f"Connection timeout to {host}\n"
                "Please verify the HTP-1 is powered on and accessible on the network"
            ) from None
        except Exception as err:
            raise ValueError(f"Setup failed: {err}") from err
