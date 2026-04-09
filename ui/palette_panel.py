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
        self._dark_mode = False
        self._drag_start: QPoint | None = None
        self.setFixedSize(130, 100)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setMouseTracking(True)

    def set_dark_mode(self, dark: bool):
        self._dark_mode = dark
        self.update()

    # ── painting ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._dark_mode:
            bg = QColor("#1e2e3e") if self._hovered else QColor("#1a1a1a")
            border = QColor("#2980b9") if self._hovered else QColor("#2a2a2a")
            label_color = QColor("#a0c8e8")
        else:
            bg = QColor("#ebf5fb") if self._hovered else QColor("#fdfefe")
            border = QColor("#2980b9") if self._hovered else QColor("#aab7b8")
            label_color = QColor("#1a3a5c")

        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 5, 5)

        self._draw_reactor_icon(painter, self.width() // 2, 40, 28, 40)

        painter.setPen(QPen(label_color))
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


class HeaterCoolerTile(EquipmentTile):
    """Palette tile for dragging a Heater/Cooler onto the flowsheet."""

    def _draw_reactor_icon(self, painter: QPainter, cx: int, cy: int, w: int, h: int):
        # Body rectangle (flatter than reactor)
        bh = h // 2
        painter.setPen(QPen(QColor("#d35400"), 1.5))
        painter.setBrush(QBrush(QColor("#fad7a0")))
        painter.drawRect(cx - w // 2, cy - bh // 2, w, bh)

        # Inlet pipe (left)
        painter.setPen(QPen(QColor("#d35400"), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(cx - w // 2 - 10, cy, cx - w // 2, cy)
        from PyQt6.QtGui import QPolygonF
        from PyQt6.QtCore import QPointF as _QPointF
        tip_in = _QPointF(cx - w // 2 + 1, cy)
        poly_in = QPolygonF([tip_in,
                             _QPointF(cx - w // 2 - 5, cy - 3),
                             _QPointF(cx - w // 2 - 5, cy + 3)])
        painter.setBrush(QBrush(QColor("#d35400")))
        painter.setPen(QPen(QColor("#d35400"), 0))
        painter.drawPolygon(poly_in)

        # Outlet pipe (right)
        painter.setPen(QPen(QColor("#d35400"), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(cx + w // 2, cy, cx + w // 2 + 10, cy)
        tip_out = _QPointF(cx + w // 2 + 10, cy)
        poly_out = QPolygonF([tip_out,
                              _QPointF(cx + w // 2 + 5, cy - 3),
                              _QPointF(cx + w // 2 + 5, cy + 3)])
        painter.setBrush(QBrush(QColor("#d35400")))
        painter.setPen(QPen(QColor("#d35400"), 0))
        painter.drawPolygon(poly_out)

        # Wavy lines inside
        painter.setPen(QPen(QColor("#d35400"), 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        inner_w = w - 8
        x0 = cx - inner_w // 2
        amp = bh // 6
        seg = inner_w / 6
        for wy in (cy - bh // 6, cy + bh // 6):
            from PyQt6.QtGui import QPainterPath
            from PyQt6.QtCore import QPointF as _P
            path = QPainterPath()
            path.moveTo(x0, wy)
            for i in range(6):
                sign = 1 if i % 2 == 0 else -1
                path.cubicTo(
                    x0 + i * seg + seg * 0.4, wy + sign * amp,
                    x0 + i * seg + seg * 0.6, wy + sign * amp,
                    x0 + (i + 1) * seg,       wy,
                )
            painter.drawPath(path)


class FlashSeparatorTile(EquipmentTile):
    """Palette tile for dragging a Flash Separator onto the flowsheet."""

    def _draw_reactor_icon(self, painter: QPainter, cx: int, cy: int, w: int, h: int):
        from PyQt6.QtGui import QPolygonF
        from PyQt6.QtCore import QPointF as _QPointF

        bh = h * 2 // 3
        # Trapezoid body
        trap = QPolygonF([
            _QPointF(cx - w // 2,      cy - bh // 2),
            _QPointF(cx + w // 2,      cy - bh // 2),
            _QPointF(cx + w // 2 - 6,  cy + bh // 2),
            _QPointF(cx - w // 2 + 6,  cy + bh // 2),
        ])
        painter.setPen(QPen(QColor("#2980b9"), 1.5))
        painter.setBrush(QBrush(QColor("#aed6f1")))
        painter.drawPolygon(trap)

        # Dividing line
        painter.setPen(QPen(QColor("#2980b9"), 1.0, Qt.PenStyle.DashLine))
        painter.drawLine(cx - w // 2 + 2, cy, cx + w // 2 - 2, cy)

        # Phase labels
        painter.setPen(QPen(QColor("#1a5276")))
        painter.setFont(QFont("", 7, QFont.Weight.Bold))
        painter.drawText(cx - 4, cy - 4, "V")
        painter.drawText(cx - 4, cy + 12, "L")

        # Inlet pipe (left)
        painter.setPen(QPen(QColor("#2980b9"), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(cx - w // 2 - 8, cy, cx - w // 2, cy)
        tip_in = _QPointF(cx - w // 2 + 1, cy)
        from PyQt6.QtGui import QPolygonF as _PF
        poly = _PF([tip_in,
                    _QPointF(cx - w // 2 - 4, cy - 3),
                    _QPointF(cx - w // 2 - 4, cy + 3)])
        painter.setBrush(QBrush(QColor("#2980b9")))
        painter.setPen(QPen(QColor("#2980b9"), 0))
        painter.drawPolygon(poly)


class AbsorptionColumnTile(EquipmentTile):
    """Palette tile for dragging an Absorption Column onto the flowsheet."""

    def _draw_reactor_icon(self, painter: QPainter, cx: int, cy: int, w: int, h: int):
        from PyQt6.QtCore import QPointF as _QPointF, QRectF as _QRectF

        bh = h * 4 // 5
        # Column body
        painter.setPen(QPen(QColor("#1abc9c"), 1.5))
        painter.setBrush(QBrush(QColor("#d1f2eb")))
        painter.drawRect(cx - w // 2, cy - bh // 2, w, bh)

        # Cross-hatch fill (packed-bed symbol)
        painter.setClipRect(_QRectF(cx - w // 2, cy - bh // 2, w, bh))
        hatch_pen = QPen(QColor("#1abc9c"), 0.6)
        painter.setPen(hatch_pen)
        step = 6
        for i in range(-bh, bh + w, step):
            painter.drawLine(
                cx - w // 2, cy - bh // 2 + i,
                cx - w // 2 + w + bh, cy - bh // 2 + i - w - bh,
            )
        painter.setClipping(False)

        # Liquid inlet stub (top left)
        painter.setPen(QPen(QColor("#1abc9c"), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(cx - w // 2 - 8, cy - bh // 4, cx - w // 2, cy - bh // 4)

        # Gas outlet stub (top right)
        painter.drawLine(cx + w // 2, cy - bh // 4, cx + w // 2 + 8, cy - bh // 4)


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
        self._header = QLabel("EQUIPMENT")
        self._header.setStyleSheet(
            "color: #7f8c8d; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(self._header)

        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.HLine)
        self._sep.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(self._sep)

        self._cat = QLabel("Reactors")
        self._cat.setStyleSheet("color: #1a5276; font-size: 11px; font-weight: bold;")
        layout.addWidget(self._cat)

        self._tile = EquipmentTile("Batch Reactor", "batch_reactor")
        layout.addWidget(self._tile, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._cstr_tile = CSTREquipmentTile("CSTR", "cstr_reactor")
        layout.addWidget(self._cstr_tile, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._sep2 = QFrame()
        self._sep2.setFrameShape(QFrame.Shape.HLine)
        self._sep2.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(self._sep2)

        self._cat2 = QLabel("Heat Transfer")
        self._cat2.setStyleSheet("color: #784212; font-size: 11px; font-weight: bold;")
        layout.addWidget(self._cat2)

        self._heater_tile = HeaterCoolerTile("Heater/Cooler", "heater_cooler")
        layout.addWidget(self._heater_tile, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._sep3 = QFrame()
        self._sep3.setFrameShape(QFrame.Shape.HLine)
        self._sep3.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(self._sep3)

        self._cat3 = QLabel("Separation")
        self._cat3.setStyleSheet("color: #1a5276; font-size: 11px; font-weight: bold;")
        layout.addWidget(self._cat3)

        self._flash_tile = FlashSeparatorTile("Flash Sep.", "flash_separator")
        layout.addWidget(self._flash_tile, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._sep4 = QFrame()
        self._sep4.setFrameShape(QFrame.Shape.HLine)
        self._sep4.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(self._sep4)

        self._cat4 = QLabel("Gas-Liquid")
        self._cat4.setStyleSheet("color: #0e6655; font-size: 11px; font-weight: bold;")
        layout.addWidget(self._cat4)

        self._abs_tile = AbsorptionColumnTile("Absorption Col.", "absorption_column")
        layout.addWidget(self._abs_tile, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._tip = QLabel("Drag onto the\nflowsheet to add")
        self._tip.setStyleSheet("color: #95a5a6; font-size: 10px;")
        self._tip.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._tip)

        layout.addStretch()

    def set_dark_mode(self, dark: bool):
        if dark:
            self.setStyleSheet("background-color: #111111;")
            self._header.setStyleSheet(
                "color: #555555; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
            self._cat.setStyleSheet("color: #a0c8e8; font-size: 11px; font-weight: bold;")
            self._cat2.setStyleSheet("color: #e0a060; font-size: 11px; font-weight: bold;")
            self._cat3.setStyleSheet("color: #a0c8e8; font-size: 11px; font-weight: bold;")
            self._cat4.setStyleSheet("color: #5dbea8; font-size: 11px; font-weight: bold;")
            sep_style = "color: #2a2a2a;"
            self._tip.setStyleSheet("color: #444444; font-size: 10px;")
        else:
            self.setStyleSheet("background-color: #f4f6f7;")
            self._header.setStyleSheet(
                "color: #7f8c8d; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
            self._cat.setStyleSheet("color: #1a5276; font-size: 11px; font-weight: bold;")
            self._cat2.setStyleSheet("color: #784212; font-size: 11px; font-weight: bold;")
            self._cat3.setStyleSheet("color: #1a5276; font-size: 11px; font-weight: bold;")
            self._cat4.setStyleSheet("color: #0e6655; font-size: 11px; font-weight: bold;")
            sep_style = "color: #bdc3c7;"
            self._tip.setStyleSheet("color: #95a5a6; font-size: 10px;")

        for sep in (self._sep, self._sep2, self._sep3, self._sep4):
            sep.setStyleSheet(sep_style)

        for tile in (self._tile, self._cstr_tile, self._heater_tile,
                     self._flash_tile, self._abs_tile):
            tile.set_dark_mode(dark)
