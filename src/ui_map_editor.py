# -*- coding: utf-8 -*-

# Enhanced UI for ROS Map Editor with modern styling and new features
# Features: Map rotation, cursor size control, improved layout

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MapEditor(object):
    def setupUi(self, MapEditor):
        MapEditor.setObjectName("MapEditor")
        MapEditor.resize(1200, 800)
        MapEditor.setMinimumSize(QtCore.QSize(1000, 700))
        
        # Set modern styling (refined dark theme)
        MapEditor.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1f1f1f;
                color: #f2f2f2;
                font-family: 'Noto Sans', 'DejaVu Sans', sans-serif;
                font-size: 12px;
            }

            QGraphicsView {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }

            QLabel {
                color: #eaeaea;
                font-weight: 600;
                font-size: 12px;
            }

            /* Inputs */
            QComboBox, QSpinBox {
                background-color: #2c2c2c;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px 8px;
                color: #ffffff;
            }
            QComboBox:hover, QSpinBox:hover {
                border-color: #2b9cff;
            }
            QComboBox::drop-down { width: 20px; border: none; }
            QComboBox::down-arrow {
                image: none;
                border: 2px solid #ffffff;
                width: 6px; height: 6px; margin-right: 6px;
                border-top: none; border-left: none;
            }

            /* Buttons */
            QPushButton {
                background-color: #2b9cff;
                border: 1px solid #2b9cff;
                border-radius: 6px;
                color: #ffffff;
                font-weight: 600;
                padding: 8px 14px;
                min-height: 30px;
            }
            QPushButton:hover { background-color: #1685e6; border-color: #1685e6; }
            QPushButton:pressed { background-color: #0f6dbd; border-color: #0f6dbd; }

            /* Sliders */
            QSlider::groove:horizontal {
                border: 1px solid #3d3d3d;
                height: 8px;
                background: #2b2b2b;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2b9cff;
                border: 1px solid #2b9cff;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover { background: #1685e6; border-color: #1685e6; }

            /* Group boxes as cards */
            QGroupBox {
                font-weight: 700;
                border: 1px solid #3d3d3d;
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 10px;
                background-color: #262626;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                background-color: transparent;
            }

            /* Scrollbars */
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #2a2a2a; border: none; border-radius: 4px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #3e3e3e; border-radius: 4px; min-height: 20px; min-width: 20px;
            }
            QScrollBar::handle:hover { background: #4a4a4a; }
            QScrollBar::add-line, QScrollBar::sub-line { background: none; border: none; }

            /* Status bar and tooltips */
            QStatusBar { background-color: #202020; color: #cfcfcf; }
            QToolTip { color: #f2f2f2; background-color: #2c2c2c; border: 1px solid #3d3d3d; }
        """)
        
        self.centralwidget = QtWidgets.QWidget(MapEditor)
        self.centralwidget.setObjectName("centralwidget")
        
        # Main layout
        self.mainLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.mainLayout.setObjectName("mainLayout")
        self.mainLayout.setSpacing(10)
        self.mainLayout.setContentsMargins(10, 10, 10, 10)
        
        # Top toolbar
        self.toolbarFrame = QtWidgets.QFrame(self.centralwidget)
        self.toolbarFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.toolbarFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.toolbarFrame.setStyleSheet("""
            QFrame {
                background-color: #404040;
                border-radius: 8px;
                padding: 5px;
            }
        """)
        self.toolbarLayout = QtWidgets.QHBoxLayout(self.toolbarFrame)
        self.toolbarLayout.setSpacing(15)
        
        # File info group
        self.fileInfoGroup = QtWidgets.QGroupBox("File Information")
        self.fileInfoLayout = QtWidgets.QFormLayout(self.fileInfoGroup)
        
        self.label_3 = QtWidgets.QLabel("File:")
        self.filename_lbl = QtWidgets.QLabel("No file loaded")
        self.label_4 = QtWidgets.QLabel("Width:")
        self.width_lbl = QtWidgets.QLabel("0")
        self.label_5 = QtWidgets.QLabel("Height:")
        self.height_lbl = QtWidgets.QLabel("0")
        
        self.fileInfoLayout.addRow(self.label_3, self.filename_lbl)
        self.fileInfoLayout.addRow(self.label_4, self.width_lbl)
        self.fileInfoLayout.addRow(self.label_5, self.height_lbl)
        
        # Tools group
        self.toolsGroup = QtWidgets.QGroupBox("Tools")
        self.toolsLayout = QtWidgets.QVBoxLayout(self.toolsGroup)
        
        # Tool mode selection
        self.toolModeLayout = QtWidgets.QHBoxLayout()
        self.toolModeLabel = QtWidgets.QLabel("Tool Mode:")
        self.toolModeBox = QtWidgets.QComboBox()
        self.toolModeBox.addItem("🖱️ Select", "select")
        self.toolModeBox.addItem("🖌️ Paint", "paint")
        self.toolModeBox.addItem("📏 Measure", "measure")
        self.toolModeBox.addItem("➖ Line", "line")
        self.toolModeBox.addItem("🔤 Text", "text")
        self.toolModeLayout.addWidget(self.toolModeLabel)
        self.toolModeLayout.addWidget(self.toolModeBox)
        
        # Color selection
        self.colorLayout = QtWidgets.QHBoxLayout()
        self.label_11 = QtWidgets.QLabel("Color Mode:")
        self.colorBox = QtWidgets.QComboBox()
        self.colorLayout.addWidget(self.label_11)
        self.colorLayout.addWidget(self.colorBox)
        
        # Cursor size
        self.cursorLayout = QtWidgets.QHBoxLayout()
        self.cursorLabel = QtWidgets.QLabel("Brush Size:")
        self.cursorSizeSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.cursorSizeSlider.setMinimum(1)
        self.cursorSizeSlider.setMaximum(20)
        self.cursorSizeSlider.setValue(1)
        self.cursorSizeSpinBox = QtWidgets.QSpinBox()
        self.cursorSizeSpinBox.setMinimum(1)
        self.cursorSizeSpinBox.setMaximum(20)
        self.cursorSizeSpinBox.setValue(1)
        # Ensure arrows are visible for increase/decrease
        try:
            self.cursorSizeSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.UpDownArrows)
        except Exception:
            pass
        
        self.cursorLayout.addWidget(self.cursorLabel)
        self.cursorLayout.addWidget(self.cursorSizeSlider)
        self.cursorLayout.addWidget(self.cursorSizeSpinBox)

        # Text properties (size + rotation)
        self.textPropLayout = QtWidgets.QGridLayout()
        self.textSizeLabel = QtWidgets.QLabel("Text Size:")
        self.textSizeSpinBox = QtWidgets.QSpinBox()
        self.textSizeSpinBox.setMinimum(6)
        self.textSizeSpinBox.setMaximum(144)
        self.textSizeSpinBox.setValue(12)
        try:
            self.textSizeSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.UpDownArrows)
        except Exception:
            pass

        self.textRotationLabel = QtWidgets.QLabel("Text Rot:")
        self.textRotationSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.textRotationSlider.setMinimum(-180)
        self.textRotationSlider.setMaximum(180)
        self.textRotationSlider.setValue(0)
        # Make the slider expand so it's fully visible
        self.textRotationSlider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.textRotationSlider.setMinimumWidth(220)
        self.textRotationSlider.setFixedHeight(20)
        self.textRotationSpinBox = QtWidgets.QSpinBox()
        self.textRotationSpinBox.setMinimum(-180)
        self.textRotationSpinBox.setMaximum(180)
        self.textRotationSpinBox.setValue(0)
        self.textRotationSpinBox.setMaximumWidth(70)
        try:
            self.textRotationSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.UpDownArrows)
        except Exception:
            pass
        # Reset button for text rotation
        self.textResetBtn = QtWidgets.QPushButton("↺ Reset")
        self.textResetBtn.setFixedWidth(72)

        # Grid placement:
        # Row 0: Text Size label | size spin | Text Rot label | rot spin | Reset
        self.textPropLayout.addWidget(self.textSizeLabel,       0, 0)
        self.textPropLayout.addWidget(self.textSizeSpinBox,     0, 1)
        self.textPropLayout.addWidget(self.textRotationLabel,   0, 2)
        self.textPropLayout.addWidget(self.textRotationSpinBox, 0, 3)
        self.textPropLayout.addWidget(self.textResetBtn,        0, 4)
        # Row 1: Rotation Slider spanning all columns
        self.textPropLayout.addWidget(self.textRotationSlider,  1, 0, 1, 5)
        # Column stretch to let slider breathe
        self.textPropLayout.setColumnStretch(0, 0)
        self.textPropLayout.setColumnStretch(1, 0)
        self.textPropLayout.setColumnStretch(2, 0)
        self.textPropLayout.setColumnStretch(3, 0)
        self.textPropLayout.setColumnStretch(4, 0)
        
        self.toolsLayout.addLayout(self.toolModeLayout)
        self.toolsLayout.addLayout(self.colorLayout)
        self.toolsLayout.addLayout(self.cursorLayout)
        self.toolsLayout.addLayout(self.textPropLayout)
        
        # View controls group
        self.viewGroup = QtWidgets.QGroupBox("View Controls")
        self.viewLayout = QtWidgets.QVBoxLayout(self.viewGroup)
        
        # Zoom control
        self.zoomLayout = QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QLabel("Zoom:")
        self.zoomBox = QtWidgets.QComboBox()
        # Progressive zoom slider: 50% .. 400% (percent values)
        self.zoomSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.zoomSlider.setMinimum(50)
        self.zoomSlider.setMaximum(400)
        self.zoomSlider.setValue(50)
        self.zoomSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.zoomSlider.setTickInterval(10)
        # Size policies so the slider expands and others stay compact
        self.zoomSlider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.zoomBox.setMaximumWidth(110)
        # Hide presets box since we use progressive slider only
        self.zoomBox.setVisible(False)
        # Live zoom percentage label
        self.zoomPercentLbl = QtWidgets.QLabel("50%")
        self.zoomPercentLbl.setMinimumWidth(52)
        self.zoomPercentLbl.setMaximumWidth(60)
        self.zoomPercentLbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.zoomPercentLbl.setStyleSheet("QLabel { color: #ffffff; font-weight: bold; }")

        self.zoomLayout.addWidget(self.label)
        self.zoomLayout.addWidget(self.zoomBox)
        self.zoomLayout.addWidget(self.zoomSlider)
        self.zoomLayout.addWidget(self.zoomPercentLbl)
        # Stretch so slider takes remaining space, percent label stays compact
        self.zoomLayout.setStretch(0, 0)  # label
        self.zoomLayout.setStretch(1, 0)  # hidden combo
        self.zoomLayout.setStretch(2, 1)  # slider expands
        self.zoomLayout.setStretch(3, 0)  # percent label fixed
        
        # Rotation control (two rows to avoid cramping/overlap)
        self.rotationLabel = QtWidgets.QLabel("Rotation:")
        self.rotationSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.rotationSlider.setMinimum(-180)
        self.rotationSlider.setMaximum(180)
        self.rotationSlider.setValue(0)
        self.rotationSlider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.rotationSpinBox = QtWidgets.QSpinBox()
        self.rotationSpinBox.setMinimum(-180)
        self.rotationSpinBox.setMaximum(180)
        self.rotationSpinBox.setValue(0)
        self.rotationSpinBox.setSuffix("°")
        self.rotationSpinBox.setMaximumWidth(70)
        # Ensure up/down arrows are visible in the spin box
        try:
            self.rotationSpinBox.setButtonSymbols(QtWidgets.QAbstractSpinBox.UpDownArrows)
        except Exception:
            pass
        self.resetRotationBtn = QtWidgets.QPushButton("↺ Reset")
        self.resetRotationBtn.setFixedWidth(72)

        self.rotationGrid = QtWidgets.QGridLayout()
        self.rotationGrid.setHorizontalSpacing(8)
        self.rotationGrid.setVerticalSpacing(6)
        # Row 0: label + spinbox + reset (compact)
        self.rotationGrid.addWidget(self.rotationLabel,   0, 0)
        self.rotationGrid.addWidget(self.rotationSpinBox, 0, 1)
        self.rotationGrid.addWidget(self.resetRotationBtn,0, 2)
        # Row 1: full-width slider
        self.rotationGrid.addWidget(self.rotationSlider,  1, 0, 1, 3)
        # Make the slider column stretch
        self.rotationGrid.setColumnStretch(0, 0)
        self.rotationGrid.setColumnStretch(1, 0)
        self.rotationGrid.setColumnStretch(2, 1)

        self.viewLayout.addLayout(self.zoomLayout)
        self.viewLayout.addLayout(self.rotationGrid)
        
        # Action buttons
        # Use a grid layout here so buttons never overlap and can wrap into two tidy rows
        self.actionGroup = QtWidgets.QGroupBox("Actions")
        self.actionLayout = QtWidgets.QGridLayout(self.actionGroup)
        self.actionLayout.setContentsMargins(8, 8, 8, 8)
        self.actionLayout.setHorizontalSpacing(8)
        self.actionLayout.setVerticalSpacing(6)

        # Create buttons with consistent size policies
        common_btn_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)

        self.clearDimensionsBtn = QtWidgets.QPushButton("🗑️ Clear Dimensions")
        self.clearDimensionsBtn.setStyleSheet("QPushButton { background-color: #ff8c00; }")
        self.clearDimensionsBtn.setSizePolicy(common_btn_policy)
        # Prevent text truncation (ensure the trailing 'n' in 'Dimensions' is visible)
        self.clearDimensionsBtn.setMinimumWidth(180)

        self.saveButton = QtWidgets.QPushButton("💾 Save")
        self.saveButton.setStyleSheet("QPushButton { background-color: #28a745; }")
        self.saveButton.setSizePolicy(common_btn_policy)

        self.closeButton = QtWidgets.QPushButton("❌ Close")
        self.closeButton.setStyleSheet("QPushButton { background-color: #dc3545; }")
        self.closeButton.setSizePolicy(common_btn_policy)

        # Undo/Redo buttons
        self.undoButton = QtWidgets.QPushButton("↶ Undo")
        self.undoButton.setToolTip("Undo (Ctrl+Z)")
        self.undoButton.setSizePolicy(common_btn_policy)
        self.redoButton = QtWidgets.QPushButton("↷ Redo")
        self.redoButton.setToolTip("Redo (Ctrl+Shift+Z)")
        self.redoButton.setSizePolicy(common_btn_policy)

        # Place buttons: Close+Save together, Undo+Redo together, Clear at bottom
        # Row 0: Close | Save
        self.actionLayout.addWidget(self.closeButton,          0, 0)
        self.actionLayout.addWidget(self.saveButton,           0, 1)
        # Row 1: Undo | Redo
        self.actionLayout.addWidget(self.undoButton,           1, 0)
        self.actionLayout.addWidget(self.redoButton,           1, 1)
        # Row 2: Clear Dimensions (span both columns)
        self.actionLayout.addWidget(self.clearDimensionsBtn,   2, 0, 1, 2)
        # Let both columns stretch evenly
        self.actionLayout.setColumnStretch(0, 1)
        self.actionLayout.setColumnStretch(1, 1)
        
        # Add groups to toolbar
        self.toolbarLayout.addWidget(self.fileInfoGroup)
        self.toolbarLayout.addWidget(self.toolsGroup)
        self.toolbarLayout.addWidget(self.viewGroup)
        self.toolbarLayout.addWidget(self.actionGroup)
        # Balance available space so action buttons keep a sensible width and never overlap
        self.toolbarLayout.setStretch(0, 0)  # File info (compact)
        self.toolbarLayout.setStretch(1, 1)  # Tools (flex)
        self.toolbarLayout.setStretch(2, 1)  # View (flex)
        self.toolbarLayout.setStretch(3, 1)  # Actions (give it breathing room)
        
        self.mainLayout.addWidget(self.toolbarFrame)
        
        # Content area with splitter
        self.contentSplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.contentSplitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #555555;
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color: #0078d4;
            }
        """)
        
        # Main graphics view
        self.graphicsView = QtWidgets.QGraphicsView()
        self.graphicsView.setObjectName("graphicsView")
        self.graphicsView.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        
        # Minimap panel
        self.minimapPanel = QtWidgets.QFrame()
        self.minimapPanel.setMaximumWidth(250)
        self.minimapPanel.setMinimumWidth(200)
        self.minimapPanel.setStyleSheet("""
            QFrame {
                background-color: #404040;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        self.minimapLayout = QtWidgets.QVBoxLayout(self.minimapPanel)
        self.minimapTitle = QtWidgets.QLabel("🗺️ Map Overview")
        self.minimapTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.minimapTitle.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        
        self.label_2 = QtWidgets.QLabel()
        self.label_2.setMaximumSize(QtCore.QSize(200, 200))
        self.label_2.setMinimumSize(QtCore.QSize(150, 150))
        self.label_2.setFrameShape(QtWidgets.QFrame.Box)
        self.label_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.label_2.setScaledContents(True)
        self.label_2.setStyleSheet("""
            QLabel {
                border: 2px solid #555555;
                border-radius: 5px;
                background-color: #3c3c3c;
            }
        """)
        
        # Status info
        self.statusInfo = QtWidgets.QLabel("Ready")
        self.statusInfo.setAlignment(QtCore.Qt.AlignCenter)
        self.statusInfo.setStyleSheet("color: #00d4aa; font-weight: bold;")
        
        self.minimapLayout.addWidget(self.minimapTitle)
        self.minimapLayout.addWidget(self.label_2)
        self.minimapLayout.addWidget(self.statusInfo)
        self.minimapLayout.addStretch()
        
        # Add to splitter
        self.contentSplitter.addWidget(self.graphicsView)
        self.contentSplitter.addWidget(self.minimapPanel)
        self.contentSplitter.setSizes([800, 200])
        
        self.mainLayout.addWidget(self.contentSplitter)
        
        MapEditor.setCentralWidget(self.centralwidget)
        
        # Enhanced menu bar
        self.menubar = QtWidgets.QMenuBar(MapEditor)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1200, 25))
        self.menubar.setStyleSheet("""
            QMenuBar {
                background-color: #404040;
                color: #ffffff;
                border-bottom: 1px solid #555555;
            }
            QMenuBar::item {
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #0078d4;
            }
        """)
        
        # File menu
        self.fileMenu = self.menubar.addMenu("File")
        self.viewMenu = self.menubar.addMenu("View")
        self.helpMenu = self.menubar.addMenu("Help")
        
        MapEditor.setMenuBar(self.menubar)
        
        # Enhanced status bar
        self.statusbar = QtWidgets.QStatusBar(MapEditor)
        self.statusbar.setStyleSheet("""
            QStatusBar {
                background-color: #404040;
                color: #ffffff;
                border-top: 1px solid #555555;
            }
        """)
        MapEditor.setStatusBar(self.statusbar)
        
        # Connect slider and spinbox synchronization
        self.cursorSizeSlider.valueChanged.connect(self.cursorSizeSpinBox.setValue)
        self.cursorSizeSpinBox.valueChanged.connect(self.cursorSizeSlider.setValue)
        self.rotationSlider.valueChanged.connect(self.rotationSpinBox.setValue)
        self.rotationSpinBox.valueChanged.connect(self.rotationSlider.setValue)
        
        self.retranslateUi(MapEditor)
        QtCore.QMetaObject.connectSlotsByName(MapEditor)

    def retranslateUi(self, MapEditor):
        _translate = QtCore.QCoreApplication.translate
        MapEditor.setWindowTitle(_translate("MapEditor", "🗺️ ROS Map Editor - Enhanced"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MapEditor = QtWidgets.QMainWindow()
    ui = Ui_MapEditor()
    ui.setupUi(MapEditor)
    MapEditor.show()
    sys.exit(app.exec_())