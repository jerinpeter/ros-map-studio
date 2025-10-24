from PyQt5 import QtCore, QtGui, QtWidgets, uic

from ui_map_editor import Ui_MapEditor

from PyQt5.QtGui import QPainter, QBrush, QPen, QTextCursor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QUndoStack, QUndoCommand

import math
import yaml
from PIL import Image
import sys
import os


# --- Undo/Redo command for snapshot-based state ---
class SnapshotCommand(QUndoCommand):
    def __init__(self, editor, before_state, after_state, label="Edit"):
        super(SnapshotCommand, self).__init__(label)
        self.editor = editor
        self.before = before_state
        self.after = after_state

    def undo(self):
        try:
            self.editor._restoreState(self.before)
        except Exception:
            pass

    def redo(self):
        try:
            self.editor._restoreState(self.after)
        except Exception:
            pass

# --- Helper classes for text annotations with resize handles ---
class TextAnnotationItem(QtWidgets.QGraphicsTextItem):
    """QGraphicsTextItem subclass that notifies a callback on position/selection changes."""
    def __init__(self, *args, **kwargs):
        super(TextAnnotationItem, self).__init__(*args, **kwargs)
        self._change_callback = None
        self._editing = False
        self._pressPos = None
        self._editor_ref = None  # set by editor when creating item

    def setChangeCallback(self, cb):
        self._change_callback = cb

    def itemChange(self, change, value):
        res = super(TextAnnotationItem, self).itemChange(change, value)
        try:
            if self._change_callback is not None:
                # Notify callback for position or selection changes so overlay can update
                if change in (QtWidgets.QGraphicsItem.ItemPositionChange,
                              QtWidgets.QGraphicsItem.ItemPositionHasChanged,
                              QtWidgets.QGraphicsItem.ItemSelectedChange,
                              QtWidgets.QGraphicsItem.ItemSelectedHasChanged):
                    try:
                        self._change_callback(self, change, value)
                    except Exception:
                        pass
        except Exception:
            pass
        return res

    def beginEdit(self):
        try:
            self._editing = True
            self.setTextInteractionFlags(Qt.TextEditorInteraction)
            self.setFocus(Qt.OtherFocusReason)
            try:
                cursor = self.textCursor()
                cursor.select(QTextCursor.Document)
                self.setTextCursor(cursor)
            except Exception:
                pass
        except Exception:
            pass

    def endEdit(self):
        try:
            self.setTextInteractionFlags(Qt.NoTextInteraction)
            self.clearFocus()
            self._editing = False
        except Exception:
            pass

    def focusOutEvent(self, event):
        try:
            if self._editing:
                self.endEdit()
        except Exception:
            pass
        try:
            super(TextAnnotationItem, self).focusOutEvent(event)
        except Exception:
            pass

    def keyPressEvent(self, event):
        try:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
                # Finish editing on Enter
                self.endEdit()
                event.accept()
                return
            if event.key() == Qt.Key_Escape:
                # Cancel edit; if empty, remove item
                if not self.toPlainText().strip():
                    try:
                        sc = self.scene()
                        if sc is not None:
                            sc.removeItem(self)
                    except Exception:
                        pass
                else:
                    self.endEdit()
                event.accept()
                return
        except Exception:
            pass
        try:
            super(TextAnnotationItem, self).keyPressEvent(event)
        except Exception:
            pass

    def mouseDoubleClickEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                self.beginEdit()
                event.accept()
                return
        except Exception:
            pass
        try:
            super(TextAnnotationItem, self).mouseDoubleClickEvent(event)
        except Exception:
            pass

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                self._pressPos = QtCore.QPointF(self.pos())
                ed = getattr(self, '_editor_ref', None)
                if ed is not None:
                    try:
                        ed._beginSnapshot("Move Text")
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            super(TextAnnotationItem, self).mousePressEvent(event)
        except Exception:
            pass

    def mouseReleaseEvent(self, event):
        try:
            super(TextAnnotationItem, self).mouseReleaseEvent(event)
        except Exception:
            pass
        try:
            ed = getattr(self, '_editor_ref', None)
            if ed is not None:
                ed._endSnapshot("Move Text")
        finally:
            self._pressPos = None


class ResizeHandle(QtWidgets.QGraphicsRectItem):
    """Small draggable handle used to resize a TextSelectionOverlay."""
    def __init__(self, parent_overlay, corner_index, size=8):
        super(ResizeHandle, self).__init__(-size/2, -size/2, size, size)
        self.parent_overlay = parent_overlay
        self.corner_index = corner_index  # 0:tl,1:tr,2:br,3:bl
        self.setBrush(QtGui.QBrush(QtGui.QColor(255,255,255)))
        self.setPen(QtGui.QPen(Qt.black))
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations, True)
        self.setZValue(1002)

    def mousePressEvent(self, event):
        try:
            event.accept()
        except Exception:
            pass
        try:
            ed = getattr(self.parent_overlay, 'editor', None)
            if ed is not None:
                ed._beginSnapshot("Resize Text")
        except Exception:
            pass

    def mouseMoveEvent(self, event):
        # map to scene position
        scene_pos = self.mapToScene(event.pos())
        try:
            self.parent_overlay.handleDrag(self, scene_pos)
        except Exception:
            pass
        try:
            event.accept()
        except Exception:
            pass

    def mouseReleaseEvent(self, event):
        try:
            self.parent_overlay.update()
        except Exception:
            pass
        try:
            ed = getattr(self.parent_overlay, 'editor', None)
            if ed is not None:
                ed._endSnapshot("Resize Text")
        except Exception:
            pass
        try:
            event.accept()
        except Exception:
            pass


class TextSelectionOverlay(object):
    """Manages a selection rectangle and four resize handles for a TextAnnotationItem."""
    CURSOR_SHAPES = [
        Qt.SizeFDiagCursor,
        Qt.SizeBDiagCursor,
        Qt.SizeFDiagCursor,
        Qt.SizeBDiagCursor,
    ]

    def __init__(self, scene, text_item, editor=None):
        self.scene = scene
        self.text_item = text_item
        self.rect_item = None
        self.handles = []
        self.editor = editor
        self.create()

    def create(self):
        # create rect and handles
        try:
            br = self.text_item.mapToScene(self.text_item.boundingRect()).boundingRect()
            pen = QtGui.QPen(QtGui.QColor(0,120,215))
            pen.setStyle(Qt.DashLine)
            pen.setWidth(1)
            self.rect_item = QtWidgets.QGraphicsRectItem(br)
            self.rect_item.setPen(pen)
            self.rect_item.setZValue(1000)
            self.rect_item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
            self.rect_item.setAcceptedMouseButtons(Qt.NoButton)
            self.scene.addItem(self.rect_item)

            for i in range(4):
                h = ResizeHandle(self, i, size=8)
                try:
                    h.setCursor(self.CURSOR_SHAPES[i])
                except Exception:
                    pass
                self.handles.append(h)
                self.scene.addItem(h)

            self.update()
        except Exception as e:
            print('Error creating selection overlay:', e)

    def update(self):
        try:
            br = self.text_item.mapToScene(self.text_item.boundingRect()).boundingRect()
            if self.rect_item:
                self.rect_item.setRect(br)
            # corners: tl,tr,br,bl
            corners = [br.topLeft(), br.topRight(), br.bottomRight(), br.bottomLeft()]
            for i, h in enumerate(self.handles):
                h.setPos(corners[i])
        except Exception as e:
            # ignore if underlying C++ objects are gone
            pass

    def handleDrag(self, handle, scene_pos):
        # compute scale based on movement of handle relative to opposite corner
        try:
            br = self.text_item.mapToScene(self.text_item.boundingRect()).boundingRect()
            idx = handle.corner_index
            opp = (idx + 2) % 4
            corners = [br.topLeft(), br.topRight(), br.bottomRight(), br.bottomLeft()]
            opp_pt = corners[opp]
            # compute new diagonal ratio for smoother scaling regardless of drag direction
            old_diag = math.hypot(br.width(), br.height())
            if old_diag <= 0:
                return
            delta_x = scene_pos.x() - opp_pt.x()
            delta_y = scene_pos.y() - opp_pt.y()
            new_diag = math.hypot(delta_x, delta_y)
            if new_diag <= 0:
                return
            scale = new_diag / old_diag
            # adjust font size
            font = self.text_item.font()
            old_size = font.pointSizeF()
            if old_size <= 0:
                fallback = font.pointSize()
                old_size = fallback if fallback > 0 else 12
            new_size = max(6.0, min(400.0, float(old_size * scale)))
            font.setPointSizeF(new_size)
            self.text_item.setFont(font)
            # update overlay
            self.update()
            if self.editor is not None:
                try:
                    self.editor._syncTextControls(self.text_item)
                except Exception:
                    pass
        except Exception:
            pass

    def destroy(self):
        try:
            if self.rect_item:
                self.scene.removeItem(self.rect_item)
                self.rect_item = None
            for h in self.handles:
                try:
                    self.scene.removeItem(h)
                except Exception:
                    pass
            self.handles = []
        except Exception:
            pass


