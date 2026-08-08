"""A small reusable button that paints crisp dependency-free line icons."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton

from jarvis_gui.themes import Theme


class GlowIconButton(QAbstractButton):
    """Rounded icon button with hover and optional accent glow states."""

    def __init__(
        self,
        icon_name: str,
        theme: Theme,
        *,
        size: int = 50,
        checkable: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.icon_name = icon_name
        self.theme = theme
        self._hovered = False
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        active = self._hovered or self.isChecked()

        border = self.theme.accent if active else self.theme.border
        background = self.theme.surface_alt if active else self.theme.surface
        painter.setPen(QPen(QColor(border), 1.0))
        painter.setBrush(QColor(background))
        painter.drawRoundedRect(rect, 9, 9)

        color = QColor(self.theme.accent if active else self.theme.muted)
        pen = QPen(color, max(1.5, self.width() / 28), Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        self._draw_icon(painter, QRectF(self.rect()))

    def _draw_icon(self, painter: QPainter, rect: QRectF) -> None:
        cx, cy = rect.center().x(), rect.center().y()
        unit = rect.width() / 50.0
        name = self.icon_name

        if name == "menu":
            for offset in (-8, 0, 8):
                painter.drawLine(QPointF(cx - 10 * unit, cy + offset * unit), QPointF(cx + 10 * unit, cy + offset * unit))
        elif name == "close":
            painter.drawLine(QPointF(cx - 8 * unit, cy - 8 * unit), QPointF(cx + 8 * unit, cy + 8 * unit))
            painter.drawLine(QPointF(cx + 8 * unit, cy - 8 * unit), QPointF(cx - 8 * unit, cy + 8 * unit))
        elif name == "back":
            painter.drawLine(QPointF(cx + 9 * unit, cy), QPointF(cx - 8 * unit, cy))
            painter.drawLine(QPointF(cx - 8 * unit, cy), QPointF(cx - 1 * unit, cy - 7 * unit))
            painter.drawLine(QPointF(cx - 8 * unit, cy), QPointF(cx - 1 * unit, cy + 7 * unit))
        elif name == "settings":
            painter.drawEllipse(QPointF(cx, cy), 5 * unit, 5 * unit)
            painter.drawEllipse(QPointF(cx, cy), 11 * unit, 11 * unit)
            for index in range(8):
                painter.save()
                painter.translate(cx, cy)
                painter.rotate(index * 45)
                painter.drawLine(QPointF(0, -11 * unit), QPointF(0, -15 * unit))
                painter.restore()
        elif name == "send":
            painter.drawEllipse(QPointF(cx, cy), 15 * unit, 15 * unit)
            painter.drawLine(QPointF(cx, cy + 8 * unit), QPointF(cx, cy - 8 * unit))
            painter.drawLine(QPointF(cx, cy - 8 * unit), QPointF(cx - 6 * unit, cy - 2 * unit))
            painter.drawLine(QPointF(cx, cy - 8 * unit), QPointF(cx + 6 * unit, cy - 2 * unit))
        elif name == "attach":
            path = QPainterPath(QPointF(cx + 8 * unit, cy - 5 * unit))
            path.cubicTo(
                QPointF(cx + 11 * unit, cy - 13 * unit),
                QPointF(cx + 1 * unit, cy - 15 * unit),
                QPointF(cx - 4 * unit, cy - 8 * unit),
            )
            path.lineTo(QPointF(cx - 10 * unit, cy + 1 * unit))
            path.cubicTo(
                QPointF(cx - 17 * unit, cy + 12 * unit),
                QPointF(cx - 1 * unit, cy + 18 * unit),
                QPointF(cx + 5 * unit, cy + 7 * unit),
            )
            path.lineTo(QPointF(cx + 10 * unit, cy - 1 * unit))
            painter.drawPath(path)
            painter.drawLine(QPointF(cx - 5 * unit, cy + 5 * unit), QPointF(cx + 5 * unit, cy - 8 * unit))
        elif name == "mic":
            painter.drawRoundedRect(QRectF(cx - 5 * unit, cy - 12 * unit, 10 * unit, 20 * unit), 5 * unit, 5 * unit)
            painter.drawArc(QRectF(cx - 10 * unit, cy - 7 * unit, 20 * unit, 20 * unit), 180 * 16, 180 * 16)
            painter.drawLine(QPointF(cx, cy + 13 * unit), QPointF(cx, cy + 18 * unit))
            painter.drawLine(QPointF(cx - 6 * unit, cy + 18 * unit), QPointF(cx + 6 * unit, cy + 18 * unit))
        elif name == "new":
            painter.drawLine(QPointF(cx - 9 * unit, cy), QPointF(cx + 9 * unit, cy))
            painter.drawLine(QPointF(cx, cy - 9 * unit), QPointF(cx, cy + 9 * unit))
        else:
            painter.drawEllipse(QPointF(cx, cy), 3 * unit, 3 * unit)
