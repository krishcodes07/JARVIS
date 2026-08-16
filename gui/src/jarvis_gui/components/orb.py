"""Runtime-drawn animated energy orb used as the JARVIS visualizer."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from jarvis_gui.config import UIConfig
from jarvis_gui.themes import Theme


class JarvisOrb(QWidget):
    """Animated, theme-aware visualizer with no external image dependencies."""

    def __init__(self, theme: Theme, config: UIConfig, parent=None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.config = config
        self._phase = 0.0
        self._status = "ONLINE • READY"
        self._speaking = False
        self._speech_level = 0.0
        self._voice_bands = [0.0] * 56
        self.setMinimumSize(380, 310)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._advance)
        self._timer.start(20)

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def set_status(self, status: str) -> None:
        self._status = status.upper()
        self.update()

    def set_speaking(self, speaking: bool) -> None:
        """Blend the orb into or out of its voice-reactive animation."""

        self._speaking = speaking
        self.update()

    def apply_settings(self, theme: Theme, config: UIConfig) -> None:
        self.theme = theme
        self.config = config
        self.update()

    def _advance(self) -> None:
        speed = 0.008 + (self.config.animation_speed / 100.0) * 0.036
        if self._speaking:
            speed *= 1.45
            syllable = abs(
                math.sin(self._phase * 3.8)
                + 0.58 * math.sin(self._phase * 7.6 + 0.9)
                + 0.28 * math.sin(self._phase * 13.4 + 2.1)
            )
            target_level = 0.18 + 0.82 * min(1.0, syllable / 1.35)
        else:
            target_level = 0.0
        blend = 0.34 if target_level > self._speech_level else 0.16
        self._speech_level += (target_level - self._speech_level) * blend
        for band_index, current in enumerate(self._voice_bands):
            if self._speaking:
                frequency_shape = (
                    0.55
                    + 0.28 * math.sin(band_index * 0.47 + self._phase * 2.7)
                    + 0.17 * math.sin(band_index * 1.13 - self._phase * 4.1)
                )
                transient = 0.42 + 0.58 * abs(
                    math.sin(self._phase * 8.8 + band_index * 0.31)
                )
                band_target = max(
                    0.04,
                    min(1.0, target_level * frequency_shape * transient),
                )
                band_blend = 0.38 if band_target > current else 0.2
            else:
                band_target = 0.0
                band_blend = 0.13
            self._voice_bands[band_index] = current + (
                band_target - current
            ) * band_blend
        self._phase = (self._phase + speed) % (math.tau * 10)
        self.update()

    @staticmethod
    def _with_alpha(color: QColor, alpha: int) -> QColor:
        result = QColor(color)
        result.setAlpha(max(0, min(255, alpha)))
        return result

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        center = QPointF(self.width() / 2, self.height() / 2 - 8)
        radius = min(self.width() * 0.25, self.height() * 0.36, 154.0)
        accent = QColor(self.theme.accent)

        style = self.config.blob_style
        if style == "Particle Cloud":
            self._draw_particles(painter, center, radius, accent, multiplier=1.55)
            self._draw_rings(painter, center, radius, accent, ring_count=3, width_scale=0.7)
        elif style == "Core Pulse":
            self._draw_core(painter, center, radius, accent)
            self._draw_rings(painter, center, radius, accent, ring_count=4, width_scale=1.2)
            self._draw_particles(painter, center, radius, accent, multiplier=0.55)
        else:
            self._draw_particles(painter, center, radius, accent, multiplier=1.0)
            self._draw_rings(painter, center, radius, accent, ring_count=6, width_scale=1.0)

        self._draw_voice_spectrum(painter, center, radius, accent)
        self._draw_brand(painter, center, radius, accent)

    def _draw_ambient_glow(
        self, painter: QPainter, center: QPointF, radius: float, accent: QColor
    ) -> None:
        glow = QRadialGradient(center, radius * 1.5)
        glow.setColorAt(0.0, self._with_alpha(accent, 28))
        glow.setColorAt(0.55, self._with_alpha(accent, 10))
        glow.setColorAt(1.0, self._with_alpha(accent, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(center, radius * 1.5, radius * 1.5)

    def _draw_shadow(
        self, painter: QPainter, center: QPointF, radius: float, accent: QColor
    ) -> None:
        shadow_center = QPointF(center.x(), center.y() + radius + 34)
        gradient = QRadialGradient(shadow_center, radius * 0.72)
        gradient.setColorAt(0.0, self._with_alpha(accent, 120))
        gradient.setColorAt(0.32, self._with_alpha(accent, 46))
        gradient.setColorAt(1.0, self._with_alpha(accent, 0))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            QRectF(
                shadow_center.x() - radius * 0.72,
                shadow_center.y() - 10,
                radius * 1.44,
                20,
            )
        )

    def _wave_path(
        self,
        center: QPointF,
        radius: float,
        index: int,
        phase: float,
    ) -> QPainterPath:
        path = QPainterPath()
        points = 180
        strength = 0.035 + self.config.wave_strength / 1000.0
        voice = self._speech_level
        vertical_scale = 1.0 + voice * (
            0.035 + 0.055 * abs(math.sin(phase * 4.2))
        )
        layer_bounce = radius * 0.025 * voice * math.sin(
            phase * 5.7 + index * 0.9
        )
        for step in range(points + 1):
            angle = math.tau * step / points
            wave = (
                math.sin(angle * (3 + index % 3) + phase * (1.0 + index * 0.07))
                + 0.54 * math.sin(angle * (7 + index) - phase * 1.35)
                + 0.22 * math.cos(angle * 13 + index * 1.7 + phase * 0.55)
            )
            idle_blend = 1.0 - voice * 0.38
            local_radius = (
                radius
                * (0.88 + index * 0.023)
                * (1 + strength * idle_blend * wave)
            )
            traveling_wave = (
                0.7 * math.sin(angle * 4.0 - phase * 7.2 + index * 0.42)
                + 0.3 * math.sin(angle * 8.0 + phase * 4.8 - index * 0.7)
            )
            side_envelope = 0.22 + 0.78 * abs(math.cos(angle))
            vertical_wave = (
                radius
                * 0.065
                * voice
                * traveling_wave
                * side_envelope
            )
            point = QPointF(
                center.x() + math.cos(angle) * local_radius,
                center.y()
                + math.sin(angle) * local_radius * vertical_scale
                + vertical_wave
                + layer_bounce,
            )
            if step == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        path.closeSubpath()
        return path

    def _draw_voice_spectrum(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        accent: QColor,
    ) -> None:
        """Draw a circular equalizer whose short strokes rise and fall to speech."""

        if self._speech_level < 0.015:
            return
        painter.setBrush(Qt.BrushStyle.NoBrush)
        count = len(self._voice_bands)
        for band_index, level in enumerate(self._voice_bands):
            angle = math.tau * band_index / count - math.pi / 2
            base_radius = radius * 1.015
            stroke_length = radius * (0.022 + 0.135 * level)
            inner_radius = base_radius - stroke_length * 0.24
            outer_radius = base_radius + stroke_length
            start = QPointF(
                center.x() + math.cos(angle) * inner_radius,
                center.y() + math.sin(angle) * inner_radius,
            )
            end = QPointF(
                center.x() + math.cos(angle) * outer_radius,
                center.y() + math.sin(angle) * outer_radius,
            )
            color = accent.lighter(135 + band_index % 4 * 7)
            color.setAlpha(int(48 + 172 * level * self._speech_level))
            pen = QPen(color, 1.0 + level * 1.35)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(start, end)

    def _draw_rings(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        accent: QColor,
        *,
        ring_count: int,
        width_scale: float,
    ) -> None:
        for index in range(ring_count):
            path = self._wave_path(center, radius, index, self._phase + index * 0.8)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            color = accent.lighter(108 + index * 5)
            color.setAlpha(
                min(230, max(58, 175 - index * 19) + int(self._speech_level * 22))
            )
            reactive_width = 1 + self._speech_level * (
                0.22 + 0.18 * abs(math.sin(self._phase * 7 + index))
            )
            line_pen = QPen(
                color,
                max(
                    0.65,
                    (1.55 - index * 0.12) * width_scale * reactive_width,
                ),
            )
            line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(line_pen)
            painter.drawPath(path)

    def _draw_particles(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        accent: QColor,
        *,
        multiplier: float,
    ) -> None:
        count = int((45 + self.config.particle_density * 2.1) * multiplier)
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(count):
            seed = index * 12.9898
            angle = (seed * 0.618033 + self._phase * (0.12 + (index % 5) * 0.018)) % math.tau
            pseudo = abs(math.sin(seed * 78.233))
            band = 0.73 + pseudo * 0.55
            ripple = 1 + 0.05 * math.sin(self._phase * 1.7 + index)
            distance = radius * band * ripple
            point = QPointF(
                center.x() + math.cos(angle) * distance,
                center.y() + math.sin(angle) * distance,
            )
            alpha = int(35 + 155 * abs(math.sin(index * 0.87 + self._phase * 1.4)))
            dot_radius = 0.5 + (index % 4) * 0.24
            painter.setBrush(self._with_alpha(accent.lighter(120 + index % 3 * 18), alpha))
            painter.drawEllipse(point, dot_radius, dot_radius)

    def _draw_core(
        self, painter: QPainter, center: QPointF, radius: float, accent: QColor
    ) -> None:
        pulse = 0.92 + math.sin(self._phase * 2.2) * 0.05
        core_radius = radius * 0.58 * pulse
        painter.setPen(QPen(self._with_alpha(accent, 90), 1.0))
        painter.setBrush(self._with_alpha(QColor(self.theme.surface_alt), 90))
        painter.drawEllipse(center, core_radius, core_radius)

    def _draw_brand(
        self, painter: QPainter, center: QPointF, radius: float, accent: QColor
    ) -> None:
        title_font = QFont("Segoe UI", max(15, int(radius * 0.13)), QFont.Weight.Medium)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(5, radius * 0.045))
        painter.setFont(title_font)
        painter.setPen(QPen(QColor(self.theme.text)))
        title_rect = QRectF(center.x() - radius, center.y() - 24, radius * 2, 42)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "JARVIS")

        status_font = QFont("Segoe UI", max(7, int(radius * 0.057)), QFont.Weight.DemiBold)
        status_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
        painter.setFont(status_font)
        painter.setPen(QPen(self._with_alpha(accent, 180)))
        status_rect = QRectF(center.x() - radius, center.y() + 25, radius * 2, 22)
        painter.drawText(status_rect, Qt.AlignmentFlag.AlignCenter, self._status)