class MapEditor(QtWidgets.QMainWindow):
    def __init__(self, fn):
        super(MapEditor, self).__init__()

        # two approaches to integrating tool generated ui file shown below
        
        # setup user interface directly from ui file
        #uic.loadUi('UI_MapEditor.ui', self)

        # setup user interface from py module converted from ui file
        self.ui = Ui_MapEditor()
        self.ui.setupUi(self)

        # Undo stack
        self.undo_stack = QUndoStack(self)

        self.setMinimumSize(600, 600)
        
        # Initialize cursor indicator early
        self.cursor_indicator = None

        # Progressive zoom via slider (percent 50..400)
        try:
            self.ui.zoomSlider.valueChanged.connect(self.handleZoomSlider)
        except Exception:
            pass
        # Use only progressive zoom; disable discrete presets box to avoid confusion
        try:
            self.ui.zoomBox.setEnabled(False)
        except Exception:
            pass

        self.ui.colorBox.addItem('🔄 Alternate', 0)
        self.ui.colorBox.addItem('⚫ Occupied', 1)
        self.ui.colorBox.addItem('⚪ Unoccupied', 2)
        self.ui.colorBox.addItem('🔘 Uncertain', 3)
        self.ui.colorBox.currentIndexChanged.connect(self.handleColor)
        self.color = 'alternate'
        
        # Initialize tool mode
        self.tool_mode = 'paint'
        self.ui.toolModeBox.currentIndexChanged.connect(self.handleToolMode)
        
        # Initialize measurement tool state
        self.measuring = False
        self.measure_start_point = None
        self.temp_measure_line = None
        self.temp_measure_text = None
        self.dimensions = []  # Store all dimension annotations
        self.selected_dimension = None  # Track selected dimension for deletion
        
        # Initialize line-draw tool state
        self.drawing_line = False
        self.line_start_point = None
        self.temp_line = None
        self.lines = []  # Store drawn line items (for persistence/undo)
        
        # Initialize cursor size
        self.cursor_size = 1
        self.ui.cursorSizeSlider.valueChanged.connect(self.handleCursorSize)
        self.ui.cursorSizeSpinBox.valueChanged.connect(self.handleCursorSize)
        
        # Initialize rotation
        self.rotation_angle = 0
        self.ui.rotationSlider.valueChanged.connect(self.handleRotation)
        self.ui.rotationSpinBox.valueChanged.connect(self.handleRotation)
        self.ui.resetRotationBtn.clicked.connect(self.resetRotation)

        self.read(fn)

        # Text annotations storage
        self.text_items = []

        # Connect text property controls if present
        try:
            self.ui.textSizeSpinBox.valueChanged.connect(self.handleTextSize)
            # Keep rotation slider and spinbox in sync and call handler
            self.ui.textRotationSlider.valueChanged.connect(self.ui.textRotationSpinBox.setValue)
            self.ui.textRotationSpinBox.valueChanged.connect(self.ui.textRotationSlider.setValue)
            self.ui.textRotationSlider.valueChanged.connect(self.handleTextRotation)
        except Exception:
            # UI may not have text controls in older layouts
            pass

        view_width = self.frameGeometry().width()

        self.min_multiplier = math.ceil(view_width / self.map_width_cells)
        # Start zoom at 50%
        self.zoom = 0.5
        self.pixels_per_cell = self.min_multiplier * self.zoom 

        self.draw_map()
        
        self.ui.closeButton.clicked.connect(self.closeEvent)
        self.ui.saveButton.clicked.connect(self.saveEvent)
        # Make Clear Dimensions undoable
        try:
            self.ui.clearDimensionsBtn.clicked.disconnect()
        except Exception:
            pass
        self.ui.clearDimensionsBtn.clicked.connect(lambda: self._pushSnapshotAction("Clear Dimensions", self.clearDimensions))
        try:
            self.ui.undoButton.clicked.connect(self.undo_stack.undo)
            self.ui.redoButton.clicked.connect(self.undo_stack.redo)
        except Exception:
            pass

        self.ui.graphicsView.horizontalScrollBar().valueChanged.connect(self.scrollChanged)
        self.ui.graphicsView.verticalScrollBar().valueChanged.connect(self.scrollChanged)

        # Ensure mouse move events are tracked on the viewport
        self.ui.graphicsView.setMouseTracking(True)

        # Install event filter on both the graphics view and its viewport so
        # we reliably receive keyboard and mouse events regardless of which
        # sub-widget currently has focus.
        self.ui.graphicsView.viewport().installEventFilter(self)
        self.ui.graphicsView.installEventFilter(self)

        # Enable keyboard focus on both the view and the viewport and set focus
        # to the view so that key presses (Esc, Delete, Backspace, etc.) are
        # delivered to the event filter.
        self.ui.graphicsView.setFocusPolicy(Qt.StrongFocus)
        self.ui.graphicsView.viewport().setFocusPolicy(Qt.StrongFocus)
        self.ui.graphicsView.setFocus()

        # Default to Select tool on startup to prevent accidental text adds
        try:
            self._setToolMode('select')
        except Exception:
            pass

        # Keyboard shortcuts for undo/redo
        try:
            undo_sc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self)
            undo_sc.activated.connect(self.undo_stack.undo)
            redo_sc = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+Z"), self)
            redo_sc.activated.connect(self.undo_stack.redo)
        except Exception:
            pass


    def eventFilter(self, source, event):
        # Handle ESC key to cancel actions
        if event.type() == QtCore.QEvent.KeyPress:
            # If a text item is currently being edited, don't hijack key presses
            try:
                if self._isEditingText():
                    return False
            except Exception:
                pass
            if event.key() == Qt.Key_Escape:
                if self.tool_mode == 'measure' and self.measuring:
                    self.cancelMeasurement()
                    self.ui.statusInfo.setText("📏 Measurement cancelled - Click to start")
                    print("Measurement cancelled with ESC")
                elif self.tool_mode == 'line' and self.drawing_line:
                    self.cancelLineDrawing()
                    self.ui.statusInfo.setText("➖ Line drawing cancelled - Click to start")
                elif self.selected_dimension:
                    self.deselectDimension()
                else:
                    # ESC switches to Select mode for convenience
                    try:
                        self._setToolMode('select')
                    except Exception:
                        pass
                return True
            elif event.key() == Qt.Key_V:
                try:
                    self._setToolMode('select')
                except Exception:
                    pass
                return True
            elif event.key() == Qt.Key_T:
                try:
                    self._setToolMode('text')
                except Exception:
                    pass
                return True
            elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
                # Prefer deleting selected dimension if any
                if self.selected_dimension:
                    def do_del_dim():
                        self.deleteSelectedDimension()
                    self._pushSnapshotAction("Delete Dimension", do_del_dim)
                    return True
                # Otherwise delete any selected QGraphicsItems (text or other items)
                try:
                    selected = []
                    if hasattr(self, 'scene') and self.scene is not None:
                        selected = self.scene.selectedItems()
                    if selected:
                        def do_del_items():
                            for item in list(selected):
                                # remove from text_items if present
                                try:
                                    if item in self.text_items:
                                        self.text_items.remove(item)
                                except Exception:
                                    pass
                                try:
                                    self.scene.removeItem(item)
                                except Exception:
                                    pass
                        self._pushSnapshotAction("Delete Selection", do_del_items)
                        self.ui.statusInfo.setText("🗑️ Selected items deleted")
                        return True
                except Exception:
                    pass

        # Handle mouse move for painting
        if (event.type() == QtCore.QEvent.MouseMove and 
            source is self.ui.graphicsView.viewport()):
            
                        # Update cursor indicator position
                        scene_pos = self.ui.graphicsView.mapToScene(event.pos())
                        self.updateCursorIndicator(scene_pos)

                        # Paint if in paint mode and dragging
                        if (self.tool_mode == 'paint' and 
                                self.color != 'alternate' and 
                                event.buttons() == QtCore.Qt.LeftButton):

                                pos = event.pos()
                                x = pos.x() + self.ui.graphicsView.horizontalScrollBar().value()
                                y = pos.y() + self.ui.graphicsView.verticalScrollBar().value()
                                x = math.floor(x / self.pixels_per_cell)
                                y = math.floor(y / self.pixels_per_cell)

                                # Apply brush with cursor size
                                self.paint_area(x, y, self.cursor_size)

                        # Show preview line in measure mode
                        elif (self.tool_mode == 'measure' and 
                                    self.measuring and 
                                    self.measure_start_point is not None):
                                self.updateMeasurePreview(scene_pos)

                        # Show preview line in line-draw mode
                        elif (self.tool_mode == 'line' and 
                                    self.drawing_line and 
                                    self.line_start_point is not None):
                                self.updateLinePreview(scene_pos)
        
        # Handle mouse enter/leave to show/hide cursor
        elif event.type() == QtCore.QEvent.Enter and source is self.ui.graphicsView.viewport():
            if not self.cursor_indicator:
                self.createCursorIndicator()
                
        elif event.type() == QtCore.QEvent.Leave and source is self.ui.graphicsView.viewport():
            self.hideCursorIndicator()
            
        return super(MapEditor, self).eventFilter(source, event)

    def _setToolMode(self, mode_str):
        """Helper to change tool mode by its data string via the combo box."""
        try:
            for i in range(self.ui.toolModeBox.count()):
                if self.ui.toolModeBox.itemData(i) == mode_str:
                    self.ui.toolModeBox.setCurrentIndex(i)
                    return
        except Exception:
            pass

    def _isEditingText(self):
        """Return True if a QGraphicsTextItem is currently in text edit mode."""
        try:
            if not hasattr(self, 'scene') or self.scene is None:
                return False
            fi = self.scene.focusItem()
            if isinstance(fi, QtWidgets.QGraphicsTextItem):
                flags = fi.textInteractionFlags()
                return bool(flags & Qt.TextEditorInteraction)
        except Exception:
            pass
        return False

    # --- Snapshot-based undo/redo helpers ---
    def _captureState(self):
        before_ppc = getattr(self, 'pixels_per_cell', self.min_multiplier)
        return {
            'text': self._captureTextAnnotations(before_ppc),
            'dims': self._captureDimensions(before_ppc)[0]
        }

    def _restoreState(self, state):
        if not state:
            return
        self._restoring_state = True
        try:
            # Remove current text items
            try:
                for item in list(getattr(self, 'text_items', [])):
                    try:
                        self.scene.removeItem(item)
                    except Exception:
                        pass
                self.text_items = []
            except Exception:
                pass

            # Remove current dimensions
            try:
                for dim in list(getattr(self, 'dimensions', [])):
                    try:
                        self.scene.removeItem(dim['line'])
                        self.scene.removeItem(dim['arrow1'])
                        self.scene.removeItem(dim['arrow2'])
                        self.scene.removeItem(dim['text'])
                        self.scene.removeItem(dim['background'])
                    except Exception:
                        pass
                self.dimensions = []
                self.selected_dimension = None
            except Exception:
                pass

            # Restore
            try:
                self._restoreTextAnnotations(state.get('text', []))
            except Exception:
                pass
            try:
                self._restoreDimensions(state.get('dims', []), None)
            except Exception:
                pass
            # Update overlay selection if needed
            try:
                self.onSelectionChanged()
            except Exception:
                pass
        finally:
            self._restoring_state = False

    def _pushSnapshotAction(self, label, action_fn):
        try:
            before = self._captureState()
        except Exception:
            before = None
        try:
            action_fn()
        except Exception as e:
            print(f"Action failed during '{label}':", e)
            return
        try:
            after = self._captureState()
        except Exception:
            after = None
        try:
            cmd = SnapshotCommand(self, before, after, label)
            self.undo_stack.push(cmd)
        except Exception:
            pass

    def _beginSnapshot(self, label):
        if getattr(self, '_restoring_state', False):
            return
        try:
            self._snapshot_label = label
            self._snapshot_before = self._captureState()
        except Exception:
            self._snapshot_before = None

    def _endSnapshot(self, label=None):
        if getattr(self, '_restoring_state', False):
            return
        before = getattr(self, '_snapshot_before', None)
        if before is None:
            return
        try:
            after = self._captureState()
            cmd = SnapshotCommand(self, before, after, label or getattr(self, '_snapshot_label', 'Edit'))
            self.undo_stack.push(cmd)
        except Exception:
            pass
        finally:
            self._snapshot_before = None
            self._snapshot_label = None

    def paint_area(self, center_x, center_y, brush_size):
        """Paint an area with the specified brush size"""
        if self.color == 'occupied':
            val = 0
        elif self.color == 'unoccupied':
            val = 255
        elif self.color == 'uncertain':
            val = 200
        else:
            return
            
        # Calculate brush area
        radius = brush_size // 2
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                x = center_x + dx
                y = center_y + dy
                
                # Check bounds
                if (x >= 0 and x < self.map_width_cells and 
                    y >= 0 and y < self.map_height_cells):
                    
                    # For circular brush, check distance
                    if brush_size > 1:
                        distance = math.sqrt(dx*dx + dy*dy)
                        if distance > radius:
                            continue
                    
                    # Update model
                    self.im.putpixel((x, y), val)
                    
                    # Redraw cell
                    color = self.value2color(val)
                    self.color_cell(x, y, color)


    def paintEvent(self, e):
        self.scrollChanged(0)


    def scrollChanged(self, val):
        # Guard because scene may be temporarily deleted during UI operations
        try:
            if not hasattr(self, 'scene') or self.scene is None:
                return
            sw = self.scene.width()
            sh = self.scene.height()
            if sw and sh:
                x = int(self.ui.graphicsView.horizontalScrollBar().value() / sw * self.im.size[0])
                y = int(self.ui.graphicsView.verticalScrollBar().value() / sh * self.im.size[1])
                width = int(self.ui.graphicsView.viewport().size().width() / sw * self.im.size[0])
                height = int(self.ui.graphicsView.viewport().size().height() / sh * self.im.size[1])
                self.drawBox(x, y, width, height)
        except Exception:
            # ignore transient errors (e.g., wrapped C++ object deleted)
            return


    def drawBox(self, x=5, y=5, width=50, height=50):

        im = self.im.convert("RGBA")
        data = im.tobytes("raw","RGBA")
        qim = QtGui.QImage(data, im.size[0], im.size[1], QtGui.QImage.Format_ARGB32)
        pix = QtGui.QPixmap.fromImage(qim)

        painter = QtGui.QPainter(pix)
        pen = QPen(Qt.red)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(x, y, width, height)

        painter.end()

        self.ui.label_2.setPixmap(pix)
        self.ui.label_2.show()

    def handleToolMode(self, index):
        mode_data = self.ui.toolModeBox.currentData()
        self.tool_mode = mode_data
        print(f"Tool mode changed to: {self.tool_mode}")
        
        if self.tool_mode == 'select':
            self.ui.statusInfo.setText("🖱️ Select Mode: Click to select, drag to move")
            # Disable paint controls in select mode
            self.ui.colorBox.setEnabled(False)
            self.ui.cursorSizeSlider.setEnabled(False)
            self.ui.cursorSizeSpinBox.setEnabled(False)
            # Enable text controls for convenience; they apply to selected text
            try:
                self.ui.textSizeSpinBox.setEnabled(True)
                self.ui.textRotationSlider.setEnabled(True)
                self.ui.textRotationSpinBox.setEnabled(True)
            except Exception:
                pass
        elif self.tool_mode == 'measure':
            self.ui.statusInfo.setText("📏 Measure Mode: Click two points")
            # Disable color selection in measure mode
            self.ui.colorBox.setEnabled(False)
            self.ui.cursorSizeSlider.setEnabled(False)
            self.ui.cursorSizeSpinBox.setEnabled(False)
        elif self.tool_mode == 'text':
            self.ui.statusInfo.setText("🔤 Text Mode: Click to add text annotations")
            # Disable color/brush controls in text mode
            self.ui.colorBox.setEnabled(False)
            self.ui.cursorSizeSlider.setEnabled(False)
            self.ui.cursorSizeSpinBox.setEnabled(False)
            # Enable text controls
            try:
                self.ui.textSizeSpinBox.setEnabled(True)
                self.ui.textRotationSlider.setEnabled(True)
                self.ui.textRotationSpinBox.setEnabled(True)
            except Exception:
                pass
        else:
            self.ui.statusInfo.setText("🖌️ Paint Mode")
            self.ui.colorBox.setEnabled(True)
            self.ui.cursorSizeSlider.setEnabled(True)
            self.ui.cursorSizeSpinBox.setEnabled(True)
            # Disable text controls when not in text mode
            try:
                self.ui.textSizeSpinBox.setEnabled(False)
                self.ui.textRotationSlider.setEnabled(False)
                self.ui.textRotationSpinBox.setEnabled(False)
            except Exception:
                pass
            # Cancel any ongoing measurement
            if self.measuring:
                self.cancelMeasurement()
            # Deselect any selected dimension
            if self.selected_dimension:
                self.deselectDimension()

    def handleColor(self, index):
        color_text = self.ui.colorBox.currentText()
        if 'Alternate' in color_text:
            self.color = 'alternate'
        elif 'Occupied' in color_text:
            self.color = 'occupied'
        elif 'Unoccupied' in color_text:
            self.color = 'unoccupied'
        elif 'Uncertain' in color_text:
            self.color = 'uncertain'
        print(f"Color changed to: {self.color}")
        self.ui.statusInfo.setText(f"Color mode: {self.color.title()}")

    def handleCursorSize(self, value):
        self.cursor_size = value
        print(f"Cursor size changed to: {self.cursor_size}")
        self.ui.statusInfo.setText(f"Brush size: {self.cursor_size}px")
        # Update cursor indicator size
        self.updateCursorIndicatorSize()

    def handleTextSize(self, value):
        """Apply font size to selected text items."""
        try:
            if not hasattr(self, 'scene') or self.scene is None:
                return
            def do_change():
                updated_any = False
                for item in self.scene.selectedItems():
                    if isinstance(item, QtWidgets.QGraphicsTextItem):
                        font = item.font()
                        font.setPointSize(int(value))
                        item.setFont(font)
                        updated_any = True
                if updated_any and hasattr(self, 'current_text_overlay') and self.current_text_overlay:
                    try:
                        self.current_text_overlay.update()
                    except Exception:
                        pass
            self._pushSnapshotAction("Change Text Size", do_change)
        except Exception as e:
            print('Error applying text size:', e)

    def handleTextRotation(self, angle):
        """Apply rotation (degrees) to selected text items."""
        try:
            if not hasattr(self, 'scene') or self.scene is None:
                return
            a = float(angle)
            def do_change():
                updated_any = False
                for item in self.scene.selectedItems():
                    if isinstance(item, QtWidgets.QGraphicsTextItem):
                        item.setRotation(a)
                        updated_any = True
                if updated_any and hasattr(self, 'current_text_overlay') and self.current_text_overlay:
                    try:
                        self.current_text_overlay.update()
                    except Exception:
                        pass
            self._pushSnapshotAction("Rotate Text", do_change)
        except Exception as e:
            print('Error applying text rotation:', e)

    def _syncTextControls(self, text_item):
        """Update text property widgets to reflect the provided text item."""
        if text_item is None:
            return
        try:
            font = text_item.font()
            size_f = font.pointSizeF()
            if size_f <= 0:
                size_f = font.pointSize()
            if size_f > 0 and hasattr(self.ui, 'textSizeSpinBox'):
                try:
                    self.ui.textSizeSpinBox.blockSignals(True)
                    self.ui.textSizeSpinBox.setValue(int(round(size_f)))
                finally:
                    self.ui.textSizeSpinBox.blockSignals(False)
        except Exception:
            pass

        rotation_val = None
        try:
            rotation_val = int(round(text_item.rotation()))
        except Exception:
            pass

        if rotation_val is not None:
            try:
                if hasattr(self.ui, 'textRotationSpinBox'):
                    self.ui.textRotationSpinBox.blockSignals(True)
                    self.ui.textRotationSpinBox.setValue(rotation_val)
            finally:
                if hasattr(self.ui, 'textRotationSpinBox'):
                    self.ui.textRotationSpinBox.blockSignals(False)
            try:
                if hasattr(self.ui, 'textRotationSlider'):
                    self.ui.textRotationSlider.blockSignals(True)
                    self.ui.textRotationSlider.setValue(rotation_val)
            finally:
                if hasattr(self.ui, 'textRotationSlider'):
                    self.ui.textRotationSlider.blockSignals(False)

    def onSelectionChanged(self):
        """Called when scene selection changes — update text controls to match first selected text item."""
        try:
            if not hasattr(self, 'scene') or self.scene is None:
                return
            selected = self.scene.selectedItems()
            first_text = None
            for item in selected:
                if isinstance(item, QtWidgets.QGraphicsTextItem):
                    first_text = item
                    break

            if first_text is not None:
                # Update UI controls to reflect the selected text item
                self._syncTextControls(first_text)
                # create/update selection overlay for this text item
                try:
                    if not hasattr(self, 'current_text_overlay') or self.current_text_overlay is None:
                        self.current_text_overlay = TextSelectionOverlay(self.scene, first_text, editor=self)
                    else:
                        # if overlay exists for different item, recreate
                        if self.current_text_overlay.text_item is not first_text:
                            try:
                                self.current_text_overlay.destroy()
                            except Exception:
                                pass
                            self.current_text_overlay = TextSelectionOverlay(self.scene, first_text, editor=self)
                        else:
                            self.current_text_overlay.update()
                except Exception as e:
                    print('Error creating/updating selection overlay:', e)
            else:
                # No text selected; nothing to sync
                # remove any existing overlay
                try:
                    if hasattr(self, 'current_text_overlay') and self.current_text_overlay:
                        self.current_text_overlay.destroy()
                        self.current_text_overlay = None
                except Exception:
                    pass
        except Exception as e:
            print('Error in onSelectionChanged:', e)

    def _onTextItemChanged(self, item, change, value):
        # called when a text item's position or selection changes
        try:
            if hasattr(self, 'current_text_overlay') and self.current_text_overlay:
                if self.current_text_overlay.text_item is item:
                    self.current_text_overlay.update()
                    try:
                        self._syncTextControls(item)
                    except Exception:
                        pass
        except Exception:
            pass

    def handleRotation(self, angle):
        self.rotation_angle = angle
        print(f"Rotation changed to: {self.rotation_angle}°")
        self.ui.statusInfo.setText(f"Rotation: {self.rotation_angle}°")
        self.apply_rotation()

    def resetRotation(self):
        self.ui.rotationSlider.setValue(0)
        self.ui.rotationSpinBox.setValue(0)
        self.rotation_angle = 0
        self.apply_rotation()

    def apply_rotation(self):
        if hasattr(self, 'scene'):
            # Apply rotation to the graphics view
            transform = QtGui.QTransform()
            transform.rotate(self.rotation_angle)
            self.ui.graphicsView.setTransform(transform)

    def updateMeasurePreview(self, end_pos):
        """Update the temporary measurement line as mouse moves"""
        if self.temp_measure_line:
            self.scene.removeItem(self.temp_measure_line)
        if self.temp_measure_text:
            self.scene.removeItem(self.temp_measure_text)
        
        # Draw temporary line
        pen = QPen(Qt.cyan)
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        self.temp_measure_line = self.scene.addLine(
            self.measure_start_point.x(), 
            self.measure_start_point.y(),
            end_pos.x(), 
            end_pos.y(), 
            pen
        )
        
        # Calculate and display temporary distance
        dx = (end_pos.x() - self.measure_start_point.x()) / self.pixels_per_cell
        dy = (end_pos.y() - self.measure_start_point.y()) / self.pixels_per_cell
        pixel_distance = math.sqrt(dx*dx + dy*dy)
        meter_distance = pixel_distance * self.resolution
        
        # Add temporary text
        text_item = self.scene.addText(f"{meter_distance:.3f} m")
        text_item.setDefaultTextColor(Qt.cyan)
        font = text_item.font()
        font.setPointSize(10)
        font.setBold(True)
        text_item.setFont(font)
        
        # Position text above the line
        mid_x = (self.measure_start_point.x() + end_pos.x()) / 2
        mid_y = (self.measure_start_point.y() + end_pos.y()) / 2
        text_item.setPos(mid_x - 30, mid_y - 20)
        self.temp_measure_text = text_item

    def updateLinePreview(self, end_pos):
        """Update the temporary straight line while drawing a line."""
        if self.temp_line:
            try:
                self.scene.removeItem(self.temp_line)
            except Exception:
                pass
            self.temp_line = None
        if not self.line_start_point:
            return
        pen = QPen(Qt.black)
        pen.setWidth(max(1, int(self.cursor_size)))
        self.temp_line = self.scene.addLine(
            self.line_start_point.x(), self.line_start_point.y(),
            end_pos.x(), end_pos.y(), pen
        )
        try:
            self.temp_line.setZValue(900)
        except Exception:
            pass

    def createLine(self, start_pos, end_pos, thickness=1, from_restore=False):
        """Create a persistent straight line with given thickness and store it."""
        if not hasattr(self, 'scene') or self.scene is None:
            return None
        try:
            pen = QPen(Qt.black)
            pen.setWidth(max(1, int(thickness or 1)))
            item = self.scene.addLine(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y(), pen)
            try:
                item.setZValue(850)
            except Exception:
                pass
            try:
                from PyQt5.QtWidgets import QGraphicsItem
                item.setFlag(QGraphicsItem.ItemIsSelectable, True)
            except Exception:
                pass
            entry = {
                'item': item,
                'start_scene': (start_pos.x(), start_pos.y()),
                'end_scene': (end_pos.x(), end_pos.y()),
                'start_cell': (start_pos.x() / self.pixels_per_cell, start_pos.y() / self.pixels_per_cell),
                'end_cell': (end_pos.x() / self.pixels_per_cell, end_pos.y() / self.pixels_per_cell),
                'thickness': max(1, int(thickness or 1)),
            }
            self.lines.append(entry)
            if not from_restore:
                self.ui.statusInfo.setText("➖ Line added")
            return item
        except Exception as e:
            print('Error creating line:', e)
            return None

    def createDimension(self, start_pos, end_pos, *, from_restore=False):
        """Create a permanent dimension annotation"""
        # Calculate distance
        dx = (end_pos.x() - start_pos.x()) / self.pixels_per_cell
        dy = (end_pos.y() - start_pos.y()) / self.pixels_per_cell
        pixel_distance = math.sqrt(dx*dx + dy*dy)
        meter_distance = pixel_distance * self.resolution
        
        # Create permanent line with arrows
        pen = QPen(Qt.yellow)
        pen.setWidth(3)
        line = self.scene.addLine(
            start_pos.x(), 
            start_pos.y(),
            end_pos.x(), 
            end_pos.y(), 
            pen
        )
        
        # Add arrow heads at both ends
        arrow_size = 10
        angle = math.atan2(end_pos.y() - start_pos.y(), end_pos.x() - start_pos.x())
        
        # Arrow at start point
        arrow1_points = [
            QtCore.QPointF(start_pos.x(), start_pos.y()),
            QtCore.QPointF(
                start_pos.x() + arrow_size * math.cos(angle + 2.8),
                start_pos.y() + arrow_size * math.sin(angle + 2.8)
            ),
            QtCore.QPointF(
                start_pos.x() + arrow_size * math.cos(angle - 2.8),
                start_pos.y() + arrow_size * math.sin(angle - 2.8)
            )
        ]
        arrow1 = self.scene.addPolygon(QtGui.QPolygonF(arrow1_points), pen, QBrush(Qt.yellow))
        
        # Arrow at end point
        arrow2_points = [
            QtCore.QPointF(end_pos.x(), end_pos.y()),
            QtCore.QPointF(
                end_pos.x() - arrow_size * math.cos(angle + 2.8),
                end_pos.y() - arrow_size * math.sin(angle + 2.8)
            ),
            QtCore.QPointF(
                end_pos.x() - arrow_size * math.cos(angle - 2.8),
                end_pos.y() - arrow_size * math.sin(angle - 2.8)
            )
        ]
        arrow2 = self.scene.addPolygon(QtGui.QPolygonF(arrow2_points), pen, QBrush(Qt.yellow))
        
        # Add permanent text with background
        text_item = self.scene.addText(f"📏 {meter_distance:.3f} m")
        text_item.setDefaultTextColor(Qt.yellow)
        font = text_item.font()
        font.setPointSize(12)
        font.setBold(True)
        text_item.setFont(font)
        
        # Add background rectangle for better visibility
        text_rect = text_item.boundingRect()
        bg_rect = self.scene.addRect(
            text_rect.adjusted(-2, -2, 2, 2),
            QPen(Qt.yellow),
            QBrush(QtGui.QColor(0, 0, 0, 180))
        )
        
        # Position text above the line
        mid_x = (start_pos.x() + end_pos.x()) / 2
        mid_y = (start_pos.y() + end_pos.y()) / 2
        text_item.setPos(mid_x - text_rect.width()/2, mid_y - 30)
        bg_rect.setPos(mid_x - text_rect.width()/2, mid_y - 30)
        
        # Ensure text is above the line
        text_item.setZValue(1000)
        bg_rect.setZValue(999)
        
        # Store dimension
        dimension_group = {
            'line': line,
            'arrow1': arrow1,
            'arrow2': arrow2,
            'text': text_item,
            'background': bg_rect,
            'distance': meter_distance,
            'start_scene': (start_pos.x(), start_pos.y()),
            'end_scene': (end_pos.x(), end_pos.y()),
            'start_cell': (start_pos.x() / self.pixels_per_cell, start_pos.y() / self.pixels_per_cell),
            'end_cell': (end_pos.x() / self.pixels_per_cell, end_pos.y() / self.pixels_per_cell)
        }
        self.dimensions.append(dimension_group)
        
        if not from_restore:
            print(f"Created dimension: {meter_distance:.3f} meters")
            self.ui.statusInfo.setText(f"📏 Measured: {meter_distance:.3f} m")

    def addTextAnnotation(self, scene_pos, text, *, from_restore=False):
        """Create a movable/selectable text annotation at the given scene position."""
        try:
            # Create the text item
            # use our TextAnnotationItem subclass so we can get itemChange callbacks
            text_item = TextAnnotationItem()
            text_item.setPlainText(text)
            self.scene.addItem(text_item)
            # Scale font relative to pixels_per_cell for readability
            font = text_item.font()
            size = max(8, int(self.pixels_per_cell / 3))
            font.setPointSize(size)
            font.setBold(True)
            text_item.setFont(font)
            text_item.setDefaultTextColor(Qt.black)
            text_item.setPos(scene_pos.x(), scene_pos.y())
            text_item.setZValue(1001)

            # Make it movable and selectable
            try:
                from PyQt5.QtWidgets import QGraphicsItem
                text_item.setFlag(QGraphicsItem.ItemIsMovable, True)
                text_item.setFlag(QGraphicsItem.ItemIsSelectable, True)
                # hook up change callback so overlay can update when item moves
                text_item.setChangeCallback(self._onTextItemChanged)
                # let item push move snapshots via editor reference
                try:
                    text_item._editor_ref = self
                except Exception:
                    pass
            except Exception:
                pass

            if not from_restore:
                try:
                    text_item.setSelected(True)
                except Exception:
                    pass
                self.text_items.append(text_item)
                print(f"Added text annotation: '{text}' at ({scene_pos.x():.1f}, {scene_pos.y():.1f})")
                self.ui.statusInfo.setText(f"Added text: {text}")
            return text_item
        except Exception as e:
            print('Error creating text annotation:', e)
            return None

    def _captureTextAnnotations(self, previous_pixels_per_cell):
        """Capture the current text annotations so they can survive a scene rebuild."""
        data = []
        valid_items = []
        items = list(getattr(self, 'text_items', []))
        scale = previous_pixels_per_cell if previous_pixels_per_cell else self.pixels_per_cell or 1
        for item in items:
            try:
                if item is None or item.scene() is None:
                    continue
            except RuntimeError:
                continue
            try:
                font = item.font()
                size_f = font.pointSizeF()
                if size_f <= 0:
                    size_f = font.pointSize()
                color = item.defaultTextColor()
                color_tuple = (color.red(), color.green(), color.blue(), color.alpha())
                data.append({
                    'text': item.toPlainText(),
                    'cell_pos': (item.pos().x() / scale, item.pos().y() / scale),
                    'font_family': font.family(),
                    'font_size': size_f,
                    'font_bold': font.bold(),
                    'color': color_tuple,
                    'rotation': item.rotation(),
                    'z': item.zValue(),
                    'selected': item.isSelected(),
                })
                valid_items.append(item)
            except Exception:
                continue
        self.text_items = valid_items
        return data

    def _restoreTextAnnotations(self, text_data):
        """Recreate text annotations after rebuilding the scene."""
        restored = []
        for entry in text_data:
            try:
                cell_x, cell_y = entry.get('cell_pos', (0, 0))
                scene_pos = QtCore.QPointF(cell_x * self.pixels_per_cell, cell_y * self.pixels_per_cell)
                item = self.addTextAnnotation(scene_pos, entry.get('text', ''), from_restore=True)
                if item is None:
                    continue
                font = item.font()
                family = entry.get('font_family')
                if family:
                    font.setFamily(family)
                size = entry.get('font_size', 0)
                if size and size > 0:
                    font.setPointSizeF(size)
                font.setBold(bool(entry.get('font_bold')))
                item.setFont(font)
                color_tuple = entry.get('color')
                if color_tuple:
                    item.setDefaultTextColor(QtGui.QColor(*color_tuple))
                item.setZValue(entry.get('z', 1001))
                item.setRotation(entry.get('rotation', 0))
                restored.append(item)
                if entry.get('selected'):
                    try:
                        item.setSelected(True)
                    except Exception:
                        pass
            except Exception:
                continue
        self.text_items = restored

    def cancelMeasurement(self):
        """Cancel ongoing measurement"""
        if self.temp_measure_line:
            self.scene.removeItem(self.temp_measure_line)
            self.temp_measure_line = None
        if self.temp_measure_text:
            self.scene.removeItem(self.temp_measure_text)
            self.temp_measure_text = None
        self.measuring = False
        self.measure_start_point = None

    def cancelLineDrawing(self):
        """Cancel an in-progress line drawing operation."""
        if getattr(self, 'temp_line', None):
            try:
                self.scene.removeItem(self.temp_line)
            except Exception:
                pass
            self.temp_line = None
        self.drawing_line = False
        self.line_start_point = None

    def clearDimensions(self):
        """Clear all dimension annotations"""
        for dim in self.dimensions:
            self.scene.removeItem(dim['line'])
            self.scene.removeItem(dim['arrow1'])
            self.scene.removeItem(dim['arrow2'])
            self.scene.removeItem(dim['text'])
            self.scene.removeItem(dim['background'])
        self.dimensions.clear()
        self.selected_dimension = None
        self.cancelMeasurement()
        print("All dimensions cleared")
        self.ui.statusInfo.setText("🗑️ All dimensions cleared")

    def findDimensionAt(self, pos):
        """Find dimension at clicked position"""
        click_tolerance = 10  # pixels
        
        for dim in self.dimensions:
            # 1) Check if clicking on the measurement label/background box
            try:
                bg = dim.get('background')
                if bg is not None:
                    bg_rect_scene = bg.mapToScene(bg.boundingRect()).boundingRect()
                    if bg_rect_scene.contains(pos):
                        return dim
            except Exception:
                pass
            try:
                txt = dim.get('text')
                if txt is not None:
                    txt_rect_scene = txt.mapToScene(txt.boundingRect()).boundingRect()
                    if txt_rect_scene.contains(pos):
                        return dim
            except Exception:
                pass

            # 2) Otherwise check proximity to the dimension line
            line = dim['line'].line()
            # Check if click is near the line
            distance = self.pointToLineDistance(
                pos.x(), pos.y(),
                line.x1(), line.y1(),
                line.x2(), line.y2()
            )
            
            if distance < click_tolerance:
                return dim
        
        return None

    def pointToLineDistance(self, px, py, x1, y1, x2, y2):
        """Calculate perpendicular distance from point to line segment"""
        # Vector from line start to point
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            # Line is actually a point
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        
        # Parameter t of closest point on infinite line
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        
        # Clamp t to line segment
        t = max(0, min(1, t))
        
        # Closest point on line segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        # Distance from point to closest point
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)

    def selectDimension(self, dimension):
        """Select and highlight a dimension"""
        # Deselect previous if any
        if self.selected_dimension:
            self.deselectDimension()
        
        self.selected_dimension = dimension
        
        # Change appearance to show selection
        highlight_pen = QPen(Qt.red)
        highlight_pen.setWidth(4)
        dimension['line'].setPen(highlight_pen)
        
        # Highlight arrows
        arrow_brush = QBrush(Qt.red)
        dimension['arrow1'].setPen(highlight_pen)
        dimension['arrow1'].setBrush(arrow_brush)
        dimension['arrow2'].setPen(highlight_pen)
        dimension['arrow2'].setBrush(arrow_brush)
        
        # Highlight text
        dimension['text'].setDefaultTextColor(Qt.red)
        dimension['background'].setPen(QPen(Qt.red))
        
        print(f"Dimension selected: {dimension['distance']:.3f} m")
        self.ui.statusInfo.setText(f"🎯 Selected: {dimension['distance']:.3f} m (Press Delete to remove)")

    def deselectDimension(self):
        """Deselect currently selected dimension"""
        if not self.selected_dimension:
            return
        
        dim = self.selected_dimension
        
        # Restore original appearance
        pen = QPen(Qt.yellow)
        pen.setWidth(3)
        dim['line'].setPen(pen)
        
        arrow_brush = QBrush(Qt.yellow)
        dim['arrow1'].setPen(pen)
        dim['arrow1'].setBrush(arrow_brush)
        dim['arrow2'].setPen(pen)
        dim['arrow2'].setBrush(arrow_brush)
        
        dim['text'].setDefaultTextColor(Qt.yellow)
        dim['background'].setPen(QPen(Qt.yellow))
        
        self.selected_dimension = None
        self.ui.statusInfo.setText("📏 Measure Mode: Click two points")
        print("Dimension deselected")

    def deleteSelectedDimension(self):
        """Delete the currently selected dimension"""
        if not self.selected_dimension:
            return
        
        dim = self.selected_dimension
        
        # Remove from scene
        self.scene.removeItem(dim['line'])
        self.scene.removeItem(dim['arrow1'])
        self.scene.removeItem(dim['arrow2'])
        self.scene.removeItem(dim['text'])
        self.scene.removeItem(dim['background'])
        
        # Remove from list
        self.dimensions.remove(dim)
        
        print(f"Dimension deleted: {dim['distance']:.3f} m")
        self.ui.statusInfo.setText("🗑️ Dimension deleted")
        
        self.selected_dimension = None

    def _captureDimensions(self, previous_pixels_per_cell):
        """Capture dimension metadata so we can rebuild them after redraw."""
        data = []
        valid_dims = []
        selected_index = None
        scale = previous_pixels_per_cell if previous_pixels_per_cell else self.pixels_per_cell or 1
        for idx, dim in enumerate(list(getattr(self, 'dimensions', []))):
            try:
                if dim.get('line') is None:
                    continue
            except Exception:
                continue
            start_cell = dim.get('start_cell')
            end_cell = dim.get('end_cell')
            if not start_cell or not end_cell:
                start_scene = dim.get('start_scene')
                end_scene = dim.get('end_scene')
                if not start_scene or not end_scene:
                    try:
                        line = dim['line'].line()
                        start_scene = (line.x1(), line.y1())
                        end_scene = (line.x2(), line.y2())
                    except Exception:
                        continue
                start_cell = (start_scene[0] / scale, start_scene[1] / scale)
                end_cell = (end_scene[0] / scale, end_scene[1] / scale)
            data.append({
                'start_cell': start_cell,
                'end_cell': end_cell,
            })
            valid_dims.append(dim)
            if dim is self.selected_dimension:
                selected_index = len(data) - 1
        self.dimensions = valid_dims
        if selected_index is not None and selected_index >= len(data):
            selected_index = None
        return data, selected_index

    def _restoreDimensions(self, dimensions_data, selected_index):
        """Restore dimension annotations after a scene rebuild."""
        restored_selection = None
        for idx, entry in enumerate(dimensions_data):
            try:
                start_cell = entry.get('start_cell')
                end_cell = entry.get('end_cell')
                if not start_cell or not end_cell:
                    continue
                start_pos = QtCore.QPointF(start_cell[0] * self.pixels_per_cell,
                                           start_cell[1] * self.pixels_per_cell)
                end_pos = QtCore.QPointF(end_cell[0] * self.pixels_per_cell,
                                         end_cell[1] * self.pixels_per_cell)
                self.createDimension(start_pos, end_pos, from_restore=True)
                if selected_index is not None and idx == selected_index:
                    restored_selection = self.dimensions[-1]
            except Exception:
                continue
        if restored_selection is not None:
            self.selectDimension(restored_selection)

    def _captureLines(self, previous_pixels_per_cell):
        """Capture drawn straight lines for persistence across redraw/undo."""
        data = []
        valid = []
        scale = previous_pixels_per_cell if previous_pixels_per_cell else self.pixels_per_cell or 1
        for entry in list(getattr(self, 'lines', [])):
            try:
                item = entry.get('item') if isinstance(entry, dict) else None
                if item is None or item.scene() is None:
                    continue
                # Prefer stored cell coords; fall back to item's current scene coords
                start_cell = entry.get('start_cell')
                end_cell = entry.get('end_cell')
                if not start_cell or not end_cell:
                    try:
                        ln = item.line()
                        start_cell = (ln.x1() / scale, ln.y1() / scale)
                        end_cell = (ln.x2() / scale, ln.y2() / scale)
                    except Exception:
                        continue
                thickness = int(entry.get('thickness', 1))
                data.append({
                    'start_cell': start_cell,
                    'end_cell': end_cell,
                    'thickness': max(1, thickness),
                })
                valid.append(entry)
            except Exception:
                continue
        self.lines = valid
        return data

    def _restoreLines(self, lines_data):
        """Restore drawn straight lines from captured data."""
        # Clear existing line items from scene and model list before restoring
        try:
            for entry in list(getattr(self, 'lines', [])):
                try:
                    item = entry.get('item')
                    if item is not None and item.scene() is self.scene:
                        self.scene.removeItem(item)
                except Exception:
                    pass
        except Exception:
            pass
        self.lines = []

        for entry in lines_data or []:
            try:
                start_cell = entry.get('start_cell')
                end_cell = entry.get('end_cell')
                if not start_cell or not end_cell:
                    continue
                start_pos = QtCore.QPointF(start_cell[0] * self.pixels_per_cell,
                                           start_cell[1] * self.pixels_per_cell)
                end_pos = QtCore.QPointF(end_cell[0] * self.pixels_per_cell,
                                         end_cell[1] * self.pixels_per_cell)
                thickness = int(entry.get('thickness', 1))
                self.createLine(start_pos, end_pos, thickness, from_restore=True)
            except Exception:
                continue

    def _captureState(self):
        """Capture current text, dimensions, and lines for undo/redo/restores."""
        scale = getattr(self, 'pixels_per_cell', 1) or 1
        text_data = self._captureTextAnnotations(scale)
        dims_data, selected_idx = self._captureDimensions(scale)
        lines_data = self._captureLines(scale)
        return {
            'text': text_data,
            'dimensions': dims_data,
            'selected_dimension_index': selected_idx,
            'lines': lines_data,
        }

    def _restoreState(self, state):
        """Restore text and dimensions from a snapshot state."""
        if not state:
            return
        # Clear current overlays
        try:
            if hasattr(self, 'current_text_overlay') and self.current_text_overlay:
                self.current_text_overlay.destroy()
        except Exception:
            pass
        self.current_text_overlay = None

        # Remove current dimensions from scene
        try:
            for dim in list(getattr(self, 'dimensions', [])):
                try:
                    self.scene.removeItem(dim['line'])
                    self.scene.removeItem(dim['arrow1'])
                    self.scene.removeItem(dim['arrow2'])
                    self.scene.removeItem(dim['text'])
                    self.scene.removeItem(dim['background'])
                except Exception:
                    pass
        except Exception:
            pass
        self.dimensions = []
        self.selected_dimension = None

        # Remove current text annotations from scene
        try:
            for item in list(getattr(self, 'text_items', [])):
                try:
                    if item is not None and item.scene() is self.scene:
                        self.scene.removeItem(item)
                except Exception:
                    pass
        except Exception:
            pass
        self.text_items = []

        # Restore from snapshot
        dims = state.get('dimensions', [])
        sel_idx = state.get('selected_dimension_index')
        self._restoreDimensions(dims, sel_idx)
        self._restoreTextAnnotations(state.get('text', []))
        self._restoreLines(state.get('lines', []))

    def _stateChanged(self, a, b):
        try:
            return a != b
        except Exception:
            return True

    def _pushSnapshotAction(self, label, fn_apply):
        """Capture state before and after fn_apply; push an undo command if changed."""
        before = self._captureState()
        fn_apply()
        after = self._captureState()
        if self._stateChanged(before, after):
            try:
                self.undo_stack.push(SnapshotCommand(self, before, after, label))
            except Exception:
                pass

    def _beginSnapshot(self, label):
        try:
            self._active_snapshot_label = label
            self._active_snapshot_before = self._captureState()
        except Exception:
            self._active_snapshot_label = None
            self._active_snapshot_before = None

    def _endSnapshot(self, label=None):
        try:
            before = getattr(self, '_active_snapshot_before', None)
            if before is None:
                return
            after = self._captureState()
            lab = label or getattr(self, '_active_snapshot_label', "Edit")
            if self._stateChanged(before, after):
                self.undo_stack.push(SnapshotCommand(self, before, after, lab))
        finally:
            self._active_snapshot_before = None
            self._active_snapshot_label = None

    def createCursorIndicator(self):
        """Create a visual cursor indicator"""
        if not hasattr(self, 'scene') or not self.scene:
            return
            
        # Create a circle to show brush size
        pen = QPen(QtGui.QColor(255, 0, 255, 150))  # Semi-transparent magenta
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        
        radius = self.cursor_size * self.pixels_per_cell / 2
        self.cursor_indicator = self.scene.addEllipse(
            -radius, -radius, radius * 2, radius * 2,
            pen,
            QBrush(QtGui.QColor(255, 0, 255, 30))  # Very light fill
        )
        self.cursor_indicator.setZValue(10000)  # Always on top
        
    def updateCursorIndicator(self, scene_pos):
        """Update cursor indicator position"""
        if self.cursor_indicator and hasattr(self, 'scene'):
            radius = self.cursor_size * self.pixels_per_cell / 2
            self.cursor_indicator.setRect(
                scene_pos.x() - radius,
                scene_pos.y() - radius,
                radius * 2,
                radius * 2
            )
            
            # Change color based on mode
            if self.tool_mode == 'measure':
                pen = QPen(QtGui.QColor(0, 255, 255, 150))  # Cyan for measure
                pen.setWidth(2)
                pen.setStyle(Qt.DashLine)
                self.cursor_indicator.setPen(pen)
                self.cursor_indicator.setBrush(QBrush(QtGui.QColor(0, 255, 255, 20)))
            else:
                pen = QPen(QtGui.QColor(255, 0, 255, 150))  # Magenta for paint
                pen.setWidth(2)
                pen.setStyle(Qt.DashLine)
                self.cursor_indicator.setPen(pen)
                self.cursor_indicator.setBrush(QBrush(QtGui.QColor(255, 0, 255, 30)))
    
    def updateCursorIndicatorSize(self):
        """Update cursor indicator size when brush size changes"""
        if self.cursor_indicator and hasattr(self, 'scene'):
            # Get current position
            rect = self.cursor_indicator.rect()
            center_x = rect.center().x()
            center_y = rect.center().y()
            
            # Update size
            radius = self.cursor_size * self.pixels_per_cell / 2
            self.cursor_indicator.setRect(
                center_x - radius,
                center_y - radius,
                radius * 2,
                radius * 2
            )
    
    def hideCursorIndicator(self):
        """Hide the cursor indicator"""
        if self.cursor_indicator and hasattr(self, 'scene'):
            self.scene.removeItem(self.cursor_indicator)
            self.cursor_indicator = None

    def handleZoom(self, index):
        previous_pixels = getattr(self, 'pixels_per_cell', self.min_multiplier)
        self.zoom = self.ui.zoomBox.currentData()
        if not self.zoom:
            self.zoom = 1
        self.pixels_per_cell = self.min_multiplier * self.zoom 
        self.draw_map(previous_pixels_per_cell=previous_pixels)
    
    def handleZoomSlider(self, value):
        """Handle zoom changes from the slider - value is percent (50..400)."""
        previous_pixels = getattr(self, 'pixels_per_cell', self.min_multiplier)
        try:
            # Convert percent to scale factor
            self.zoom = max(0.01, float(value) / 100.0)
        except Exception:
            return
        self.pixels_per_cell = self.min_multiplier * self.zoom
        # Update status info with current zoom percent
        try:
            self.ui.statusInfo.setText(f"Zoom: {int(round(self.zoom*100))}%")
            if hasattr(self.ui, 'zoomPercentLbl') and self.ui.zoomPercentLbl is not None:
                self.ui.zoomPercentLbl.setText(f"{int(round(self.zoom*100))}%")
        except Exception:
            pass
        self.draw_map(previous_pixels_per_cell=previous_pixels)
        

    def read(self, fn):
        # try to open as fn or fn.pgm. If not found, also look in the
        # repository-level `maps/` directory (useful for keeping project
        # maps in one place).
        #
        # Resolution order:
        # 1. Exactly `fn` (path as given)
        # 2. `fn + '.pgm'` (same dir)
        # 3. `maps/fn` (maps directory)
        # 4. `maps/fn + '.pgm'`
        #
        # Create maps dir path relative to repository root (parent of src)
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        maps_dir = os.path.join(repo_root, 'maps')

        # Ensure maps_dir exists (created earlier by the assistant if needed)
        try:
            os.makedirs(maps_dir, exist_ok=True)
        except Exception:
            pass

        tried_paths = []

        def try_open(path):
            tried_paths.append(path)
            try:
                im = Image.open(path)
                return im, path
            except Exception:
                return None, None

        # 1) try as provided
        im, used = try_open(fn)

        # 2) try with .pgm extension next
        if im is None:
            fnpgm = fn + '.pgm'
            im, used = try_open(fnpgm)

        # 3) try in maps/ directory
        if im is None:
            maps_path = os.path.join(maps_dir, fn)
            im, used = try_open(maps_path)

        # 4) try maps/<name>.pgm
        if im is None:
            maps_path_pgm = os.path.join(maps_dir, fn + '.pgm')
            im, used = try_open(maps_path_pgm)

        if im is None:
            print("Tried the following paths:")
            for p in tried_paths:
                print("  ", p)
            print("ERROR:  Cannot open file", fn)
            sys.exit(1)

        self.im = im
        self.fn = used

        if self.im.format != 'PPM':
            print("ERROR:  This is not a PGM formatted file.")
            sys.exit(1)

        if self.im.mode != 'L':
            print("ERROR:  This PGM file is not of mode L.")
            sys.exit(1)   

        self.map_width_cells = self.im.size[0]
        self.map_height_cells = self.im.size[1]

        self.ui.filename_lbl.setText(os.path.basename(self.fn)) 
        self.ui.width_lbl.setText(f"{self.map_width_cells} pixels")
        self.ui.height_lbl.setText(f"{self.map_height_cells} pixels")
        
        # Update status
        self.ui.statusInfo.setText("Map loaded successfully!")
        self.ui.statusbar.showMessage(f"Loaded: {os.path.basename(self.fn)} ({self.map_width_cells}x{self.map_height_cells})")

        # Try to find corresponding YAML file. We prefer a YAML next to the
        # actual image we opened (`used` path), then fall back to common
        # alternatives (original fn + .yaml, maps/ directory).
        # Build candidate YAML paths in order.
        candidates = []

        # 1) same directory as the image we actually opened
        try:
            base_used = os.path.splitext(self.fn)[0]
            candidates.append(base_used + '.yaml')
        except Exception:
            pass

        # 2) if the user passed a simple name like 'floor', try that next
        try:
            candidates.append(os.path.splitext(fn)[0] + '.yaml')
        except Exception:
            pass

        # 3) maps/<name>.yaml in repo-level maps dir
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            maps_dir = os.path.join(repo_root, 'maps')
            candidates.append(os.path.join(maps_dir, os.path.splitext(fn)[0] + '.yaml'))
        except Exception:
            pass

        yaml_found = False
        yaml_error = None
        for fn_yaml in candidates:
            if not fn_yaml:
                continue
            try:
                with open(fn_yaml, 'r') as stream:
                    docs = yaml.load_all(stream, Loader=yaml.FullLoader)
                    for doc in docs:
                        # Validate expected keys
                        self.occupied_thresh = doc['occupied_thresh']  # probability its occupied
                        self.free_thresh = doc['free_thresh']  # probability its uncertain or occupied
                        self.resolution = doc['resolution']    # in meters per cell
                        self.origin_x = doc['origin'][0]
                        self.origin_y = doc['origin'][1]
                    yaml_found = True
                    self.yaml_path = fn_yaml
                    break
            except Exception as e:
                yaml_error = e
                continue

        if not yaml_found:
            if yaml_error:
                print("ERROR:  Corresponding YAML file is missing or incorrectly formatted.")
                print("Last YAML parse error:", yaml_error)
            else:
                print("ERROR:  Corresponding YAML file is missing or incorrectly formatted.")
            sys.exit(1)


    def mapClick(self, event):
        # Ensure the viewport has focus on click so that subsequent key
        # presses are delivered to our eventFilter
        try:
            self.ui.graphicsView.viewport().setFocus()
        except Exception:
            pass
        # Selection tool: let the scene handle selection/dragging
        if self.tool_mode == 'select':
            try:
                QtWidgets.QGraphicsScene.mousePressEvent(self.scene, event)
            except Exception:
                pass
            return

        # If text mode, add or edit text annotations
        if self.tool_mode == 'text':
            # If clicking existing text/handles/overlay, don't create a new text
            try:
                hit_items = self.scene.items(event.scenePos())
            except Exception:
                hit_items = []
            for it in hit_items:
                if isinstance(it, (TextAnnotationItem, QtWidgets.QGraphicsTextItem, ResizeHandle)):
                    try:
                        QtWidgets.QGraphicsScene.mousePressEvent(self.scene, event)
                    except Exception:
                        pass
                    return

            if event.button() != QtCore.Qt.LeftButton:
                QtWidgets.QGraphicsScene.mousePressEvent(self.scene, event)
                return

            scene_pos = event.scenePos()
            try:
                def do_add():
                    item = self.addTextAnnotation(scene_pos, "Text")
                    if item is not None:
                        item.beginEdit()
                self._pushSnapshotAction("Add Text", do_add)
            except Exception as e:
                print('Error adding text annotation:', e)
            return
        if self.tool_mode == 'measure':
            # Check if clicking on an existing dimension to select it
            scene_pos = event.scenePos()

            # First check if clicking near any dimension line
            clicked_dimension = self.findDimensionAt(scene_pos)
            if clicked_dimension:
                self.selectDimension(clicked_dimension)
                return

            # Otherwise handle measurement creation
            if not self.measuring:
                # First click - start measurement
                self.measuring = True
                self.measure_start_point = scene_pos
                print(f"Measurement started at ({scene_pos.x():.1f}, {scene_pos.y():.1f})")
                self.ui.statusInfo.setText("📏 Click second point (ESC to cancel)")
            else:
                # Second click - complete measurement (undoable)
                self._pushSnapshotAction(
                    "Add Dimension",
                    lambda: self.createDimension(self.measure_start_point, scene_pos)
                )
                # Clean up temporary items
                if self.temp_measure_line:
                    self.scene.removeItem(self.temp_measure_line)
                    self.temp_measure_line = None
                if self.temp_measure_text:
                    self.scene.removeItem(self.temp_measure_text)
                    self.temp_measure_text = None
                # Reset for next measurement
                self.measuring = False
                self.measure_start_point = None
                self.ui.statusInfo.setText("📏 Measure Mode: Click two points")
            return

        if self.tool_mode == 'line':
            scene_pos = event.scenePos()
            if not self.drawing_line:
                # First click - start line drawing
                self.drawing_line = True
                self.line_start_point = scene_pos
                self.ui.statusInfo.setText("➖ Click second point (ESC to cancel)")
            else:
                # Second click - finalize line (undoable)
                start = QtCore.QPointF(self.line_start_point)
                end = QtCore.QPointF(scene_pos)
                thickness = max(1, int(self.cursor_size))
                self._pushSnapshotAction(
                    "Add Line",
                    lambda: self.createLine(start, end, thickness)
                )
                # Clean up temporary preview
                if self.temp_line:
                    try:
                        self.scene.removeItem(self.temp_line)
                    except Exception:
                        pass
                    self.temp_line = None
                self.drawing_line = False
                self.line_start_point = None
                self.ui.statusInfo.setText("➖ Line Mode: Click two points")
            return
        
        # Paint tool mode
        # get current model value
        x = math.floor(event.scenePos().x() / self.pixels_per_cell)
        y = math.floor(event.scenePos().y() / self.pixels_per_cell)
        print(f"Map clicked at ({x}, {y}), color mode: {self.color}, brush size: {self.cursor_size}")

        if self.color != 'alternate':
            # Use brush painting for non-alternate modes
            self.paint_area(x, y, self.cursor_size)
        else:
            # Original alternate behavior for single click
            val = self.im.getpixel((x,y))
            # determine next value in sequence white->black->gray
            if val <= (255.0 * (1.0 - self.occupied_thresh)):  # if black, become gray
                val = 200
            elif val <= (255.0 * (1.0 - self.free_thresh)):  # else if gray, become white
                val = 255
            else:  # else its white, become black
                val = 0    

            # update model with new value
            self.im.putpixel((x,y), val)    

            # redraw cell in new color
            color = self.value2color(val)
            self.color_cell(x, y, color)


    def value2color(self, val):
        if val > (255.0 * (1.0 - self.free_thresh)):
            return Qt.white
        elif val > (255.0 * (1.0 - self.occupied_thresh)):
            return Qt.gray
        else:
            return Qt.black

    def color_cell(self, x, y, color):
        pen = QPen(color)
        pen.setWidth(1)
        if self.pixels_per_cell > 10:
            pen = QPen(Qt.lightGray)
        brush = QBrush(color)
        #x = x * self.pixels_per_cell
        #y = y * self.pixels_per_cell
  
        qrect = self.grids[x][y]
        qrect.setBrush(brush)
        qrect.setPen(pen)

        
    def add_cell(self, x, y, color):
        pen = QPen(color)
        pen.setWidth(1)
        if self.pixels_per_cell > 10:
            pen = QPen(Qt.lightGray)
        brush = QBrush(color)
        x = x * self.pixels_per_cell
        y = y * self.pixels_per_cell
        return self.scene.addRect(x, y, self.pixels_per_cell, self.pixels_per_cell, pen, brush)
    def draw_map(self, previous_pixels_per_cell=None):        
        prev_scale = previous_pixels_per_cell if previous_pixels_per_cell else getattr(self, 'pixels_per_cell', 1)
        if prev_scale <= 0:
            prev_scale = 1

        preserved_text = self._captureTextAnnotations(prev_scale)
        preserved_dims, selected_dim_index = self._captureDimensions(prev_scale)
        # Preserve drawn lines across scene rebuild
        preserved_lines = self._captureLines(prev_scale)

        # Drop any lingering overlay tied to the old scene
        if hasattr(self, 'current_text_overlay') and self.current_text_overlay:
            try:
                self.current_text_overlay.destroy()
            except Exception:
                pass
            self.current_text_overlay = None

        self.scene = QtWidgets.QGraphicsScene()
        self.ui.graphicsView.setScene(self.scene)
        # Track selection changes on the scene so we can update text property UI
        try:
            self.scene.selectionChanged.connect(self.onSelectionChanged)
        except Exception:
            pass
        self.scene.mousePressEvent = self.mapClick
        self.grids = []

        # draw the cells
        for x in range(0,self.map_width_cells):
            grid_col = []
            for y in range(0, self.map_height_cells):
                val = self.im.getpixel((x,y))
                color = self.value2color(val)
                qrect = self.add_cell(x,y,color)
                grid_col.append(qrect)
            self.grids.append(grid_col)

        # draw the grid lines
        if self.pixels_per_cell > 10:
            pen = QPen(Qt.lightGray)
            pen.setWidth(1)
            pixel_width = self.map_width_cells * self.pixels_per_cell
            pixel_height = self.map_height_cells * self.pixels_per_cell
            for x in range(0, pixel_width, self.pixels_per_cell):
                self.scene.addLine(x, 0, x, pixel_height, pen)
            for y in range(0, pixel_height, self.pixels_per_cell):
                self.scene.addLine(0, y, pixel_width, y, pen)

        # Restore dimensions, lines, and text annotations after rebuilding the grid
        self.dimensions = []
        self.selected_dimension = None
        self._restoreDimensions(preserved_dims, selected_dim_index)
        self._restoreLines(preserved_lines)
        self._restoreTextAnnotations(preserved_text)

        # Recreate cursor indicator after redrawing scene if it previously existed
        recreate_cursor = bool(self.cursor_indicator)
        if recreate_cursor:
            self.cursor_indicator = None
            self.createCursorIndicator()
    def closeEvent(self, event):
        self.close()

    def saveEvent(self, event):
        """Save two outputs into an `output/` folder at the repo root:
        - raw PGM (current map model without annotations)
        - annotated PNG (renders the QGraphicsScene including annotations)
        """
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        out_dir = os.path.join(repo_root, 'output')
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            pass

        base_name = os.path.splitext(os.path.basename(self.fn))[0]

        # 1) Save raw PGM (the model image without annotations)
        raw_path = os.path.join(out_dir, base_name + '.pgm')
        try:
            self.im.save(raw_path)
            print(f"Raw map saved to: {raw_path}")
        except Exception as e:
            self.ui.statusInfo.setText("❌ Error saving raw map!")
            self.ui.statusbar.showMessage(f"Error saving raw map: {str(e)}", 5000)
            print(f"Error saving raw map: {e}")
            return

        # 2) Render annotated scene to an image and save as PNG
        try:
            pixel_width = int(self.map_width_cells * self.pixels_per_cell)
            pixel_height = int(self.map_height_cells * self.pixels_per_cell)

            # Create QImage canvas with alpha for annotations
            qim = QtGui.QImage(pixel_width, pixel_height, QtGui.QImage.Format_ARGB32)
            qim.fill(QtGui.QColor(0, 0, 0, 0))

            painter = QtGui.QPainter(qim)
            # Render the scene at 1:1 scale
            self.scene.render(painter)
            painter.end()

            annotated_path = os.path.join(out_dir, base_name + '_annotated.png')
            saved = qim.save(annotated_path)
            if not saved:
                raise IOError('Failed to save annotated image')
            print(f"Annotated map saved to: {annotated_path}")
        except Exception as e:
            self.ui.statusInfo.setText("❌ Error saving annotated map!")
            self.ui.statusbar.showMessage(f"Error saving annotated map: {str(e)}", 5000)
            print(f"Error saving annotated map: {e}")
            return

        # Success
        self.ui.statusInfo.setText(f"💾 Saved raw and annotated maps to {out_dir}")
        self.ui.statusbar.showMessage(f"Saved: {os.path.basename(raw_path)} and {os.path.basename(annotated_path)}", 5000)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('ERROR:  Must provide map file name - with or without .pgm extension.')
        print()
        print('     $ python MapEditor.py map_file_name')
        print()
    # On Linux without a graphical display, fallback to offscreen platform to avoid Qt crashes.
    try:
        if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'):
            print('INFO: No DISPLAY found. Using offscreen platform (set QT_QPA_PLATFORM=offscreen).')
            os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    except Exception:
        pass
    app = QtWidgets.QApplication(sys.argv)
    window = MapEditor(sys.argv[1])
    window.show()
    try:
        sys.exit(app.exec_())
    except Exception as e:
        print('ERROR: Qt application terminated with an exception:', e)
        sys.exit(1)
