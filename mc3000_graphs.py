"""
MC3000 Real-time Graphs

Real-time plotting widgets for monitoring battery charging data.
Uses pyqtgraph for fast, interactive plots.
"""

from collections import deque
from typing import Optional, Dict, List
import time

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QComboBox,
    QLabel,
    QCheckBox,
    QPushButton,
    QGroupBox,
)
from PySide6.QtCore import Qt

import numpy as np
import pyqtgraph as pg

from mc3000_protocol import SlotData

# Configure pyqtgraph
pg.setConfigOptions(antialias=True, background='w', foreground='k')

# Colors for each slot
SLOT_COLORS = [
    (31, 119, 180),   # Blue
    (255, 127, 14),   # Orange
    (44, 160, 44),    # Green
    (214, 39, 40),    # Red
]

# Line styles
VOLTAGE_PEN = {'width': 2}
CURRENT_PEN = {'width': 2, 'style': Qt.DashLine}
CAPACITY_PEN = {'width': 2, 'style': Qt.DotLine}


class SlotDataHistory:
    """Stores historical data for a single slot."""

    def __init__(self, max_points: int = 3600):
        """
        Initialize data history.

        Args:
            max_points: Maximum number of data points to store (default 1 hour at 1Hz)
        """
        self.max_points = max_points
        self.timestamps: deque = deque(maxlen=max_points)
        self.voltage: deque = deque(maxlen=max_points)
        self.current: deque = deque(maxlen=max_points)
        self.capacity: deque = deque(maxlen=max_points)
        self.temperature: deque = deque(maxlen=max_points)
        self.internal_temp: deque = deque(maxlen=max_points)
        self.power: deque = deque(maxlen=max_points)
        self.start_time: Optional[float] = None

    def add_data(self, data: SlotData) -> None:
        """Add a data point from SlotData."""
        now = time.time()
        if self.start_time is None:
            self.start_time = now

        elapsed = now - self.start_time
        self.timestamps.append(elapsed)
        self.voltage.append(data.voltage_v)
        self.current.append(data.current_a)
        self.capacity.append(data.capacity_mah)
        self.temperature.append(data.temperature_c)
        self.internal_temp.append(data.internal_temp_c)
        self.power.append(data.power_w)

    def clear(self) -> None:
        """Clear all stored data."""
        self.timestamps.clear()
        self.voltage.clear()
        self.current.clear()
        self.capacity.clear()
        self.temperature.clear()
        self.internal_temp.clear()
        self.power.clear()
        self.start_time = None

    def get_arrays(self) -> Dict[str, np.ndarray]:
        """Get data as numpy arrays for plotting."""
        return {
            'time': np.array(self.timestamps),
            'voltage': np.array(self.voltage),
            'current': np.array(self.current),
            'capacity': np.array(self.capacity),
            'temperature': np.array(self.temperature),
            'internal_temp': np.array(self.internal_temp),
            'power': np.array(self.power),
        }

    def __len__(self) -> int:
        return len(self.timestamps)


class SlotGraphWidget(QWidget):
    """Graph widget for a single slot with selectable metrics."""

    METRICS = [
        ('voltage', 'Voltage', 'V', (31, 119, 180)),
        ('current', 'Current', 'A', (255, 127, 14)),
        ('capacity', 'Capacity', 'mAh', (44, 160, 44)),
        ('temperature', 'Batt Temp', '°C', (214, 39, 40)),
        ('internal_temp', 'Int Temp', '°C', (148, 103, 189)),
        ('power', 'Power', 'W', (140, 86, 75)),
    ]

    def __init__(self, slot_number: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.slot_number = slot_number
        self.history = SlotDataHistory()
        self.color = SLOT_COLORS[slot_number % len(SLOT_COLORS)]
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Controls row
        controls_layout = QHBoxLayout()

        # Metric checkboxes
        controls_layout.addWidget(QLabel("Show:"))
        self.metric_checkboxes: Dict[str, QCheckBox] = {}

        # Default: show voltage, current, capacity
        default_metrics = ['voltage', 'current', 'capacity']

        for key, name, unit, color in self.METRICS:
            cb = QCheckBox(name)
            cb.setChecked(key in default_metrics)
            cb.setStyleSheet(f"color: rgb({color[0]}, {color[1]}, {color[2]})")
            cb.stateChanged.connect(self._update_plots)
            controls_layout.addWidget(cb)
            self.metric_checkboxes[key] = cb

        controls_layout.addStretch()

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self.clear_data)
        controls_layout.addWidget(clear_btn)

        layout.addLayout(controls_layout)

        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.plot_widget.addLegend(offset=(10, 10))

        # Create curves for each metric
        self.curves: Dict[str, pg.PlotDataItem] = {}
        for key, name, unit, color in self.METRICS:
            curve = self.plot_widget.plot(
                [], [], name=f'{name} ({unit})',
                pen=pg.mkPen(color=color, width=2)
            )
            curve.hide()  # Hide initially
            self.curves[key] = curve

        layout.addWidget(self.plot_widget)

    def _update_plots(self) -> None:
        """Update plot visibility and data."""
        if len(self.history) == 0:
            return

        arrays = self.history.get_arrays()

        for key, name, unit, color in self.METRICS:
            curve = self.curves[key]
            checkbox = self.metric_checkboxes[key]

            if checkbox.isChecked():
                data = arrays[key]
                # Use absolute value for current
                if key == 'current':
                    data = np.abs(data)
                curve.setData(arrays['time'], data)
                curve.show()
            else:
                curve.hide()

    def update_data(self, data: Optional[SlotData]) -> None:
        """Update the graph with new data."""
        if data is None:
            return

        # Only record data if slot is active (not standby)
        if data.status > 0:
            self.history.add_data(data)
            self._update_plots()

    def clear_data(self) -> None:
        """Clear all graph data."""
        self.history.clear()
        for curve in self.curves.values():
            curve.setData([], [])


