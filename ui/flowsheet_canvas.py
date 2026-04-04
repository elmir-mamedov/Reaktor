from __future__ import annotations
import math
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (QGraphicsScene, QGraphicsView, QGraphicsItem,
                              QGraphicsLineItem, QMenu)
from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF, pyqtSignal
from PyQt6.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                          QTransform, QAction, QPainterPath)

from PyQt6.QtGui import QPolygonF
from models.reaction import CustomReaction, default_reaction, default_cstr_reaction
from models.heater import HeaterConfig
from models.flash import FlashConfig
from models.absorption import AbsorptionConfig

# ── Batch reactor geometry ────────────────────────────────────────────────────
_W = 64       # vessel body width
_H = 90       # vessel body height
_EH = 20      # ellipse height at top and bottom

# ── CSTR geometry ─────────────────────────────────────────────────────────────
_CW = 72      # CSTR vessel width
_CH = 78      # CSTR vessel height
_CEH = 18     # CSTR ellipse height

# ── Heater/Cooler geometry ────────────────────────────────────────────────────
_HW = 90      # heater body width
_HH = 46      # heater body height

# ── Flash Separator geometry ──────────────────────────────────────────────────
_FW = 70      # flash body width
_FH = 90      # flash body height

_PORT_RADIUS = 12   # px — how close cursor must be to snap to a port

# ── Absorption Column geometry ────────────────────────────────────────────────
_ACW = 56     # column body width
_ACH = 100    # column body height


class BatchReactorItem(QGraphicsItem):
    """PFD symbol for a batch reactor, rendered with a custom painter."""

    MIME_KEY = "batch_reactor"

    def __init__(self, name: str = "R-100", scene: FlowsheetScene = None):
        super().__init__()
        self.name = name
        self.reaction = default_reaction()
        self._scene_ref = scene
        self._hovered = False
        self._connected_streams: list[StreamItem] = []
        self._last_results = None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    # ── bounding rect / shape ─────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return QRectF(-_W / 2 - 8, -_H / 2 - 26, _W + 16, _H + 52)

    # ── events ────────────────────────────────────────────────────────────

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for stream in self._connected_streams:
                stream.prepareGeometryChange()
                stream.update()
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if self._scene_ref is not None:
                if value:
                    self._scene_ref._notify_selected(self)
                else:
                    if not self._scene_ref.selectedItems():
                        self._scene_ref._notify_deselected()
        return super().itemChange(change, value)

    # ── painting ──────────────────────────────────────────────────────────

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        selected = self.isSelected()
        hovered = self._hovered

        if selected:
            body_fill = QColor("#85c1e9")
            border = QColor("#154360")
            bw = 2.5
        elif hovered:
            body_fill = QColor("#aed6f1")
            border = QColor("#1a5276")
            bw = 2.0
        else:
            body_fill = QColor("#d6eaf8")
            border = QColor("#2980b9")
            bw = 1.5

        pen = QPen(border, bw)
        brush = QBrush(body_fill)
        painter.setPen(pen)
        painter.setBrush(brush)

        w, h, eh = _W, _H, _EH

        painter.drawRect(QRectF(-w / 2, -h / 2 + eh / 2, w, h - eh))
        painter.drawEllipse(QRectF(-w / 2, -h / 2, w, eh))
        painter.drawEllipse(QRectF(-w / 2, h / 2 - eh, w, eh))
        painter.drawRect(QRectF(-5, -h / 2 - 18, 10, 18))

        agit_pen = QPen(border, 1.2)
        painter.setPen(agit_pen)
        shaft_top = -h / 2 + eh / 2
        shaft_bot = h / 2 - eh / 2
        painter.drawLine(QPointF(0, shaft_top), QPointF(0, shaft_bot))
        blen = w * 0.36
        for blade_y in (-h * 0.18, h * 0.18):
            painter.drawLine(QPointF(-blen, blade_y), QPointF(blen, blade_y))

        if selected:
            sel_pen = QPen(QColor("#3498db"), 1.2, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(3, 3, -3, -3))

        painter.setPen(QPen(QColor("#1a3a5c")))
        painter.setFont(QFont("", 9, QFont.Weight.Bold))
        painter.drawText(QRectF(-w / 2, h / 2 + 6, w, 18),
                         Qt.AlignmentFlag.AlignCenter, self.name)

        painter.setFont(QFont("", 7))
        painter.setPen(QPen(QColor("#5d6d7e")))
        rstr = self.reaction.reaction_label()
        if len(rstr) > 12:
            rstr = rstr[:11] + "…"
        painter.drawText(QRectF(-w / 2, -h / 2 + eh + 3, w, 14),
                         Qt.AlignmentFlag.AlignCenter, rstr)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _draw_arrowhead(painter: QPainter, tip_x: float, tip_y: float,
                    size: float, color: QColor):
    """Draw a rightward arrowhead with its tip at (tip_x, tip_y)."""
    poly = QPolygonF([
        QPointF(tip_x, tip_y),
        QPointF(tip_x - size, tip_y - size * 0.5),
        QPointF(tip_x - size, tip_y + size * 0.5),
    ])
    painter.setPen(QPen(color, 0))
    painter.setBrush(QBrush(color))
    painter.drawPolygon(poly)


