"""
MC3000 USB HID Communication Layer

Cross-platform USB HID communication for SKYRC MC3000 battery charger.
Uses hidapi library for cross-platform support.
"""

import time
import platform
import os
from typing import Optional, List, Any, Tuple
import logging

try:
    import hid
    HID_AVAILABLE = True
except ImportError:
    hid = None
    HID_AVAILABLE = False

from mc3000_protocol import (
    VENDOR_ID,
    PRODUCT_ID,
    DATA_SIZE,
    TIMEOUT_MS,
    cmd_query_slot,
    cmd_take_mtu,
    cmd_get_system_settings,
    cmd_start_processing,
    cmd_stop_processing,
    parse_slot_data,
    parse_system_settings,
    parse_slot_settings,
    SlotData,
    SlotSettings,
    SystemSettings,
)

logger = logging.getLogger(__name__)


def detect_linux_distro() -> Tuple[str, str]:
    """
    Detect Linux distribution.

    Returns:
        Tuple of (distro_id, distro_family) e.g. ('ubuntu', 'debian')
    """
    if platform.system() != 'Linux':
        return ('', '')

    distro_id = ''
    distro_family = ''

    try:
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if line.startswith('ID='):
                    distro_id = line.strip().split('=')[1].strip('"').lower()
                elif line.startswith('ID_LIKE='):
                    distro_family = line.strip().split('=')[1].strip('"').lower()
    except (IOError, OSError):
        pass

    return (distro_id, distro_family)


def get_udev_instructions() -> str:
    """
    Get udev setup instructions for the current Linux distribution.

    Returns:
        Instructions string for setting up udev rules
    """
    distro_id, distro_family = detect_linux_distro()

    udev_rule = '''SUBSYSTEM=="usb", ATTR{idVendor}=="0000", ATTR{idProduct}=="0001", MODE="0666"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0000", ATTRS{idProduct}=="0001", MODE="0666"'''

    # Determine package manager and commands based on distro
    if distro_id in ('ubuntu', 'debian', 'linuxmint', 'pop') or 'debian' in distro_family:
        reload_cmd = "sudo udevadm control --reload-rules && sudo udevadm trigger"
        extra_note = ""
    elif distro_id in ('fedora', 'rhel', 'centos', 'rocky', 'alma') or 'fedora' in distro_family or 'rhel' in distro_family:
        reload_cmd = "sudo udevadm control --reload-rules && sudo udevadm trigger"
        extra_note = "\n# You may also need: sudo dnf install hidapi"
    elif distro_id in ('arch', 'manjaro', 'endeavouros') or 'arch' in distro_family:
        reload_cmd = "sudo udevadm control --reload-rules && sudo udevadm trigger"
        extra_note = "\n# You may also need: sudo pacman -S hidapi"
    elif distro_id in ('opensuse', 'suse') or 'suse' in distro_family:
        reload_cmd = "sudo udevadm control --reload-rules && sudo udevadm trigger"
        extra_note = "\n# You may also need: sudo zypper install hidapi"
    elif distro_id == 'gentoo':
        reload_cmd = "sudo udevadm control --reload-rules && sudo udevadm trigger"
        extra_note = "\n# You may also need: sudo emerge dev-libs/hidapi"
    else:
        reload_cmd = "sudo udevadm control --reload-rules && sudo udevadm trigger"
        extra_note = ""

    instructions = f"""
USB Permission Error - udev rules needed

To access the MC3000 without root privileges, create a udev rule:

1. Create the rules file:
   sudo tee /etc/udev/rules.d/99-mc3000.rules << 'EOF'
{udev_rule}
EOF

2. Reload udev rules:
   {reload_cmd}

3. Reconnect the MC3000 USB cable

4. Try running the application again{extra_note}

Alternatively, you can run with sudo (not recommended for regular use):
   sudo python main.py
"""
    return instructions


class MC3000USBError(Exception):
    """Exception for MC3000 USB communication errors."""
    pass


class MC3000PermissionError(MC3000USBError):
    """Exception for USB permission errors with helpful instructions."""

    def __init__(self, original_error: str):
        self.original_error = original_error
        self.instructions = get_udev_instructions() if platform.system() == 'Linux' else ""
        message = f"{original_error}\n{self.instructions}" if self.instructions else original_error
        super().__init__(message)


