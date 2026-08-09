"""Animated glowing core orb representing JARVIS AI state."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget

if TYPE_CHECKING:
    from jarvis.ui.gui.config import UIConfig
    from jarvis.ui.gui.themes import Theme


class JarvisOrb(QWidget):
    """Animated glowing core orb representing JARVIS AI status."""

    def __init__(
        self,
        theme: Theme,
        config: UIConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.theme = theme
        self.config = config
        self.status_text = "ONLINE • READY"
        self.is_speaking = False
        self._phase = 0.0

        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._update_timer_interval()
        self._timer.start()

    def _update_timer_interval(self) -> None:
        speed = max(10, min(100, self.config.animation_speed))
        interval = int(1000 / (15 + (speed / 100.0) * 45))
        self._timer.setInterval(interval)

    def _on_tick(self) -> None:
        self._phase += 0.05
        if self._phase > 2 * math.pi * 100:
            self._phase = 0.0
        self.update()

    def apply_settings(self, theme: Theme, config: UIConfig) -> None:
        self.theme = theme
        self.config = config
        self._update_timer_interval()
        self.update()

    def set_status(self, status: str) -> None:
        self.status_text = status
        self.update()

    def set_speaking(self, speaking: bool) -> None:
        self.is_speaking = speaking
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        cx = width / 2.0
        cy = height / 2.0 - 15.0
        base_radius = min(width, height) * 0.28

        accent = QColor(self.theme.accent)

        # Pulse calculations based on config
        wave = self.config.wave_strength / 50.0
        pulse = math.sin(self._phase * (1.8 if self.is_speaking else 1.0)) * 6.0 * wave
        current_radius = base_radius + pulse

        # Outer Radial Glow
        outer_grad = QRadialGradient(QPointF(cx, cy), current_radius * 1.8)
        c_glow = QColor(accent)
        c_glow.setAlpha(60 if self.is_speaking else 35)
        c_transparent = QColor(accent)
        c_transparent.setAlpha(0)
        outer_grad.setColorAt(0.0, c_glow)
        outer_grad.setColorAt(1.0, c_transparent)
        painter.setBrush(outer_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), current_radius * 1.8, current_radius * 1.8)

        # Orbiting Energy Rings
        ring_count = 3
        for i in range(ring_count):
            r_x = current_radius * (1.1 + i * 0.15)
            r_y = current_radius * (0.6 + i * 0.2)

            painter.save()
            painter.translate(cx, cy)
            painter.rotate(math.degrees(self._phase * 0.2) + i * 60)
            pen_color = QColor(accent)
            pen_color.setAlpha(180 - i * 40)
            painter.setPen(QPen(pen_color, 2, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(0, 0), r_x, r_y)
            painter.restore()

        # Core Orb Gradient
        core_grad = QRadialGradient(
            QPointF(cx - current_radius * 0.3, cy - current_radius * 0.3),
            current_radius * 1.3,
        )
        c_core_bright = QColor("#ffffff")
        c_core_mid = QColor(accent)
        c_core_dark = QColor(self.theme.accent_soft)
        core_grad.setColorAt(0.0, c_core_bright)
        core_grad.setColorAt(0.35, c_core_mid)
        core_grad.setColorAt(1.0, c_core_dark)

        painter.setBrush(core_grad)
        painter.setPen(QPen(accent.lighter(130), 2))
        painter.drawEllipse(QPointF(cx, cy), current_radius, current_radius)

        # Status text below orb
        painter.setPen(QPen(QColor(self.theme.muted)))
        font = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        painter.setFont(font)
        text_rect = QRectF(0, cy + current_radius + 18, width, 30)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.status_text)