def _draw_arrowhead_dir(painter: QPainter, tip: QPointF,
                        direction: QPointF, size: float, color: QColor):
    """Draw an arrowhead at tip pointing in the given direction."""
    length = math.sqrt(direction.x() ** 2 + direction.y() ** 2)
    if length < 1e-9:
        return
    dx, dy = direction.x() / length, direction.y() / length
    px, py = -dy, dx          # perpendicular
    poly = QPolygonF([
        QPointF(tip.x(), tip.y()),
        QPointF(tip.x() - size * dx + size * 0.45 * px,
                tip.y() - size * dy + size * 0.45 * py),
        QPointF(tip.x() - size * dx - size * 0.45 * px,
                tip.y() - size * dy - size * 0.45 * py),
    ])
    painter.setPen(QPen(color, 0))
    painter.setBrush(QBrush(color))
    painter.drawPolygon(poly)


class CSTRReactorItem(QGraphicsItem):
    """PFD symbol for a CSTR (Continuous Stirred Tank Reactor)."""

    MIME_KEY = "cstr_reactor"

    def __init__(self, name: str = "R-100", scene=None):
        super().__init__()
        self.name = name
        self.reaction = default_cstr_reaction()
        self._scene_ref = scene
        self._hovered = False
        self._connected_streams: list[StreamItem] = []
        self._last_results = None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        return QRectF(-_CW / 2 - 30, -_CH / 2 - 10, _CW + 60, _CH + 42)

    def input_scene_ports(self) -> list[QPointF]:
        """Input port positions in scene coordinates."""
        return [self.mapToScene(QPointF(-_CW / 2 - 22, -_CH / 4))]

    def output_scene_ports(self) -> list[QPointF]:
        """Output port positions in scene coordinates."""
        return [self.mapToScene(QPointF(_CW / 2 + 22, _CH / 4))]

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for stream in self._connected_streams:
                stream.prepareGeometryChange()
                stream.update()
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if self._scene_ref is not None:
                if value:
                    self._scene_ref._notify_selected(self)
                else:
                    if not self._scene_ref.selectedItems():
                        self._scene_ref._notify_deselected()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        selected = self.isSelected()
        hovered = self._hovered

        if selected:
            body_fill = QColor("#a9dfbf")
            border = QColor("#145a32")
            bw = 2.5
        elif hovered:
            body_fill = QColor("#abebc6")
            border = QColor("#1e8449")
            bw = 2.0
        else:
            body_fill = QColor("#d5f5e3")
            border = QColor("#27ae60")
            bw = 1.5

        pen = QPen(border, bw)
        brush = QBrush(body_fill)
        painter.setPen(pen)
        painter.setBrush(brush)

        w, h, eh = _CW, _CH, _CEH

        painter.drawRect(QRectF(-w / 2, -h / 2 + eh / 2, w, h - eh))
        painter.drawEllipse(QRectF(-w / 2, -h / 2, w, eh))
        painter.drawEllipse(QRectF(-w / 2, h / 2 - eh, w, eh))

        inlet_y = -h / 4
        painter.setPen(QPen(border, bw))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(-w / 2 - 22, inlet_y), QPointF(-w / 2, inlet_y))
        _draw_arrowhead(painter, -w / 2 + 1, inlet_y, 6, border)

        outlet_y = h / 4
        painter.setPen(QPen(border, bw))
        painter.drawLine(QPointF(w / 2, outlet_y), QPointF(w / 2 + 22, outlet_y))
        _draw_arrowhead(painter, w / 2 + 22, outlet_y, 6, border)

        painter.setPen(QPen(border, 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        shaft_top = -h / 2 + eh / 2
        shaft_bot = h / 2 - eh / 2
        painter.drawLine(QPointF(0, shaft_top), QPointF(0, shaft_bot))
        blen = w * 0.36
        for blade_y in (-h * 0.15, h * 0.15):
            painter.drawLine(QPointF(-blen, blade_y), QPointF(blen, blade_y))

        if selected:
            sel_pen = QPen(QColor("#2ecc71"), 1.2, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(3, 3, -3, -3))

        painter.setPen(QPen(QColor("#145a32")))
        painter.setFont(QFont("", 9, QFont.Weight.Bold))
        painter.drawText(QRectF(-w / 2, h / 2 + 6, w, 18),
                         Qt.AlignmentFlag.AlignCenter, self.name)

        painter.setFont(QFont("", 7))
        painter.setPen(QPen(QColor("#5d6d7e")))
        rstr = self.reaction.reaction_label()
        if len(rstr) > 12:
            rstr = rstr[:11] + "…"
        painter.drawText(QRectF(-w / 2, -h / 2 + eh + 3, w, 14),
                         Qt.AlignmentFlag.AlignCenter, rstr)

        # Port indicators (shown when hovered or selected)
        if hovered or selected:
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(QPen(border, 1.5))
            painter.drawEllipse(QPointF(-w / 2 - 22, -h / 4), 5, 5)
            painter.drawEllipse(QPointF(w / 2 + 22, h / 4), 5, 5)


def _draw_wave_line(painter: QPainter, x0: float, y0: float,
                    width: float, amplitude: float, n_waves: int):
    """Draw a horizontal sine-like wave using cubic bezier segments."""
    path = QPainterPath()
    path.moveTo(x0, y0)
    seg = width / (n_waves * 2)
    for i in range(n_waves * 2):
        sign = 1 if i % 2 == 0 else -1
        path.cubicTo(
            x0 + i * seg + seg * 0.4, y0 + sign * amplitude,
            x0 + i * seg + seg * 0.6, y0 + sign * amplitude,
            x0 + (i + 1) * seg,       y0,
        )
    painter.drawPath(path)


class HeaterCoolerItem(QGraphicsItem):
    """PFD symbol for a Heater/Cooler block."""

    MIME_KEY = "heater_cooler"

    def __init__(self, name: str = "H-100", scene=None):
        super().__init__()
        self.name = name
        self.config = HeaterConfig()
        self._scene_ref = scene
        self._hovered = False
        self._connected_streams: list[StreamItem] = []
        self._last_results = None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        return QRectF(-_HW / 2 - 30, -_HH / 2 - 8, _HW + 60, _HH + 36)

    def output_scene_ports(self) -> list[QPointF]:
        """Output port positions in scene coordinates."""
        return [self.mapToScene(QPointF(_HW / 2 + 22, 0))]

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for stream in self._connected_streams:
                stream.prepareGeometryChange()
                stream.update()
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if self._scene_ref is not None:
                if value:
                    self._scene_ref._notify_selected(self)
                else:
                    if not self._scene_ref.selectedItems():
                        self._scene_ref._notify_deselected()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        selected = self.isSelected()
        hovered = self._hovered

        if selected:
            body_fill = QColor("#f0b27a")
            border = QColor("#a04000")
            bw = 2.5
        elif hovered:
            body_fill = QColor("#fad7a0")
            border = QColor("#d35400")
            bw = 2.0
        else:
            body_fill = QColor("#fdebd0")
            border = QColor("#e67e22")
            bw = 1.5

        pen = QPen(border, bw)
        w, h = _HW, _HH

        painter.setPen(pen)
        painter.setBrush(QBrush(body_fill))
        painter.drawRect(QRectF(-w / 2, -h / 2, w, h))

        painter.setPen(QPen(border, bw))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(-w / 2 - 22, 0), QPointF(-w / 2, 0))
        _draw_arrowhead(painter, -w / 2 + 1, 0, 6, border)

        painter.setPen(QPen(border, bw))
        painter.drawLine(QPointF(w / 2, 0), QPointF(w / 2 + 22, 0))
        _draw_arrowhead(painter, w / 2 + 22, 0, 6, border)

        painter.setPen(QPen(border, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inner_w = w - 16
        x0 = -inner_w / 2
        for wave_y in (-h / 5, h / 5):
            _draw_wave_line(painter, x0, wave_y, inner_w, h / 9, 3)

        if selected:
            sel_pen = QPen(QColor("#e67e22"), 1.2, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(3, 3, -3, -3))

        painter.setPen(QPen(QColor("#784212")))
        painter.setFont(QFont("", 9, QFont.Weight.Bold))
        painter.drawText(QRectF(-w / 2, h / 2 + 4, w, 18),
                         Qt.AlignmentFlag.AlignCenter, self.name)

        painter.setFont(QFont("", 7))
        painter.setPen(QPen(QColor("#784212")))
        hint = f"\u2192 {self.config.T_target:.1f} K"
        painter.drawText(QRectF(-w / 2, -h / 2 + 3, w, 14),
                         Qt.AlignmentFlag.AlignCenter, hint)

        # Output port indicator (shown when hovered or selected)
        if hovered or selected:
            port_local = QPointF(w / 2 + 22, 0)
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(QPen(border, 1.5))
            painter.drawEllipse(port_local, 5, 5)


# ── Flash Separator ───────────────────────────────────────────────────────────

class FlashSeparatorItem(QGraphicsItem):
    """PFD symbol for a single-stage flash separator."""

    MIME_KEY = "flash_separator"

    def __init__(self, name: str = "F-100", scene=None):
        super().__init__()
        self.name = name
        self.config = FlashConfig()
        self._scene_ref = scene
        self._hovered = False
        self._connected_streams: list = []
        self._last_results = None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        return QRectF(-_FW / 2 - 30, -_FH / 2 - 26, _FW + 60, _FH + 52)

    def input_scene_ports(self) -> list[QPointF]:
        """Feed inlet port on the left side."""
        return [self.mapToScene(QPointF(-_FW / 2 - 22, 0))]

    def output_scene_ports(self) -> list[QPointF]:
        """Vapor port (top right) and liquid port (bottom right)."""
        return [
            self.mapToScene(QPointF(_FW / 2 + 22, -_FH / 4)),  # vapor
            self.mapToScene(QPointF(_FW / 2 + 22,  _FH / 4)),  # liquid
        ]

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for stream in self._connected_streams:
                stream.prepareGeometryChange()
                stream.update()
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if self._scene_ref is not None:
                if value:
                    self._scene_ref._notify_selected(self)
                else:
                    if not self._scene_ref.selectedItems():
                        self._scene_ref._notify_deselected()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = self.isSelected()
        hovered = self._hovered

        if selected:
            body_fill = QColor("#aed6f1")
            border = QColor("#1a5276")
            bw = 2.5
        elif hovered:
            body_fill = QColor("#d6eaf8")
            border = QColor("#2980b9")
            bw = 2.0
        else:
            body_fill = QColor("#ebf5fb")
            border = QColor("#5dade2")
            bw = 1.5

        w, h = _FW, _FH

        # Trapezoid: wider at top, narrower at bottom
        trap = QPolygonF([
            QPointF(-w / 2,       -h / 2),   # top-left
            QPointF( w / 2,       -h / 2),   # top-right
            QPointF( w / 2 - 10,   h / 2),   # bottom-right
            QPointF(-w / 2 + 10,   h / 2),   # bottom-left
        ])
        painter.setPen(QPen(border, bw))
        painter.setBrush(QBrush(body_fill))
        painter.drawPolygon(trap)

        # Horizontal dividing line (vapor / liquid)
        painter.setPen(QPen(border, 1.0, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(-w / 2 + 4, 0), QPointF(w / 2 - 4, 0))

        # Phase labels
        painter.setFont(QFont("", 7, QFont.Weight.Bold))
        painter.setPen(QPen(QColor("#1a5276")))
        painter.drawText(QRectF(-w / 2, -h / 2 + 4, w, 14),
                         Qt.AlignmentFlag.AlignCenter, "V")
        painter.drawText(QRectF(-w / 2 + 10, h / 2 - 18, w - 10, 14),
                         Qt.AlignmentFlag.AlignCenter, "L")

        # Feed inlet pipe (left center)
        painter.setPen(QPen(border, bw))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(-w / 2 - 22, 0), QPointF(-w / 2, 0))
        _draw_arrowhead(painter, -w / 2 + 1, 0, 6, border)

        # Vapor outlet (top right)
        painter.drawLine(QPointF(w / 2, -h / 4), QPointF(w / 2 + 22, -h / 4))
        _draw_arrowhead(painter, w / 2 + 22, -h / 4, 6, border)

        # Liquid outlet (bottom right)
        painter.drawLine(QPointF(w / 2 - 10, h / 4), QPointF(w / 2 + 22, h / 4))
        _draw_arrowhead(painter, w / 2 + 22, h / 4, 6, border)

        if selected:
            painter.setPen(QPen(QColor("#2980b9"), 1.2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(3, 3, -3, -3))

        painter.setPen(QPen(QColor("#1a5276")))
        painter.setFont(QFont("", 9, QFont.Weight.Bold))
        painter.drawText(QRectF(-w / 2, h / 2 + 6, w, 18),
                         Qt.AlignmentFlag.AlignCenter, self.name)

        painter.setFont(QFont("", 7))
        painter.setPen(QPen(QColor("#5d6d7e")))
        painter.drawText(QRectF(-w / 2, -h / 2 - 18, w, 14),
                         Qt.AlignmentFlag.AlignCenter, f"T = {self.config.T:.0f} K")

        # Port indicators (shown when hovered or selected)
        if hovered or selected:
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(QPen(border, 1.5))
            painter.drawEllipse(QPointF(-w / 2 - 22, 0), 5, 5)
            painter.drawEllipse(QPointF(w / 2 + 22, -h / 4), 5, 5)
            painter.drawEllipse(QPointF(w / 2 + 22,  h / 4), 5, 5)


# ── Absorption Column ─────────────────────────────────────────────────────────

class AbsorptionColumnItem(QGraphicsItem):
    """PFD symbol for a packed absorption column (steady-state design block)."""

    MIME_KEY = "absorption_column"

    def __init__(self, name: str = "A-100", scene=None):
        super().__init__()
        self.name = name
        self.config = AbsorptionConfig()
        self._scene_ref = scene
        self._hovered = False
        self._connected_streams: list = []
        self._last_results = None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        return QRectF(-_ACW / 2 - 30, -_ACH / 2 - 26, _ACW + 60, _ACH + 52)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for stream in self._connected_streams:
                stream.prepareGeometryChange()
                stream.update()
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if self._scene_ref is not None:
                if value:
                    self._scene_ref._notify_selected(self)
                else:
                    if not self._scene_ref.selectedItems():
                        self._scene_ref._notify_deselected()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = self.isSelected()
        hovered  = self._hovered

        if selected:
            body_fill = QColor("#a2d9ce")
            border    = QColor("#0e6655")
            bw = 2.5
        elif hovered:
            body_fill = QColor("#c0ece5")
            border    = QColor("#148f77")
            bw = 2.0
        else:
            body_fill = QColor("#d1f2eb")
            border    = QColor("#1abc9c")
            bw = 1.5

        w, h = _ACW, _ACH
        pen   = QPen(border, bw)
        brush = QBrush(body_fill)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRect(QRectF(-w / 2, -h / 2, w, h))

        # Cross-hatch fill (packed-bed symbol) — 45° lines
        hatch_pen = QPen(border, 0.7)
        hatch_pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(hatch_pen)
        step = 10
        for i in range(-h, h + w, step):
            x1 = -w / 2
            y1 = -h / 2 + i
            x2 = x1 + h
            y2 = -h / 2
            # Clip to rectangle bounds with simple parametric approach
            painter.setClipRect(QRectF(-w / 2, -h / 2, w, h))
            painter.drawLine(QPointF(x1, y1), QPointF(x1 + w + h, y1 - w - h))
        painter.setClipping(False)

        # Port stub lines (drawn on top of hatch)
        painter.setPen(QPen(border, bw))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Liquid inlet — top left
        painter.drawLine(QPointF(-w / 2 - 22, -h / 4), QPointF(-w / 2, -h / 4))
        _draw_arrowhead(painter, -w / 2 + 1, -h / 4, 6, border)
        # Gas inlet — bottom right
        painter.drawLine(QPointF(w / 2, h / 4), QPointF(w / 2 + 22, h / 4))
        _draw_arrowhead(painter, w / 2 - 1, h / 4, 6, border)
        # Gas outlet — top right
        painter.drawLine(QPointF(w / 2, -h / 4), QPointF(w / 2 + 22, -h / 4))
        _draw_arrowhead(painter, w / 2 + 22, -h / 4, 6, border)
        # Liquid outlet — bottom left
        painter.drawLine(QPointF(-w / 2 - 22, h / 4), QPointF(-w / 2, h / 4))
        _draw_arrowhead(painter, -w / 2 - 22, h / 4, 6, border)

        # Name label below
        painter.setPen(QPen(QColor("#0e6655")))
        painter.setFont(QFont("", 9, QFont.Weight.Bold))
        painter.drawText(QRectF(-w / 2, h / 2 + 6, w, 18),
                         Qt.AlignmentFlag.AlignCenter, self.name)

        # Packing hint above
        painter.setFont(QFont("", 7))
        painter.setPen(QPen(QColor("#5d6d7e")))
        packing_short = self.config.packing.split()[0] + " " + self.config.packing.split()[1] \
            if len(self.config.packing.split()) >= 2 else self.config.packing
        painter.drawText(QRectF(-w / 2, -h / 2 - 18, w, 14),
                         Qt.AlignmentFlag.AlignCenter, packing_short)

        if selected:
            painter.setPen(QPen(QColor("#1abc9c"), 1.2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(3, 3, -3, -3))


# ── Stream ────────────────────────────────────────────────────────────────────

class StreamItem(QGraphicsItem):
    """A directed connection arrow between two unit operations."""

    def __init__(self, source, dest):
        super().__init__()
        self.source = source
        self.dest = dest
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        source._connected_streams.append(self)
        dest._connected_streams.append(self)

    def _bezier_data(self):
        """Return (path, p0, p3, cp2) computed from live port positions."""
        p0 = self.source.output_scene_ports()[0]
        p3 = self.dest.input_scene_ports()[0]
        dx = max(abs(p3.x() - p0.x()) * 0.5, 40.0)
        cp1 = QPointF(p0.x() + dx, p0.y())
        cp2 = QPointF(p3.x() - dx, p3.y())
        path = QPainterPath()
        path.moveTo(p0)
        path.cubicTo(cp1, cp2, p3)
        return path, p0, p3, cp2

    def boundingRect(self) -> QRectF:
        try:
            path, _, _, _ = self._bezier_data()
            return path.boundingRect().adjusted(-12, -12, 12, 12)
        except Exception:
            return QRectF(-5000, -5000, 10000, 10000)

    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            path, p0, p3, cp2 = self._bezier_data()
        except Exception:
            return

        color = QColor("#7f8c8d")
        painter.setPen(QPen(color, 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Arrowhead pointing from cp2 → p3
        direction = QPointF(p3.x() - cp2.x(), p3.y() - cp2.y())
        _draw_arrowhead_dir(painter, p3, direction, 8, color)


# ── Scene ─────────────────────────────────────────────────────────────────────

class FlowsheetScene(QGraphicsScene):
    reactor_selected = pyqtSignal(object)
    reactor_deselected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-2000, -2000, 4000, 4000)
        self._counter = 0
        self._streams: list[StreamItem] = []

    # ── unit creation ─────────────────────────────────────────────────────

    def add_reactor(self, pos: QPointF) -> BatchReactorItem:
        self._counter += 1
        item = BatchReactorItem(f"R-{100 + self._counter - 1}", scene=self)
        item.setPos(pos)
        self.addItem(item)
        return item

    def add_cstr(self, pos: QPointF) -> CSTRReactorItem:
        self._counter += 1
        item = CSTRReactorItem(f"R-{100 + self._counter - 1}", scene=self)
        item.setPos(pos)
        self.addItem(item)
        return item

    def add_heater(self, pos: QPointF) -> HeaterCoolerItem:
        self._counter += 1
        item = HeaterCoolerItem(f"H-{100 + self._counter - 1}", scene=self)
        item.setPos(pos)
        self.addItem(item)
        return item

    def add_flash(self, pos: QPointF) -> FlashSeparatorItem:
        self._counter += 1
        item = FlashSeparatorItem(f"F-{100 + self._counter - 1}", scene=self)
        item.setPos(pos)
        self.addItem(item)
        return item

    def add_absorption_column(self, pos: QPointF) -> AbsorptionColumnItem:
        self._counter += 1
        item = AbsorptionColumnItem(f"A-{100 + self._counter - 1}", scene=self)
        item.setPos(pos)
        self.addItem(item)
        return item

    # ── stream management ─────────────────────────────────────────────────

    def add_stream(self, source, dest) -> StreamItem:
        # Remove any existing connection to the same dest
        self.remove_streams_for(dest, role="dest")
        stream = StreamItem(source, dest)
        self._streams.append(stream)
        self.addItem(stream)
        return stream

    def remove_streams_for(self, item, role: str = "any"):
        """Remove streams connected to item (role: 'source', 'dest', or 'any')."""
        to_remove = []
        for s in self._streams:
            if role in ("any", "source") and s.source is item:
                to_remove.append(s)
            elif role in ("any", "dest") and s.dest is item:
                to_remove.append(s)
        for s in to_remove:
            if s.source in (s.source, item):
                s.source._connected_streams.discard if hasattr(
                    s.source._connected_streams, "discard") else None
                try:
                    s.source._connected_streams.remove(s)
                except ValueError:
                    pass
            try:
                s.dest._connected_streams.remove(s)
            except ValueError:
                pass
            self._streams.remove(s)
            self.removeItem(s)

    def get_upstream_heater(self, cstr: CSTRReactorItem):
        """Return the HeaterCoolerItem connected to cstr's input, or None."""
        for s in self._streams:
            if s.dest is cstr and isinstance(s.source, HeaterCoolerItem):
                return s.source
        return None

    def get_upstream_cstr(self, flash: FlashSeparatorItem):
        """Return the CSTRReactorItem connected to flash's input, or None."""
        for s in self._streams:
            if s.dest is flash and isinstance(s.source, CSTRReactorItem):
                return s.source
        return None

    # ── notifications ─────────────────────────────────────────────────────

    def _notify_selected(self, item):
        self.reactor_selected.emit(item)

    def _notify_deselected(self):
        self.reactor_deselected.emit()

    # ── context menu ──────────────────────────────────────────────────────

    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos(), QTransform())
        # Ignore clicks on stream arrows
        if isinstance(item, StreamItem):
            item = None
        menu = QMenu()

        if item is None:
            add_batch_act = QAction("Add Batch Reactor Here")
            add_cstr_act = QAction("Add CSTR Here")
            add_heater_act = QAction("Add Heater/Cooler Here")
            add_flash_act = QAction("Add Flash Separator Here")
            add_abs_act = QAction("Add Absorption Column Here")
            menu.addAction(add_batch_act)
            menu.addAction(add_cstr_act)
            menu.addAction(add_heater_act)
            menu.addAction(add_flash_act)
            menu.addAction(add_abs_act)
            chosen = menu.exec(event.screenPos())
            if chosen == add_batch_act:
                r = self.add_reactor(event.scenePos())
                self.clearSelection(); r.setSelected(True)
            elif chosen == add_cstr_act:
                r = self.add_cstr(event.scenePos())
                self.clearSelection(); r.setSelected(True)
            elif chosen == add_heater_act:
                r = self.add_heater(event.scenePos())
                self.clearSelection(); r.setSelected(True)
            elif chosen == add_flash_act:
                r = self.add_flash(event.scenePos())
                self.clearSelection(); r.setSelected(True)
            elif chosen == add_abs_act:
                r = self.add_absorption_column(event.scenePos())
                self.clearSelection(); r.setSelected(True)
        elif isinstance(item, (BatchReactorItem, CSTRReactorItem, HeaterCoolerItem,
                               FlashSeparatorItem, AbsorptionColumnItem)):
            del_act = QAction(f"Delete  {item.name}")
            menu.addAction(del_act)
            chosen = menu.exec(event.screenPos())
            if chosen == del_act:
                self.remove_streams_for(item)
                self.removeItem(item)
                self.reactor_deselected.emit()


# ── View ──────────────────────────────────────────────────────────────────────

class FlowsheetView(QGraphicsView):
    """Zoomable, pannable flowsheet canvas with drop and connection support."""

    def __init__(self, scene: FlowsheetScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAcceptDrops(True)

        self._mid_panning = False
        self._pan_origin = QPointF()

        # Connection drag state
        self._connecting = False
        self._conn_source = None
        self._conn_source_port: QPointF | None = None
        self._temp_line: QGraphicsLineItem | None = None

    # ── background grid ───────────────────────────────────────────────────

    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.fillRect(rect, QColor("#fafafa"))
        grid = 25
        left = int(rect.left()) - (int(rect.left()) % grid)
        top = int(rect.top()) - (int(rect.top()) % grid)
        dot_pen = QPen(QColor("#d5d8dc"), 1)
        painter.setPen(dot_pen)
        x = left
        while x <= int(rect.right()) + grid:
            y = top
            while y <= int(rect.bottom()) + grid:
                painter.drawPoint(x, y)
                y += grid
            x += grid

    # ── zoom ──────────────────────────────────────────────────────────────

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(factor, factor)

    # ── port detection ────────────────────────────────────────────────────

    def _port_at(self, scene_pos: QPointF):
        """Return (item, 'in'|'out') if scene_pos is near a port, else None."""
        sc = self.scene()
        for item in sc.items():
            if hasattr(item, "output_scene_ports"):
                for port in item.output_scene_ports():
                    if _dist(scene_pos, port) < _PORT_RADIUS:
                        return (item, "out")
            if hasattr(item, "input_scene_ports"):
                for port in item.input_scene_ports():
                    if _dist(scene_pos, port) < _PORT_RADIUS:
                        return (item, "in")
        return None

    # ── mouse events ──────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._mid_panning = True
            self._pan_origin = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            hit = self._port_at(scene_pos)
            if hit is not None and hit[1] == "out":
                # Start connection drag from output port
                self._connecting = True
                self._conn_source = hit[0]
                ports = hit[0].output_scene_ports()
                port = min(ports, key=lambda p: _dist(scene_pos, p))
                self._conn_source_port = port
                self._temp_line = self.scene().addLine(
                    QLineF(port, port),
                    QPen(QColor("#7f8c8d"), 1.5, Qt.PenStyle.DashLine))
                self.setCursor(Qt.CursorShape.CrossCursor)
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mid_panning:
            delta = event.position() - self._pan_origin
            self._pan_origin = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y()))
            return

        if self._connecting and self._temp_line is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            src_port = self._conn_source_port or self._conn_source.output_scene_ports()[0]
            self._temp_line.setLine(QLineF(src_port, scene_pos))
            # Highlight nearby input ports
            hit = self._port_at(scene_pos)
            if hit is not None and hit[1] == "in":
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._mid_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton and self._connecting:
            scene_pos = self.mapToScene(event.position().toPoint())
            hit = self._port_at(scene_pos)
            sc = self.scene()
            if self._temp_line is not None:
                sc.removeItem(self._temp_line)
                self._temp_line = None
            if hit is not None and hit[1] == "in":
                sc.add_stream(self._conn_source, hit[0])
            self._connecting = False
            self._conn_source = None
            self._conn_source_port = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        super().mouseReleaseEvent(event)

    # ── keyboard ──────────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            sc = self.scene()
            for item in list(sc.selectedItems()):
                if isinstance(item, (BatchReactorItem, CSTRReactorItem,
                                     HeaterCoolerItem, FlashSeparatorItem,
                                     AbsorptionColumnItem)):
                    sc.remove_streams_for(item)
                sc.removeItem(item)
            sc.reactor_deselected.emit()
        elif event.key() == Qt.Key.Key_F:
            self._fit_all()
        else:
            super().keyPressEvent(event)

    def _fit_all(self):
        sc = self.scene()
        br = sc.itemsBoundingRect()
        if not br.isNull():
            self.fitInView(br.adjusted(-80, -80, 80, 80),
                           Qt.AspectRatioMode.KeepAspectRatio)

    # ── drag-and-drop from palette ────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            mime = event.mimeData().text()
            sc = self.scene()
            if isinstance(sc, FlowsheetScene):
                pos = self.mapToScene(event.position().toPoint())
                if mime == BatchReactorItem.MIME_KEY:
                    reactor = sc.add_reactor(pos)
                elif mime == CSTRReactorItem.MIME_KEY:
                    reactor = sc.add_cstr(pos)
                elif mime == HeaterCoolerItem.MIME_KEY:
                    reactor = sc.add_heater(pos)
                elif mime == FlashSeparatorItem.MIME_KEY:
                    reactor = sc.add_flash(pos)
                elif mime == AbsorptionColumnItem.MIME_KEY:
                    reactor = sc.add_absorption_column(pos)
                else:
                    return
                sc.clearSelection()
                reactor.setSelected(True)
            event.acceptProposedAction()


# ── Utilities ─────────────────────────────────────────────────────────────────

def _dist(a: QPointF, b: QPointF) -> float:
    return math.sqrt((a.x() - b.x()) ** 2 + (a.y() - b.y()) ** 2)
