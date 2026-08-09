"""Settings & theme configuration view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from jarvis.ui.gui.widgets.buttons import GlowIconButton

if TYPE_CHECKING:
    from jarvis.ui.gui.config import UIConfig
    from jarvis.ui.gui.themes import Theme


class SettingsPage(QFrame):
    """Configuration & settings page for theme, accent, and orb animation tweaking."""

    back_requested = Signal()
    config_changed = Signal(object)

    def __init__(
        self, theme: Theme, config: UIConfig, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.theme = theme
        self.config = config

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header row
        header = QHBoxLayout()
        self.back_btn = GlowIconButton("back", theme, size=40)
        self.back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(self.back_btn)

        title = QLabel("UI Settings & Appearance")
        font = title.font()
        font.setPixelSize(18)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch(1)
        layout.addLayout(header)

        # Scroll area for settings form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_w = QWidget()
        form_layout = QVBoxLayout(form_w)
        form_layout.setSpacing(16)

        # Theme Combobox
        form_layout.addWidget(self._make_label("Color Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Midnight", "Obsidian", "Aurora"])
        self.theme_combo.setCurrentText(config.theme_name)
        self.theme_combo.currentTextChanged.connect(self._on_change)
        form_layout.addWidget(self.theme_combo)

        # Accent Combobox
        form_layout.addWidget(self._make_label("Accent Color:"))
        self.accent_combo = QComboBox()
        self.accent_combo.addItems(
            [
                "Electric Blue",
                "Arc Violet",
                "Plasma Cyan",
                "Reactor Green",
                "Solar Amber",
            ]
        )
        self.accent_combo.setCurrentText(config.accent_name)
        self.accent_combo.currentTextChanged.connect(self._on_change)
        form_layout.addWidget(self.accent_combo)

        # Blob Style
        form_layout.addWidget(self._make_label("Core Orb Style:"))
        self.blob_combo = QComboBox()
        self.blob_combo.addItems(["Energy Ring", "Quantum Wave", "Plasma Core"])
        self.blob_combo.setCurrentText(config.blob_style)
        self.blob_combo.currentTextChanged.connect(self._on_change)
        form_layout.addWidget(self.blob_combo)

        # Animation Speed Slider
        form_layout.addWidget(self._make_label("Orb Animation Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(10, 100)
        self.speed_slider.setValue(config.animation_speed)
        self.speed_slider.valueChanged.connect(self._on_change)
        form_layout.addWidget(self.speed_slider)

        # Wave Strength Slider
        form_layout.addWidget(self._make_label("Wave Pulse Strength:"))
        self.wave_slider = QSlider(Qt.Orientation.Horizontal)
        self.wave_slider.setRange(10, 100)
        self.wave_slider.setValue(config.wave_strength)
        self.wave_slider.valueChanged.connect(self._on_change)
        form_layout.addWidget(self.wave_slider)

        # Particle Density Slider
        form_layout.addWidget(self._make_label("Particle Density:"))
        self.particle_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_slider.setRange(10, 100)
        self.particle_slider.setValue(config.particle_density)
        self.particle_slider.valueChanged.connect(self._on_change)
        form_layout.addWidget(self.particle_slider)

        form_layout.addStretch(1)
        scroll.setWidget(form_w)
        layout.addWidget(scroll, 1)

        self.apply_theme(theme)

    @staticmethod
    def _make_label(text: str) -> QLabel:
        lbl = QLabel(text)
        font = lbl.font()
        font.setBold(True)
        lbl.setFont(font)
        return lbl

    def _on_change(self) -> None:
        from jarvis.ui.gui.config import UIConfig

        new_config = UIConfig(
            theme_name=self.theme_combo.currentText(),
            accent_name=self.accent_combo.currentText(),
            blob_style=self.blob_combo.currentText(),
            animation_speed=self.speed_slider.value(),
            wave_strength=self.wave_slider.value(),
            particle_density=self.particle_slider.value(),
        )
        self.config = new_config
        self.config_changed.emit(new_config)

    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.back_btn.set_theme(theme)
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {theme.background};
                color: {theme.text};
            }}
            QLabel {{
                color: {theme.text};
            }}
            QComboBox {{
                background: {theme.surface};
                color: {theme.text};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: {theme.surface_alt};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {theme.accent};
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            """
        )
