from PyQt5 import QtCore, QtGui, QtWidgets, uic

from ui_map_editor import Ui_MapEditor

from PyQt5.QtGui import QPainter, QBrush, QPen
from PyQt5.QtCore import Qt

import math
import yaml
from PIL import Image
import sys
import os


class MapEditor(QtWidgets.QMainWindow):
    def __init__(self, fn):
        super(MapEditor, self).__init__()

        # two approaches to integrating tool generated ui file shown below
        
        # setup user interface directly from ui file
        #uic.loadUi('UI_MapEditor.ui', self)

        # setup user interface from py module converted from ui file
        self.ui = Ui_MapEditor()
        self.ui.setupUi(self)

        self.setMinimumSize(600, 600)
        
        # Initialize cursor indicator early
        self.cursor_indicator = None

        self.ui.zoomBox.addItem("100 %", 1)
        self.ui.zoomBox.addItem("200 %", 2)
        self.ui.zoomBox.addItem("400 %", 4)
        self.ui.zoomBox.addItem("800 %", 8)
        self.ui.zoomBox.addItem("1600 %", 16)
        self.ui.zoomBox.currentIndexChanged.connect(self.handleZoom)
        # Slider-based zoom control (1..16 multiplier)
        try:
            self.ui.zoomSlider.valueChanged.connect(self.handleZoomSlider)
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

        view_width = self.frameGeometry().width()

        self.min_multiplier = math.ceil(view_width / self.map_width_cells)
        self.zoom = 1
        self.pixels_per_cell = self.min_multiplier * self.zoom 

        self.draw_map()
        
        self.ui.closeButton.clicked.connect(self.closeEvent)
        self.ui.saveButton.clicked.connect(self.saveEvent)
        self.ui.clearDimensionsBtn.clicked.connect(self.clearDimensions)

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


    def eventFilter(self, source, event):
        # Handle ESC key to cancel actions
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                if self.tool_mode == 'measure' and self.measuring:
                    self.cancelMeasurement()
                    self.ui.statusInfo.setText("📏 Measurement cancelled - Click to start")
                    print("Measurement cancelled with ESC")
                elif self.selected_dimension:
                    self.deselectDimension()
                return True
            elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
                if self.selected_dimension:
                    self.deleteSelectedDimension()
                    return True

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
        
        # Handle mouse enter/leave to show/hide cursor
        elif event.type() == QtCore.QEvent.Enter and source is self.ui.graphicsView.viewport():
            if not self.cursor_indicator:
                self.createCursorIndicator()
                
        elif event.type() == QtCore.QEvent.Leave and source is self.ui.graphicsView.viewport():
            self.hideCursorIndicator()
            
        return super(MapEditor, self).eventFilter(source, event)

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
        
        if self.scene.width() and self.scene.height():
            x = int(self.ui.graphicsView.horizontalScrollBar().value() /  self.scene.width() * self.im.size[0])
            y = int(self.ui.graphicsView.verticalScrollBar().value() /  self.scene.height() * self.im.size[1])
            width = int(self.ui.graphicsView.viewport().size().width() /  self.scene.width() * self.im.size[0])
            height = int(self.ui.graphicsView.viewport().size().height() /  self.scene.height() * self.im.size[1])
            self.drawBox(x, y, width, height)


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
        
        if self.tool_mode == 'measure':
            self.ui.statusInfo.setText("📏 Measure Mode: Click two points")
            # Disable color selection in measure mode
            self.ui.colorBox.setEnabled(False)
            self.ui.cursorSizeSlider.setEnabled(False)
            self.ui.cursorSizeSpinBox.setEnabled(False)
        else:
            self.ui.statusInfo.setText("🖌️ Paint Mode")
            self.ui.colorBox.setEnabled(True)
            self.ui.cursorSizeSlider.setEnabled(True)
            self.ui.cursorSizeSpinBox.setEnabled(True)
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

    def createDimension(self, start_pos, end_pos):
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
            'start': (start_pos.x(), start_pos.y()),
            'end': (end_pos.x(), end_pos.y())
        }
        self.dimensions.append(dimension_group)
        
        print(f"Created dimension: {meter_distance:.3f} meters")
        self.ui.statusInfo.setText(f"📏 Measured: {meter_distance:.3f} m")

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
        self.zoom = self.ui.zoomBox.currentData()
        self.pixels_per_cell = self.min_multiplier * self.zoom 
        self.draw_map()
    
    def handleZoomSlider(self, value):
        """Handle zoom changes from the slider (value is integer multiplier)."""
        try:
            self.zoom = int(value)
        except Exception:
            return
        self.pixels_per_cell = self.min_multiplier * self.zoom
        # If a zoomBox exists, try to keep it in sync by selecting nearest index
        try:
            # find the combo index whose data is closest to current zoom
            best_idx = 0
            best_diff = None
            for i in range(self.ui.zoomBox.count()):
                d = self.ui.zoomBox.itemData(i)
                if d is None:
                    continue
                diff = abs(d - self.zoom)
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_idx = i
            self.ui.zoomBox.setCurrentIndex(best_idx)
        except Exception:
            pass

        self.draw_map()
        

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
                # Second click - complete measurement
                self.createDimension(self.measure_start_point, scene_pos)
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


    def draw_map(self):        
        self.scene = QtWidgets.QGraphicsScene()
        self.ui.graphicsView.setScene(self.scene)
        self.scene.mousePressEvent = self.mapClick
        self.grids = []

        # draw the cells
        self.scene.clear()
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
            pixel_height =self. map_height_cells * self.pixels_per_cell
            for x in range(0, pixel_width, self.pixels_per_cell):
                self.scene.addLine(x, 0, x, pixel_height, pen)
            for y in range(0, pixel_height, self.pixels_per_cell):
                self.scene.addLine(0, y, pixel_width, y, pen)
        
        # Recreate cursor indicator after redrawing scene
        if self.cursor_indicator:
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
    app = QtWidgets.QApplication(sys.argv)
    window = MapEditor(sys.argv[1])
    window.show()
    sys.exit(app.exec_())
