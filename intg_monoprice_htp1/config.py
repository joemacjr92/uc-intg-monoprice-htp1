"""
Monoprice HTP-1 configuration for Unfolded Circle integration.

:copyright: (c) 2026 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from dataclasses import dataclass
from ucapi_framework import BaseConfigManager


@dataclass
class HTP1Config:
    """Monoprice HTP-1 configuration."""

    identifier: str
    name: str
    host: str


class HTP1ConfigManager(BaseConfigManager[HTP1Config]):
    """Configuration manager with automatic JSON persistence."""

    pass
