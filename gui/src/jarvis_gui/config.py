"""Persistent, serializable UI settings."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings


@dataclass(slots=True)
class UIConfig:
    """Runtime settings consumed by the theme and animated orb."""

    theme_name: str = "Midnight"
    accent_name: str = "Electric Blue"
    blob_style: str = "Energy Ring"
    animation_speed: int = 55
    wave_strength: int = 58
    particle_density: int = 62

    @classmethod
    def load(cls, settings: QSettings | None = None) -> "UIConfig":
        settings = settings or QSettings("JARVIS", "GUI")
        defaults = cls()
        return cls(
            theme_name=str(settings.value("theme/name", defaults.theme_name)),
            accent_name=str(settings.value("theme/accent", defaults.accent_name)),
            blob_style=str(settings.value("blob/style", defaults.blob_style)),
            animation_speed=int(
                settings.value("blob/speed", defaults.animation_speed)
            ),
            wave_strength=int(settings.value("blob/wave", defaults.wave_strength)),
            particle_density=int(
                settings.value("blob/particles", defaults.particle_density)
            ),
        )

    def save(self) -> None:
        settings = QSettings("JARVIS", "GUI")
        settings.setValue("theme/name", self.theme_name)
        settings.setValue("theme/accent", self.accent_name)
        settings.setValue("blob/style", self.blob_style)
        settings.setValue("blob/speed", self.animation_speed)
        settings.setValue("blob/wave", self.wave_strength)
        settings.setValue("blob/particles", self.particle_density)
