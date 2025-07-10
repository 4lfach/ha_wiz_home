"""Custom effect manager for Wiz integration."""

import logging
from typing import Any

from pywizlight.effect_manager import (
    EffectDetails,
    EffectStep,
    ModifierType,
    PreviewEffect,
    RenderingType,
)

from .storage import WizHomeConfigStorage

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


class CustomEffectManager:
    """Manager class for custom PreviewEffects loaded from WiZ home configuration."""

    def __init__(self, storage: WizHomeConfigStorage) -> None:
        """Initialize the custom effect manager.

        Args:
            hass: Home Assistant instance
            file_path: Optional file path for backward compatibility

        """
        self._preview_effects: list[PreviewEffect] = []
        self._effect_names: list[str] = []
        self._storage = storage

    async def async_load_effects(self) -> None:
        """Load custom effects from storage."""
        config_data = await self._storage.async_load_config()
        if config_data:
            self._load_effects_from_data(config_data)
        else:
            _LOGGER.debug("No WiZ home config found in storage")

    def _load_effects_from_data(self, home_data: dict[str, Any]) -> None:
        """Load custom effects from home structure data."""
        custom_effects_data = home_data.get("custom_effects", [])

        for effect_data in custom_effects_data:
            try:
                name = effect_data.get("name", "")
                if not name or not effect_data.get("state", True):
                    continue

                preview_effect = self._create_preview_effect(effect_data)

                self._preview_effects.append(preview_effect)
                self._effect_names.append(name)

            except (KeyError, ValueError, TypeError) as ex:
                _LOGGER.error(
                    "Error parsing effect %s: %s",
                    effect_data.get("name", "unknown"),
                    ex,
                )

    def _create_preview_effect(self, effect_data: dict[str, Any]) -> PreviewEffect:
        """Create PreviewEffect from effect data."""
        elm_data = effect_data.get("elm", {})

        details = EffectDetails(
            modifier=ModifierType(elm_data.get("modifier", 0)),
            gradient=elm_data.get("gradient", True),
            init_step=elm_data.get("initStep", 0),
            rand=elm_data.get("rand", 0),
            duration=effect_data.get("duration", 10),
        )

        steps = []
        raw_steps = elm_data.get("steps", [])

        for step_data in raw_steps:
            if isinstance(step_data, list) and len(step_data) >= 13:
                step = EffectStep(
                    rendering_type=RenderingType(step_data[0]),
                    r=step_data[1],
                    g=step_data[2],
                    b=step_data[3],
                    ww=step_data[4],
                    cw=step_data[5],
                    cct=step_data[6],
                    dimming=step_data[7],
                    duration=step_data[8],
                    transition=step_data[9],
                    rand=step_data[10],
                    advanced=step_data[11],
                    software_head=step_data[12],
                )
                steps.append(step)

        # Default step if none provided
        if not steps:
            steps.append(EffectStep.from_rgb(255, 255, 255))

        return PreviewEffect(details, steps)

    def get_effect_names(self) -> list[str]:
        """Get list of all custom effect names."""
        return self._effect_names.copy()

    def get_preview_effects(self) -> list[PreviewEffect]:
        """Get list of all PreviewEffect instances."""
        return self._preview_effects.copy()
