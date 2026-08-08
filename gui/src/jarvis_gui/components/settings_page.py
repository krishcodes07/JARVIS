"""Dedicated full-page settings experience for the JARVIS interface."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from jarvis_gui.components.icon_button import GlowIconButton
from jarvis_gui.config import UIConfig
from jarvis_gui.themes import ACCENTS, THEMES, Theme


class SettingsCard(QFrame):
    def __init__(self, title: str, description: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsCard")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 19, 20, 20)
        self.layout.setSpacing(11)

        heading = QLabel(title)
        heading.setObjectName("SettingsCardTitle")
        self.layout.addWidget(heading)
        helper = QLabel(description)
        helper.setObjectName("SettingsCardDescription")
        helper.setWordWrap(True)
        self.layout.addWidget(helper)
        self.layout.addSpacing(5)


class SettingsPage(QWidget):
    back_requested = Signal()
    config_changed = Signal(object)

    def __init__(self, theme: Theme, config: UIConfig, parent=None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.config = replace(config)
        self.setObjectName("SettingsPage")

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(22, 18, 22, 22)
        page_layout.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(14)
        self.back_button = GlowIconButton("back", theme, size=42)
        self.back_button.setToolTip("Back to assistant")
        self.back_button.clicked.connect(self.back_requested)
        header.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignTop)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(3)
        title = QLabel("Settings")
        title.setObjectName("SettingsPageTitle")
        subtitle = QLabel("Personalize the interface and visualizer behavior.")
        subtitle.setObjectName("SettingsPageSubtitle")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header.addLayout(title_stack)
        header.addStretch(1)
        page_layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        page_layout.addWidget(scroll, 1)

        content = QWidget()
        content.setObjectName("SettingsContent")
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 6, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        scroll.setWidget(content)

        appearance = SettingsCard(
            "Appearance",
            "Choose a neutral color system and a single interface accent.",
        )
        self.theme_combo = self._add_combo(
            appearance.layout, "Theme", list(THEMES), self.config.theme_name
        )
        self.accent_combo = self._add_combo(
            appearance.layout, "Accent", list(ACCENTS), self.config.accent_name
        )
        appearance.layout.addStretch(1)
        grid.addWidget(appearance, 0, 0)

        visualizer = SettingsCard(
            "Visualizer",
            "Adjust the orb style and motion without changing assistant behavior.",
        )
        self.style_combo = self._add_combo(
            visualizer.layout,
            "Orb style",
            ["Energy Ring", "Particle Cloud", "Core Pulse"],
            self.config.blob_style,
        )
        self.speed_slider, self.speed_value = self._add_slider(
            visualizer.layout, "Animation speed", self.config.animation_speed
        )
        self.wave_slider, self.wave_value = self._add_slider(
            visualizer.layout, "Wave strength", self.config.wave_strength
        )
        self.particle_slider, self.particle_value = self._add_slider(
            visualizer.layout, "Particle density", self.config.particle_density
        )
        grid.addWidget(visualizer, 0, 1)

        storage = SettingsCard(
            "Local data",
            "Conversation history is stored only on this computer in a local SQLite database.",
        )
        storage_status = QLabel("Conversation history  •  Enabled")
        storage_status.setObjectName("SettingsStatus")
        storage.layout.addWidget(storage_status)
        storage.layout.addStretch(1)
        grid.addWidget(storage, 1, 0)

        reset = SettingsCard(
            "Reset appearance",
            "Restore the default theme and visualizer values. Saved conversations are not affected.",
        )
        reset_button = QPushButton("Restore defaults")
        reset_button.setObjectName("QuietAction")
        reset_button.clicked.connect(self.reset_defaults)
        reset.layout.addWidget(reset_button)
        reset.layout.addStretch(1)
        grid.addWidget(reset, 1, 1)
        grid.setRowStretch(2, 1)

        self.theme_combo.currentTextChanged.connect(self._emit_changes)
        self.accent_combo.currentTextChanged.connect(self._emit_changes)
        self.style_combo.currentTextChanged.connect(self._emit_changes)
        self.speed_slider.valueChanged.connect(self._emit_changes)
        self.wave_slider.valueChanged.connect(self._emit_changes)
        self.particle_slider.valueChanged.connect(self._emit_changes)

    @staticmethod
    def _add_combo(
        layout: QVBoxLayout, label: str, options: list[str], selected: str
    ) -> QComboBox:
        caption = QLabel(label)
        caption.setObjectName("SettingsFieldLabel")
        layout.addWidget(caption)
        combo = QComboBox()
        combo.addItems(options)
        if selected in options:
            combo.setCurrentText(selected)
        layout.addWidget(combo)
        return combo

    @staticmethod
    def _add_slider(
        layout: QVBoxLayout, label: str, value: int
    ) -> tuple[QSlider, QLabel]:
        header = QHBoxLayout()
        caption = QLabel(label)
        caption.setObjectName("SettingsFieldLabel")
        value_label = QLabel(str(value))
        value_label.setObjectName("SettingsValue")
        header.addWidget(caption)
        header.addStretch(1)
        header.addWidget(value_label)
        layout.addLayout(header)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(value)
        slider.valueChanged.connect(
            lambda changed, display=value_label: display.setText(str(changed))
        )
        layout.addWidget(slider)
        return slider, value_label

    def _emit_changes(self, *_) -> None:
        self.config = UIConfig(
            theme_name=self.theme_combo.currentText(),
            accent_name=self.accent_combo.currentText(),
            blob_style=self.style_combo.currentText(),
            animation_speed=self.speed_slider.value(),
            wave_strength=self.wave_slider.value(),
            particle_density=self.particle_slider.value(),
        )
        self.config_changed.emit(replace(self.config))

    def reset_defaults(self) -> None:
        defaults = UIConfig()
        for combo, value in (
            (self.theme_combo, defaults.theme_name),
            (self.accent_combo, defaults.accent_name),
            (self.style_combo, defaults.blob_style),
        ):
            combo.blockSignals(True)
            combo.setCurrentText(value)
            combo.blockSignals(False)
        for slider, value in (
            (self.speed_slider, defaults.animation_speed),
            (self.wave_slider, defaults.wave_strength),
            (self.particle_slider, defaults.particle_density),
        ):
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
        self.speed_value.setText(str(defaults.animation_speed))
        self.wave_value.setText(str(defaults.wave_strength))
        self.particle_value.setText(str(defaults.particle_density))
        self._emit_changes()

    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.back_button.set_theme(theme)

