"""WiZ integration models."""

from __future__ import annotations

from dataclasses import dataclass

from pywizlight_alfa import wizlight

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .custom_effect import CustomEffectManager


@dataclass
class WizData:
    """Data for the wiz integration."""

    coordinator: DataUpdateCoordinator[float | None]
    bulb: wizlight
    scenes: list
    custom_effect_manager: CustomEffectManager | None = None