class MultiSlotGraphWidget(QWidget):
    """Combined graph widget showing all slots or selected metrics."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.histories: List[SlotDataHistory] = [SlotDataHistory() for _ in range(4)]
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Controls
        controls_layout = QHBoxLayout()

        # Metric selector
        controls_layout.addWidget(QLabel("Show:"))
        self.metric_combo = QComboBox()
        self.metric_combo.addItems([
            "Voltage (V)",
            "Current (A)",
            "Capacity (mAh)",
            "Temperature (°C)",
            "Power (W)",
        ])
        self.metric_combo.currentIndexChanged.connect(self._update_plots)
        controls_layout.addWidget(self.metric_combo)

        controls_layout.addSpacing(20)

        # Slot checkboxes
        self.slot_checkboxes: List[QCheckBox] = []
        for i in range(4):
            cb = QCheckBox(f"Slot {i + 1}")
            cb.setChecked(True)
            cb.stateChanged.connect(self._update_plots)
            color = SLOT_COLORS[i]
            cb.setStyleSheet(f"color: rgb({color[0]}, {color[1]}, {color[2]})")
            controls_layout.addWidget(cb)
            self.slot_checkboxes.append(cb)

        controls_layout.addStretch()

        # Clear button
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_all_data)
        controls_layout.addWidget(clear_btn)

        layout.addLayout(controls_layout)

        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.plot_widget.addLegend(offset=(10, 10))

        # Create curves for each slot
        self.curves: List[pg.PlotDataItem] = []
        for i in range(4):
            color = SLOT_COLORS[i]
            curve = self.plot_widget.plot(
                [], [],
                name=f'Slot {i + 1}',
                pen=pg.mkPen(color=color, width=2)
            )
            self.curves.append(curve)

        layout.addWidget(self.plot_widget)

    def _get_metric_data(self, arrays: Dict[str, np.ndarray]) -> np.ndarray:
        """Get the currently selected metric data."""
        metric_idx = self.metric_combo.currentIndex()
        metric_keys = ['voltage', 'current', 'capacity', 'temperature', 'power']
        return arrays[metric_keys[metric_idx]]

    def _get_metric_unit(self) -> str:
        """Get the unit for the currently selected metric."""
        units = ['V', 'A', 'mAh', '°C', 'W']
        return units[self.metric_combo.currentIndex()]

    def _update_plots(self) -> None:
        """Update all plot curves."""
        self.plot_widget.setLabel('left', self.metric_combo.currentText().split('(')[0].strip(),
                                   units=self._get_metric_unit())

        for i, (history, curve, checkbox) in enumerate(
            zip(self.histories, self.curves, self.slot_checkboxes)
        ):
            if checkbox.isChecked() and len(history) > 0:
                arrays = history.get_arrays()
                data = self._get_metric_data(arrays)
                # Use absolute value for current
                if self.metric_combo.currentIndex() == 1:
                    data = np.abs(data)
                curve.setData(arrays['time'], data)
                curve.show()
            else:
                curve.hide()

    def update_data(self, slot: int, data: Optional[SlotData]) -> None:
        """Update data for a specific slot."""
        if data is None or slot < 0 or slot > 3:
            return

        # Only record data if slot is active
        if data.status > 0:
            self.histories[slot].add_data(data)
            self._update_plots()

    def clear_all_data(self) -> None:
        """Clear all graph data."""
        for history in self.histories:
            history.clear()
        for curve in self.curves:
            curve.setData([], [])


class GraphTabWidget(QTabWidget):
    """Tabbed widget containing individual slot graphs and combined view."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Combined view (all slots)
        self.multi_graph = MultiSlotGraphWidget()
        self.addTab(self.multi_graph, "All Slots")

        # Individual slot graphs
        self.slot_graphs: List[SlotGraphWidget] = []
        for i in range(4):
            graph = SlotGraphWidget(i)
            self.slot_graphs.append(graph)
            self.addTab(graph, f"Slot {i + 1}")

    def update_data(self, slot: int, data: Optional[SlotData]) -> None:
        """Update data for a specific slot."""
        if 0 <= slot < 4:
            self.slot_graphs[slot].update_data(data)
            self.multi_graph.update_data(slot, data)

    def clear_all_data(self) -> None:
        """Clear all graph data."""
        for graph in self.slot_graphs:
            graph.clear_data()
        self.multi_graph.clear_all_data()
