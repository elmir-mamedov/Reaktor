from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QMimeData, QPoint, QPointF
from PyQt6.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                          QDrag, QPixmap)


class EquipmentTile(QWidget):
    """A single draggable equipment icon in the palette."""

    def __init__(self, label: str, mime_key: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._mime_key = mime_key
        self._hovered = False
        self._drag_start: QPoint | None = None
        self.setFixedSize(130, 100)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setMouseTracking(True)

    # ── painting ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor("#ebf5fb") if self._hovered else QColor("#fdfefe")
        border = QColor("#2980b9") if self._hovered else QColor("#aab7b8")

        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 5, 5)

        self._draw_reactor_icon(painter, self.width() // 2, 40, 28, 40)

        painter.setPen(QPen(QColor("#1a3a5c")))
        painter.setFont(QFont("", 9, QFont.Weight.Bold))
        painter.drawText(0, self.height() - 18, self.width(), 18,
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                         self._label)
        painter.end()

    def _draw_reactor_icon(self, painter: QPainter, cx: int, cy: int, w: int, h: int):
        ew, eh = w, max(8, int(w * 0.32))

        painter.setPen(QPen(QColor("#1a5276"), 1.5))
        painter.setBrush(QBrush(QColor("#aed6f1")))

        # Body rectangle
        painter.drawRect(cx - w // 2, cy - h // 2 + eh // 2, w, h - eh)
        # Top + bottom ellipses
        painter.drawEllipse(cx - ew // 2, cy - h // 2, ew, eh)
        painter.drawEllipse(cx - ew // 2, cy + h // 2 - eh, ew, eh)

        # Agitator
        painter.setPen(QPen(QColor("#1a5276"), 1))
        shaft_top = cy - h // 2 + eh // 2
        shaft_bot = cy + h // 2 - eh // 2
        painter.drawLine(cx, shaft_top, cx, shaft_bot)
        mid = (shaft_top + shaft_bot) // 2
        blen = w // 3
        painter.drawLine(cx - blen, mid - 4, cx + blen, mid - 4)
        painter.drawLine(cx - blen, mid + 4, cx + blen, mid + 4)

    # ── drag support (uses self._draw_reactor_icon for pixmap) ───────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton
                and self._drag_start is not None
                and (event.position().toPoint() - self._drag_start).manhattanLength() >= 8):
            self._start_drag()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def _start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self._mime_key)
        drag.setMimeData(mime)

        pm = QPixmap(60, 80)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_reactor_icon(p, 30, 35, 44, 60)
        p.end()
        drag.setPixmap(pm)
        drag.setHotSpot(QPoint(30, 35))

        drag.exec(Qt.DropAction.CopyAction)

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()


class CSTREquipmentTile(EquipmentTile):
    """Palette tile for dragging a CSTR onto the flowsheet."""

    def _draw_reactor_icon(self, painter: QPainter, cx: int, cy: int, w: int, h: int):
        ew, eh = w, max(8, int(w * 0.32))

        painter.setPen(QPen(QColor("#1e8449"), 1.5))
        painter.setBrush(QBrush(QColor("#a9dfbf")))

        # Body + ellipses
        painter.drawRect(cx - w // 2, cy - h // 2 + eh // 2, w, h - eh)
        painter.drawEllipse(cx - ew // 2, cy - h // 2, ew, eh)
        painter.drawEllipse(cx - ew // 2, cy + h // 2 - eh, ew, eh)

        # Inlet pipe (upper left) with arrowhead
        inlet_y = cy - h // 4
        painter.setPen(QPen(QColor("#1e8449"), 1.5))
        painter.drawLine(cx - w // 2 - 10, inlet_y, cx - w // 2, inlet_y)
        # arrowhead pointing right
        from PyQt6.QtGui import QPolygonF
        from PyQt6.QtCore import QPointF as _QPointF
        tip = _QPointF(cx - w // 2 + 1, inlet_y)
        poly = QPolygonF([tip,
                          _QPointF(cx - w // 2 - 5, inlet_y - 3),
                          _QPointF(cx - w // 2 - 5, inlet_y + 3)])
        painter.setBrush(QBrush(QColor("#1e8449")))
        painter.setPen(QPen(QColor("#1e8449"), 0))
        painter.drawPolygon(poly)

        # Outlet pipe (lower right)
        outlet_y = cy + h // 4
        painter.setPen(QPen(QColor("#1e8449"), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(cx + w // 2, outlet_y, cx + w // 2 + 10, outlet_y)
        tip2 = _QPointF(cx + w // 2 + 10, outlet_y)
        poly2 = QPolygonF([tip2,
                           _QPointF(cx + w // 2 + 5, outlet_y - 3),
                           _QPointF(cx + w // 2 + 5, outlet_y + 3)])
        painter.setBrush(QBrush(QColor("#1e8449")))
        painter.setPen(QPen(QColor("#1e8449"), 0))
        painter.drawPolygon(poly2)

        # Agitator
        painter.setPen(QPen(QColor("#1e8449"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        shaft_top = cy - h // 2 + eh // 2
        shaft_bot = cy + h // 2 - eh // 2
        painter.drawLine(cx, shaft_top, cx, shaft_bot)
        mid = (shaft_top + shaft_bot) // 2
        blen = w // 3
        painter.drawLine(cx - blen, mid - 4, cx + blen, mid - 4)
        painter.drawLine(cx - blen, mid + 4, cx + blen, mid + 4)


class PalettePanel(QWidget):
    """Equipment palette dock contents."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(150)
        self.setMaximumWidth(180)
        self.setStyleSheet("background-color: #f4f6f7;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(8)

        # Section header
        header = QLabel("EQUIPMENT")
        header.setStyleSheet(
            "color: #7f8c8d; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(sep)

        cat = QLabel("Reactors")
        cat.setStyleSheet("color: #1a5276; font-size: 11px; font-weight: bold;")
        layout.addWidget(cat)

        tile = EquipmentTile("Batch Reactor", "batch_reactor")
        layout.addWidget(tile, alignment=Qt.AlignmentFlag.AlignHCenter)

        cstr_tile = CSTREquipmentTile("CSTR", "cstr_reactor")
        layout.addWidget(cstr_tile, alignment=Qt.AlignmentFlag.AlignHCenter)

        tip = QLabel("Drag onto the\nflowsheet to add")
        tip.setStyleSheet("color: #95a5a6; font-size: 10px;")
        tip.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(tip)

        layout.addStretch()
