"""
MC3000 GUI Components

PySide6-based graphical user interface for SKYRC MC3000 battery charger.
Provides real-time monitoring of all 4 charging slots.
"""

__version__ = "1.5.0"

import sys
import logging
from typing import Optional, List

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGroupBox,
    QMessageBox,
    QProgressBar,
    QStatusBar,
    QSplitter,
    QCheckBox,
    QDialog,
    QFormLayout,
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QPalette, QColor

from mc3000_usb import MC3000USB, MC3000USBError, MC3000PermissionError
from mc3000_protocol import SlotData, STATUS_CODES

# Try to import graph module (optional dependency)
try:
    from mc3000_graphs import GraphTabWidget
    GRAPHS_AVAILABLE = True
except ImportError:
    GRAPHS_AVAILABLE = False
    GraphTabWidget = None

# Try to import config module
try:
    from mc3000_config import SlotConfigDialog
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    SlotConfigDialog = None

logger = logging.getLogger(__name__)

# Color scheme for status
STATUS_COLORS = {
    0: "#808080",  # Standby - Gray
    1: "#00AA00",  # Charging - Green
    2: "#FF6600",  # Discharging - Orange
    3: "#0066FF",  # Resting - Blue
    4: "#00CCCC",  # Finished - Cyan
}
ERROR_COLOR = "#FF0000"  # Red for errors


