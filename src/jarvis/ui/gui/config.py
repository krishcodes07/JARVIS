"""Persistent, serializable UI settings stored in config/jarvis.yaml."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _find_jarvis_yaml() -> Path:
    """Locate config/jarvis.yaml relative to current module or working directory."""
    # src/jarvis/ui/gui/config.py -> project root (4 levels up)
    file_root = Path(__file__).resolve().parents[4]
    if (file_root / "config" / "jarvis.yaml").exists():
        return file_root / "config" / "jarvis.yaml"

    cwd_config = Path.cwd() / "config" / "jarvis.yaml"
    if cwd_config.exists():
        return cwd_config

    return file_root / "config" / "jarvis.yaml"


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
    def load(cls, config_path: Path | str | None = None) -> UIConfig:
        path = Path(config_path) if config_path else _find_jarvis_yaml()
        defaults = cls()
        if not path.exists():
            return defaults

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            gui_data = data.get("ui", {}).get("gui", {})
            if not isinstance(gui_data, dict):
                gui_data = {}

            return cls(
                theme_name=str(gui_data.get("theme_name", gui_data.get("theme", defaults.theme_name))),
                accent_name=str(gui_data.get("accent_name", defaults.accent_name)),
                blob_style=str(gui_data.get("blob_style", defaults.blob_style)),
                animation_speed=int(gui_data.get("animation_speed", defaults.animation_speed)),
                wave_strength=int(gui_data.get("wave_strength", defaults.wave_strength)),
                particle_density=int(gui_data.get("particle_density", defaults.particle_density)),
            )
        except Exception as e:
            logger.warning("Failed to load GUI config from %s: %s", path, e)
            return defaults

    def save(self, config_path: Path | str | None = None) -> None:
        path = Path(config_path) if config_path else _find_jarvis_yaml()
        try:
            data: dict[str, Any] = {}
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

            if "ui" not in data or not isinstance(data["ui"], dict):
                data["ui"] = {}

            gui_dict = {
                "theme_name": self.theme_name,
                "accent_name": self.accent_name,
                "blob_style": self.blob_style,
                "animation_speed": self.animation_speed,
                "wave_strength": self.wave_strength,
                "particle_density": self.particle_density,
            }
            if isinstance(data["ui"].get("gui"), dict):
                data["ui"]["gui"].update(gui_dict)
            else:
                data["ui"]["gui"] = gui_dict

            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
            logger.info("Saved GUI config to %s", path)
        except Exception as e:
            logger.error("Failed to save GUI config to %s: %s", path, e)
