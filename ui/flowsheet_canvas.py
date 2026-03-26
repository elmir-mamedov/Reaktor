from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (QGraphicsScene, QGraphicsView, QGraphicsItem,
                              QMenu)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (QPainter, QPen, QBrush, QColor, QFont,
                          QTransform, QAction)

from models.reaction import ElementaryReaction, ReactionType

# ── Vessel geometry constants ─────────────────────────────────────────────────
_W = 64       # vessel body width
_H = 90       # vessel body height
_EH = 20      # ellipse height at top and bottom


class BatchReactorItem(QGraphicsItem):
    """PFD symbol for a batch reactor, rendered with a custom painter."""

    MIME_KEY = "batch_reactor"

    def __init__(self, name: str = "R-100", scene: FlowsheetScene = None):
        super().__init__()
        self.name = name
        self.reaction = ElementaryReaction()
        self._scene_ref = scene  # kept to call scene methods (no QObject signal)
        self._hovered = False

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    # ── bounding rect / shape ─────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        # extra room for nozzle above and label below
        return QRectF(-_W / 2 - 8, -_H / 2 - 26, _W + 16, _H + 52)

    # ── events ────────────────────────────────────────────────────────────

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if self._scene_ref is not None:
                if value:
                    self._scene_ref._notify_selected(self)
                else:
                    # Only deselect if nothing else is selected
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

        # Vessel body rectangle
        painter.drawRect(QRectF(-w / 2, -h / 2 + eh / 2, w, h - eh))
        # Top ellipse
        painter.drawEllipse(QRectF(-w / 2, -h / 2, w, eh))
        # Bottom ellipse
        painter.drawEllipse(QRectF(-w / 2, h / 2 - eh, w, eh))

        # Nozzle on top
        painter.drawRect(QRectF(-5, -h / 2 - 18, 10, 18))

        # Agitator shaft
        agit_pen = QPen(border, 1.2)
        painter.setPen(agit_pen)
        shaft_top = -h / 2 + eh / 2
        shaft_bot = h / 2 - eh / 2
        painter.drawLine(QPointF(0, shaft_top), QPointF(0, shaft_bot))

        # Agitator blades (two sets)
        blen = w * 0.36
        for blade_y in (-h * 0.18, h * 0.18):
            painter.drawLine(QPointF(-blen, blade_y), QPointF(blen, blade_y))

        # Selection highlight (dashed border)
        if selected:
            sel_pen = QPen(QColor("#3498db"), 1.2, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect().adjusted(3, 3, -3, -3))

        # Reactor name label (below vessel)
        painter.setPen(QPen(QColor("#1a3a5c")))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(
            QRectF(-w / 2, h / 2 + 6, w, 18),
            Qt.AlignmentFlag.AlignCenter, self.name)

        # Reaction type hint (inside vessel body)
        _rtype_short = {
            "FIRST_ORDER_A_TO_B": "A→B",
            "SECOND_ORDER_A_B_TO_C": "A+B→C",
            "SECOND_ORDER_2A_TO_B": "2A→B",
        }
        painter.setFont(QFont("Segoe UI", 7))
        painter.setPen(QPen(QColor("#5d6d7e")))
        rstr = _rtype_short.get(self.reaction.reaction_type.name, "")
        painter.drawText(
            QRectF(-w / 2, -h / 2 + eh + 3, w, 14),
            Qt.AlignmentFlag.AlignCenter, rstr)


# ── Scene ─────────────────────────────────────────────────────────────────────

class FlowsheetScene(QGraphicsScene):
    reactor_selected = pyqtSignal(object)   # BatchReactorItem
    reactor_deselected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-2000, -2000, 4000, 4000)
        self._counter = 0

    # ── public API ────────────────────────────────────────────────────────

    def add_reactor(self, pos: QPointF) -> BatchReactorItem:
        self._counter += 1
        name = f"R-{100 + self._counter - 1}"
        item = BatchReactorItem(name, scene=self)
        item.setPos(pos)
        self.addItem(item)
        return item

    # ── called by BatchReactorItem.itemChange ─────────────────────────────

    def _notify_selected(self, item: BatchReactorItem):
        self.reactor_selected.emit(item)

    def _notify_deselected(self):
        self.reactor_deselected.emit()

    # ── context menu (right-click on background) ──────────────────────────

    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos(), QTransform())
        menu = QMenu()

        if item is None:
            add_act = QAction("Add Batch Reactor Here")
            menu.addAction(add_act)
            chosen = menu.exec(event.screenPos())
            if chosen == add_act:
                reactor = self.add_reactor(event.scenePos())
                self.clearSelection()
                reactor.setSelected(True)
        elif isinstance(item, BatchReactorItem):
            del_act = QAction(f"Delete  {item.name}")
            menu.addAction(del_act)
            chosen = menu.exec(event.screenPos())
            if chosen == del_act:
                self.removeItem(item)
                self.reactor_deselected.emit()


# ── View ──────────────────────────────────────────────────────────────────────

class FlowsheetView(QGraphicsView):
    """Zoomable, pannable flowsheet canvas with drop support."""

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

    # ── middle-mouse pan ──────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._mid_panning = True
            self._pan_origin = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mid_panning:
            delta = event.position() - self._pan_origin
            self._pan_origin = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y()))
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._mid_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)

    # ── keyboard ──────────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            sc = self.scene()
            for item in list(sc.selectedItems()):
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
        if (event.mimeData().hasText()
                and event.mimeData().text() == BatchReactorItem.MIME_KEY):
            sc = self.scene()
            if isinstance(sc, FlowsheetScene):
                pos = self.mapToScene(event.position().toPoint())
                reactor = sc.add_reactor(pos)
                sc.clearSelection()
                reactor.setSelected(True)
            event.acceptProposedAction()