class SlotWidget(QGroupBox):
    """Widget displaying data for a single charger slot."""

    def __init__(self, slot_number: int, parent: Optional[QWidget] = None):
        super().__init__(f"Slot {slot_number + 1}", parent)
        self.slot_number = slot_number
        self._setup_ui()
        self.clear_data()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # Status indicator
        self.status_frame = QFrame()
        self.status_frame.setFixedHeight(6)
        self.status_frame.setStyleSheet(f"background-color: {STATUS_COLORS[0]};")
        layout.addWidget(self.status_frame)

        # Battery type and mode
        info_layout = QHBoxLayout()
        self.battery_label = QLabel("---")
        self.battery_label.setAlignment(Qt.AlignLeft)
        self.mode_label = QLabel("---")
        self.mode_label.setAlignment(Qt.AlignRight)
        info_layout.addWidget(self.battery_label)
        info_layout.addWidget(self.mode_label)
        layout.addLayout(info_layout)

        # Status label
        self.status_label = QLabel("Standby")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont()
        status_font.setBold(True)
        status_font.setPointSize(11)
        self.status_label.setFont(status_font)
        layout.addWidget(self.status_label)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Measurements grid
        measurements_layout = QGridLayout()
        measurements_layout.setSpacing(2)

        # Create measurement labels
        self.voltage_label = self._create_value_label()
        self.current_label = self._create_value_label()
        self.capacity_label = self._create_value_label()
        self.temperature_label = self._create_value_label()
        self.resistance_label = self._create_value_label()
        self.power_label = self._create_value_label()
        self.energy_label = self._create_value_label()

        row = 0
        measurements_layout.addWidget(QLabel("Voltage:"), row, 0)
        measurements_layout.addWidget(self.voltage_label, row, 1)

        row += 1
        measurements_layout.addWidget(QLabel("Current:"), row, 0)
        measurements_layout.addWidget(self.current_label, row, 1)

        row += 1
        measurements_layout.addWidget(QLabel("Capacity:"), row, 0)
        measurements_layout.addWidget(self.capacity_label, row, 1)

        row += 1
        measurements_layout.addWidget(QLabel("Temp:"), row, 0)
        measurements_layout.addWidget(self.temperature_label, row, 1)

        row += 1
        measurements_layout.addWidget(QLabel("Resistance:"), row, 0)
        measurements_layout.addWidget(self.resistance_label, row, 1)

        row += 1
        measurements_layout.addWidget(QLabel("Power:"), row, 0)
        measurements_layout.addWidget(self.power_label, row, 1)

        row += 1
        measurements_layout.addWidget(QLabel("Energy:"), row, 0)
        measurements_layout.addWidget(self.energy_label, row, 1)

        layout.addLayout(measurements_layout)

        # Cycle info
        self.cycle_label = QLabel("")
        self.cycle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.cycle_label)

        layout.addStretch()

        # Set minimum size
        self.setMinimumWidth(180)
        self.setMinimumHeight(280)

    def _create_value_label(self) -> QLabel:
        """Create a styled value label."""
        label = QLabel("---")
        label.setAlignment(Qt.AlignRight)
        font = QFont("Monospace")
        font.setStyleHint(QFont.Monospace)
        label.setFont(font)
        return label

    def update_data(self, data: Optional[SlotData]):
        """Update the widget with new slot data."""
        if data is None:
            self.clear_data()
            return

        # Update battery type and mode
        self.battery_label.setText(data.battery_type_name)
        self.mode_label.setText(data.operation_mode_name)

        # Update status
        self.status_label.setText(data.status_name)

        # Update status color
        if data.is_error:
            color = ERROR_COLOR
        else:
            color = STATUS_COLORS.get(data.status, STATUS_COLORS[0])
        self.status_frame.setStyleSheet(f"background-color: {color};")
        self.status_label.setStyleSheet(f"color: {color};")

        # Update measurements
        self.voltage_label.setText(f"{data.voltage_v:.3f} V")
        self.current_label.setText(f"{data.current_a:+.3f} A")
        self.capacity_label.setText(f"{data.capacity_mah} mAh")
        self.temperature_label.setText(f"{data.temperature_c:.1f} \u00b0C")
        if data.resistance_mohm == 0xFFFF:
            self.resistance_label.setText("--- m\u03a9")
        else:
            self.resistance_label.setText(f"{data.resistance_mohm} m\u03a9")
        self.power_label.setText(f"{data.power_w:.2f} W")
        self.energy_label.setText(f"{data.energy_mwh} mWh")

        # Update cycle info if in cycle mode
        if data.cycle_number > 0:
            self.cycle_label.setText(f"Cycle {data.cycle_number}")
        else:
            self.cycle_label.setText("")

    def clear_data(self):
        """Clear all displayed data."""
        self.battery_label.setText("---")
        self.mode_label.setText("---")
        self.status_label.setText("Standby")
        self.status_label.setStyleSheet(f"color: {STATUS_COLORS[0]};")
        self.status_frame.setStyleSheet(f"background-color: {STATUS_COLORS[0]};")

        self.voltage_label.setText("--- V")
        self.current_label.setText("--- A")
        self.capacity_label.setText("--- mAh")
        self.temperature_label.setText("--- \u00b0C")
        self.resistance_label.setText("--- m\u03a9")
        self.power_label.setText("--- W")
        self.energy_label.setText("--- mWh")
        self.cycle_label.setText("")


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.mc3000 = MC3000USB()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_device)

        self._setup_ui()
        if self._check_hid_available():
            self._auto_connect()

    def _setup_ui(self):
        """Set up the main window UI."""
        self.setWindowTitle(f"SKYRC MC3000 Battery Charger v{__version__}")
        self.setMinimumSize(900, 800)
        self.resize(1100, 950)  # Default size

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header with controls
        header_layout = QHBoxLayout()

        # Configure button
        if CONFIG_AVAILABLE:
            self.config_btn = QPushButton("Configure...")
            self.config_btn.clicked.connect(self._on_config_clicked)
            self.config_btn.setEnabled(False)
            self.config_btn.setFixedWidth(100)
            header_layout.addWidget(self.config_btn)

        self.system_settings_btn = QPushButton("System Settings...")
        self.system_settings_btn.clicked.connect(self._on_system_settings_clicked)
        self.system_settings_btn.setEnabled(False)
        self.system_settings_btn.setFixedWidth(140)
        header_layout.addWidget(self.system_settings_btn)

        header_layout.addStretch()

        # Show/hide graphs checkbox
        if GRAPHS_AVAILABLE:
            self.show_graphs_cb = QCheckBox("Show Graphs")
            self.show_graphs_cb.setChecked(True)
            self.show_graphs_cb.stateChanged.connect(self._toggle_graphs)
            header_layout.addWidget(self.show_graphs_cb)
            header_layout.addSpacing(20)

        # Connection status indicator
        self.connection_indicator = QLabel("\u25cf")
        self.connection_indicator.setStyleSheet("color: #FF0000; font-size: 16px;")
        header_layout.addWidget(self.connection_indicator)

        self.connection_status = QLabel("Disconnected")
        header_layout.addWidget(self.connection_status)

        main_layout.addLayout(header_layout)

        # System temperature
        self.firmware_label = QLabel("")
        main_layout.addWidget(self.firmware_label)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Create splitter for slots and graphs
        self.splitter = QSplitter(Qt.Vertical)

        # Slots container
        slots_widget = QWidget()
        slots_layout = QHBoxLayout(slots_widget)
        slots_layout.setSpacing(10)
        slots_layout.setContentsMargins(0, 0, 0, 0)

        self.slot_widgets: List[SlotWidget] = []
        for i in range(4):
            slot_widget = SlotWidget(i)
            self.slot_widgets.append(slot_widget)
            slots_layout.addWidget(slot_widget)

        self.splitter.addWidget(slots_widget)

        # Graph widget (if available)
        self.graph_widget = None
        if GRAPHS_AVAILABLE:
            self.graph_widget = GraphTabWidget()
            self.graph_widget.setMinimumHeight(200)
            self.splitter.addWidget(self.graph_widget)
            # Set initial splitter sizes (slots:graphs = 2:3)
            self.splitter.setStretchFactor(0, 2)
            self.splitter.setStretchFactor(1, 3)

        main_layout.addWidget(self.splitter, 1)  # stretch factor 1 to fill space

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _toggle_graphs(self, state):
        """Show or hide the graphs panel."""
        if self.graph_widget:
            self.graph_widget.setVisible(state == Qt.Checked)

    def _on_config_clicked(self):
        """Open the slot configuration dialog."""
        if CONFIG_AVAILABLE and self.mc3000.is_connected():
            dialog = SlotConfigDialog(self.mc3000, self)
            dialog.exec()

    def _on_system_settings_clicked(self):
        """Open the system settings dialog."""
        if self.mc3000.is_connected():
            dialog = SystemSettingsDialog(self.mc3000, self)
            dialog.exec()

    def _check_hid_available(self) -> bool:
        """Check if HID library is available and show warning if not."""
        if not MC3000USB.check_hid_available():
            QMessageBox.warning(
                self,
                "HID Library Not Found",
                "The 'hid' library is not installed.\n\n"
                "Please install it with:\n"
                "pip install hid\n\n"
                "On Linux, you may also need to install libhidapi:\n"
                "sudo apt install libhidapi-hidraw0\n\n"
                "The application will run but cannot connect to devices."
            )
            self.status_bar.showMessage("Error: HID library not available")
            return False
        return True

    def _auto_connect(self):
        """Connect to the device on startup."""
        self._on_connect_clicked()

    def _on_connect_clicked(self):
        """Handle connect button click."""
        self.status_bar.showMessage("Connecting...")

        try:
            # Check for available devices first
            devices = MC3000USB.enumerate_devices()
            if not devices:
                raise MC3000USBError(
                    "No MC3000 device found.\n\n"
                    "Make sure the device is connected via USB.\n"
                    "On Linux, you may need to set up udev rules for USB HID access."
                )

            self.mc3000.connect()

            # Update UI for connected state
            self.connection_indicator.setStyleSheet("color: #00AA00; font-size: 16px;")
            self.connection_status.setText("Connected")
            if CONFIG_AVAILABLE and hasattr(self, 'config_btn'):
                self.config_btn.setEnabled(True)
            if hasattr(self, 'system_settings_btn'):
                self.system_settings_btn.setEnabled(True)

            self.firmware_label.setText("")

            # Start polling
            self.poll_timer.start(1000)  # Poll every 1 second
            self.status_bar.showMessage("Connected - Monitoring active")

            # Do initial poll
            self._poll_device()

        except MC3000PermissionError as e:
            # Show detailed permission error with instructions
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("USB Permission Error")
            msg.setText("Cannot access the MC3000 device due to insufficient permissions.")
            msg.setDetailedText(str(e))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            self.status_bar.showMessage("Permission denied - see instructions")
        except MC3000USBError as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.status_bar.showMessage("Connection failed")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unexpected error: {e}")
            self.status_bar.showMessage("Connection failed")

    def _on_disconnect_clicked(self):
        """Handle disconnect button click."""
        self._disconnect()

    def _disconnect(self):
        """Disconnect from device and update UI."""
        self.poll_timer.stop()
        self.mc3000.disconnect()

        # Update UI for disconnected state
        self.connection_indicator.setStyleSheet("color: #FF0000; font-size: 16px;")
        self.connection_status.setText("Disconnected")
        if CONFIG_AVAILABLE and hasattr(self, 'config_btn'):
            self.config_btn.setEnabled(False)
        if hasattr(self, 'system_settings_btn'):
            self.system_settings_btn.setEnabled(False)
        self.firmware_label.setText("")

        # Clear slot displays
        for slot_widget in self.slot_widgets:
            slot_widget.clear_data()

        # Note: Don't clear graph data on disconnect - user may want to review it

        self.status_bar.showMessage("Disconnected")

    def _poll_device(self):
        """Poll device for updated slot data."""
        if not self.mc3000.is_connected():
            return

        try:
            # Query all slots
            system_temp_c = None
            for i, slot_widget in enumerate(self.slot_widgets):
                data = self.mc3000.get_slot_data(i)
                slot_widget.update_data(data)
                if data and system_temp_c is None:
                    system_temp_c = data.system_temp_c

                # Update graphs if available
                if self.graph_widget and data:
                    self.graph_widget.update_data(i, data)
            if system_temp_c is not None:
                self.firmware_label.setText(f"System Temp: {system_temp_c:.1f} \u00b0C")
            else:
                self.firmware_label.setText("")

        except MC3000USBError as e:
            logger.error(f"Poll error: {e}")
            self.status_bar.showMessage(f"Communication error: {e}")
            # Try to recover on next poll, but don't disconnect immediately
        except Exception as e:
            logger.error(f"Unexpected poll error: {e}")
            self.status_bar.showMessage(f"Error: {e}")

    def closeEvent(self, event):
        """Handle window close event."""
        self.poll_timer.stop()
        if self.mc3000.is_connected():
            self.mc3000.disconnect()
        event.accept()