class MC3000USB:
    """
    USB HID communication layer for SKYRC MC3000 battery charger.

    This class handles all USB communication with the charger including
    device discovery, connection management, and data exchange.
    """

    def __init__(self):
        self._device: Any = None
        self._connected: bool = False
        self._system_settings: Optional[SystemSettings] = None

    @staticmethod
    def check_hid_available() -> bool:
        """Check if HID library is available."""
        return HID_AVAILABLE

    @staticmethod
    def enumerate_devices() -> List[dict]:
        """
        Enumerate all MC3000 devices connected to the system.

        Returns:
            List of device info dictionaries
        """
        if not MC3000USB.check_hid_available():
            return []

        devices = []
        try:
            all_devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
            for dev in all_devices:
                devices.append({
                    'path': dev.get('path'),
                    'vendor_id': dev.get('vendor_id'),
                    'product_id': dev.get('product_id'),
                    'serial_number': dev.get('serial_number', ''),
                    'manufacturer': dev.get('manufacturer_string', 'SKYRC'),
                    'product': dev.get('product_string', 'MC3000'),
                    'interface': dev.get('interface_number', -1),
                })
        except Exception as e:
            logger.error(f"Error enumerating HID devices: {e}")

        return devices

    def connect(self, device_path: Optional[bytes] = None) -> bool:
        """
        Connect to an MC3000 device.

        Args:
            device_path: Optional specific device path to connect to.
                        If None, connects to the first available device.

        Returns:
            True if connection successful, False otherwise

        Raises:
            MC3000USBError: If HID library not available or connection fails
        """
        if not MC3000USB.check_hid_available():
            raise MC3000USBError("HID library not available. Install with: pip install hid")

        if self._connected:
            self.disconnect()

        try:
            if device_path:
                self._device = hid.Device(path=device_path)
            else:
                # MC3000 uses VID=0x0000 which hid.Device treats as "not specified"
                # So we must enumerate and connect by path
                devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
                if not devices:
                    raise MC3000USBError("No MC3000 device found")
                self._device = hid.Device(path=devices[0]['path'])

            self._connected = True
            logger.info("Connected to MC3000")

            # Try to get system settings on connect
            try:
                self._system_settings = self.get_system_settings()
                if self._system_settings:
                    logger.info(f"Firmware version: {self._system_settings.firmware_version}")
            except Exception as e:
                logger.warning(f"Could not read system settings: {e}")

            return True

        except Exception as e:
            self._connected = False
            self._device = None
            error_str = str(e).lower()
            logger.error(f"Failed to connect to MC3000: {e}")

            # Check for permission-related errors
            if platform.system() == 'Linux' and any(x in error_str for x in [
                'permission', 'access', 'unable to open', 'operation not permitted',
                'could not open', 'cannot open'
            ]):
                raise MC3000PermissionError(f"Failed to connect: {e}")
            raise MC3000USBError(f"Failed to connect: {e}")

    def disconnect(self) -> None:
        """Disconnect from the MC3000 device."""
        if self._device:
            try:
                self._device.close()
            except Exception as e:
                logger.warning(f"Error closing device: {e}")
            finally:
                self._device = None
                self._connected = False
                self._system_settings = None
                logger.info("Disconnected from MC3000")

    def is_connected(self) -> bool:
        """Check if currently connected to a device."""
        return self._connected and self._device is not None

    def _send_command(self, command: bytes) -> bool:
        """
        Send a command to the device.

        Args:
            command: 64-byte command to send

        Returns:
            True if command sent successfully
        """
        if not self.is_connected():
            raise MC3000USBError("Not connected to device")

        try:
            # HID write expects the report ID as first byte (0x00 for default)
            data = bytes([0x00]) + command[:DATA_SIZE]
            bytes_written = self._device.write(data)
            return bytes_written > 0
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            raise MC3000USBError(f"Send failed: {e}")

    def _read_response(self, timeout_ms: int = TIMEOUT_MS) -> Optional[bytes]:
        """
        Read a response from the device.

        Args:
            timeout_ms: Read timeout in milliseconds

        Returns:
            64-byte response data or None on timeout
        """
        if not self.is_connected():
            raise MC3000USBError("Not connected to device")

        try:
            data = self._device.read(DATA_SIZE, timeout=timeout_ms)
            if data:
                return bytes(data)
            return None
        except Exception as e:
            logger.error(f"Error reading response: {e}")
            raise MC3000USBError(f"Read failed: {e}")

    def get_system_settings(self) -> Optional[SystemSettings]:
        """
        Query system settings from the device.

        Returns:
            SystemSettings object or None on failure
        """
        if not self.is_connected():
            return None

        try:
            cmd = cmd_get_system_settings()
            self._send_command(cmd)
            time.sleep(0.01)  # Small delay as in reference implementation

            response = self._read_response()
            if response:
                settings = parse_system_settings(response)
                if settings:
                    self._system_settings = settings
                return settings
        except Exception as e:
            logger.error(f"Error getting system settings: {e}")
        return None

    def get_slot_data(self, slot: int) -> Optional[SlotData]:
        """
        Query real-time data for a specific slot.

        Args:
            slot: Slot number (0-3)

        Returns:
            SlotData object or None on failure
        """
        if not self.is_connected():
            return None

        if slot < 0 or slot > 3:
            raise ValueError("Slot must be 0-3")

        try:
            # Use TakeMtuData command (0x55) for real-time measurements
            # (0x5F QuerySlotData returns slot settings/configuration instead)
            cmd = cmd_take_mtu(slot)
            self._send_command(cmd)
            time.sleep(0.01)  # Small delay as in reference implementation

            response = self._read_response()
            if response:
                return parse_slot_data(response, slot)
        except Exception as e:
            logger.error(f"Error getting slot {slot} data: {e}")
        return None

    def get_all_slots_data(self) -> List[Optional[SlotData]]:
        """
        Query real-time data for all 4 slots.

        Returns:
            List of 4 SlotData objects (or None for failed queries)
        """
        return [self.get_slot_data(slot) for slot in range(4)]

    def start_processing(self) -> bool:
        """
        Send start processing command.

        Returns:
            True if command sent successfully
        """
        if not self.is_connected():
            return False

        try:
            cmd = cmd_start_processing()
            return self._send_command(cmd)
        except Exception as e:
            logger.error(f"Error starting processing: {e}")
            return False

    def stop_processing(self) -> bool:
        """
        Send stop processing command.

        Returns:
            True if command sent successfully
        """
        if not self.is_connected():
            return False

        try:
            cmd = cmd_stop_processing()
            return self._send_command(cmd)
        except Exception as e:
            logger.error(f"Error stopping processing: {e}")
            return False

    def get_slot_settings(self, slot: int) -> Optional[SlotSettings]:
        """
        Query slot settings/configuration for a specific slot.

        Args:
            slot: Slot number (0-3)

        Returns:
            SlotSettings object or None on failure
        """
        if not self.is_connected():
            return None

        if slot < 0 or slot > 3:
            raise ValueError("Slot must be 0-3")

        try:
            # Use QuerySlotData command (0x5F) for settings
            cmd = cmd_query_slot(slot)
            self._send_command(cmd)
            time.sleep(0.02)

            response = self._read_response()
            if response:
                fw_version = self.firmware_version_int or 123
                return parse_slot_settings(response, fw_version)
        except Exception as e:
            logger.error(f"Error getting slot {slot} settings: {e}")
        return None

    def set_slot_config(self, config_data: bytes) -> bool:
        """
        Send slot configuration to the device.

        Args:
            config_data: 64-byte configuration buffer

        Returns:
            True if configuration was accepted by the device
        """
        if not self.is_connected():
            return False

        try:
            self._send_command(config_data)
            time.sleep(0.02)  # Wait for device to process

            response = self._read_response()
            if response and (response[0] & 0xFF) == 0xF0:
                logger.info("Slot configuration applied successfully")
                return True
            else:
                logger.warning(f"Slot config rejected, response: {response[0] if response else 'None'}")
                return False
        except Exception as e:
            logger.error(f"Error setting slot config: {e}")
            return False

    @property
    def firmware_version(self) -> Optional[str]:
        """Get firmware version string if available."""
        if self._system_settings:
            return self._system_settings.firmware_version
        return None

    @property
    def firmware_version_int(self) -> int:
        """Get firmware version as integer (e.g., 111 for 1.11)."""
        if self._system_settings:
            return self._system_settings.firmware_version_int
        return 0

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures disconnection."""
        self.disconnect()
        return False