class SystemSettingsDialog(QDialog):
    """Dialog to display system settings."""

    def __init__(self, mc3000: MC3000USB, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.mc3000 = mc3000
        self._setup_ui()
        self._refresh_settings()

    def _setup_ui(self):
        self.setWindowTitle("System Settings")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.firmware_label = QLabel("---")
        self.hardware_label = QLabel("---")
        self.temp_unit_label = QLabel("---")
        self.beep_label = QLabel("---")
        self.lcd_label = QLabel("---")
        self.ui_mode_label = QLabel("---")
        self.current_slot_label = QLabel("---")
        self.slot_programs_label = QLabel("---")
        self.min_voltage_label = QLabel("---")

        form_layout.addRow("Firmware:", self.firmware_label)
        form_layout.addRow("Hardware:", self.hardware_label)
        form_layout.addRow("Temperature Unit:", self.temp_unit_label)
        form_layout.addRow("Beep Tone:", self.beep_label)
        form_layout.addRow("LCD Off Time:", self.lcd_label)
        form_layout.addRow("UI Mode:", self.ui_mode_label)
        form_layout.addRow("Current Slot:", self.current_slot_label)
        form_layout.addRow("Slot Programs:", self.slot_programs_label)
        form_layout.addRow("Min Voltage:", self.min_voltage_label)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_settings)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def _set_label_text(self, label: QLabel, value: str):
        label.setText(value if value else "---")

    def _refresh_settings(self):
        if not self.mc3000.is_connected():
            QMessageBox.warning(self, "Not Connected", "Connect to the MC3000 to read system settings.")
            return

        settings = self.mc3000.get_system_settings()
        if not settings:
            QMessageBox.warning(self, "Read Failed", "Could not read system settings from the device.")
            return

        lcd_modes = {
            0: "Off",
            1: "Auto",
            2: "1 minute",
            3: "3 minutes",
            4: "5 minutes",
            5: "Always on",
        }
        beep_modes = {
            0: "Off",
            1: "On",
        }

        self._set_label_text(self.firmware_label, settings.firmware_version)
        self._set_label_text(self.hardware_label, str(settings.hardware_version))
        self._set_label_text(
            self.temp_unit_label,
            "Celsius (\u00b0C)" if settings.temperature_unit == 0 else "Fahrenheit (\u00b0F)",
        )
        self._set_label_text(
            self.beep_label,
            beep_modes.get(settings.beep_tone, f"Unknown ({settings.beep_tone})"),
        )
        self._set_label_text(
            self.lcd_label,
            lcd_modes.get(settings.lcd_off_time, f"Unknown ({settings.lcd_off_time})"),
        )
        self._set_label_text(self.ui_mode_label, str(settings.user_interface_mode))
        self._set_label_text(self.current_slot_label, str(settings.current_slot_number + 1))
        slot_programs = ", ".join(str(p) for p in settings.slot_programs)
        self._set_label_text(self.slot_programs_label, slot_programs)
        self._set_label_text(self.min_voltage_label, str(settings.min_voltage))


def create_udev_rules_message() -> str:
    """Return instructions for setting up udev rules on Linux."""
    return """
To access the MC3000 without root privileges on Linux, create a udev rule:

1. Create file /etc/udev/rules.d/99-mc3000.rules with content:
   SUBSYSTEM=="usb", ATTR{idVendor}=="0000", ATTR{idProduct}=="0001", MODE="0666"
   SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0000", ATTRS{idProduct}=="0001", MODE="0666"

2. Reload udev rules:
   sudo udevadm control --reload-rules
   sudo udevadm trigger

3. Reconnect the MC3000 device
"""


def run_gui():
    """Run the GUI application."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for consistent cross-platform look

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run_gui())
