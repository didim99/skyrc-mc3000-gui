"""
MC3000 BLE Communication Layer

Bluetooth Low Energy communication for SKYRC MC3000 battery charger.
Uses bleak library for cross-platform BLE support.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

try:
    from bleak import BleakClient, BleakScanner
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData
    BLEAK_AVAILABLE = True
except ImportError:
    BleakClient = None
    BleakScanner = None
    BLEDevice = None
    AdvertisementData = None
    BLEAK_AVAILABLE = False

from mc3000_protocol import (
    BLE_SERVICE_UUID,
    BLE_CHARACTERISTIC_UUID,
    BLE_DEVICE_NAMES,
    BLE_PACKET_SIZE,
    cmd_ble_take_mtu,
    cmd_ble_get_version,
    cmd_ble_get_basic_data,
    parse_ble_slot_data,
    parse_ble_version,
    parse_ble_basic_data,
    SlotData,
    BLEVersionInfo,
    BLEBasicData,
)

logger = logging.getLogger(__name__)


class MC3000BLEError(Exception):
    """Exception for MC3000 BLE communication errors."""
    pass


@dataclass
class BLEDeviceInfo:
    """Information about a discovered BLE device."""
    address: str
    name: str
    rssi: int

    def __str__(self) -> str:
        return f"{self.name} ({self.address}) RSSI: {self.rssi} dBm"


class MC3000BLE:
    """
    BLE communication layer for SKYRC MC3000 battery charger.

    This class handles all BLE communication with the charger including
    device discovery, connection management, and data exchange.

    IMPORTANT: All async methods must be called from the same event loop
    where connect_async() was called. For Qt applications, use
    MC3000BLEManager which handles the event loop properly.
    """

    def __init__(self):
        self._client: Optional[Any] = None
        self._connected: bool = False
        self._device_address: Optional[str] = None
        self._response_buffer: bytes = b""
        self._response_event: Optional[asyncio.Event] = None
        self._version_info: Optional[BLEVersionInfo] = None
        self._notification_callback: Optional[Callable[[bytes], None]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._char_properties: List[str] = []

    @staticmethod
    def check_ble_available() -> bool:
        """Check if BLE library is available."""
        return BLEAK_AVAILABLE

    @staticmethod
    async def scan_devices(timeout: float = 5.0) -> List[BLEDeviceInfo]:
        """
        Scan for MC3000 BLE devices.

        Args:
            timeout: Scan timeout in seconds

        Returns:
            List of discovered BLEDeviceInfo objects
        """
        if not BLEAK_AVAILABLE:
            return []

        devices: List[BLEDeviceInfo] = []
        discovered: Dict[str, BLEDeviceInfo] = {}

        def detection_callback(device: BLEDevice, adv_data: AdvertisementData):
            name = adv_data.local_name or device.name or ""
            # Check if device name matches MC3000 patterns
            if any(known_name.lower() in name.lower() for known_name in BLE_DEVICE_NAMES):
                if device.address not in discovered:
                    info = BLEDeviceInfo(
                        address=device.address,
                        name=name,
                        rssi=adv_data.rssi if adv_data.rssi else -100,
                    )
                    discovered[device.address] = info
                    logger.info(f"Found MC3000 BLE device: {info}")

        try:
            scanner = BleakScanner(detection_callback=detection_callback)
            await scanner.start()
            await asyncio.sleep(timeout)
            await scanner.stop()
        except Exception as e:
            logger.error(f"Error scanning for BLE devices: {e}")

        return list(discovered.values())

    def _notification_handler(self, sender: int, data: bytearray):
        """Handle incoming BLE notifications."""
        self._response_buffer = bytes(data)
        logger.debug(f"Received BLE notification: {data.hex()}")
        if self._response_event:
            self._response_event.set()
        if self._notification_callback:
            self._notification_callback(bytes(data))

    async def connect_async(self, device_address: str) -> bool:
        """
        Connect to an MC3000 device via BLE.

        Args:
            device_address: BLE device address to connect to

        Returns:
            True if connection successful
        """
        if not BLEAK_AVAILABLE:
            raise MC3000BLEError("BLE library not available. Install with: pip install bleak")

        if self._connected:
            await self.disconnect_async()

        try:
            self._loop = asyncio.get_event_loop()
            self._client = BleakClient(device_address)
            await self._client.connect()

            if not self._client.is_connected:
                raise MC3000BLEError(f"Failed to connect to {device_address}")

            # Small delay to let the connection stabilize
            await asyncio.sleep(0.5)

            # Log available services and characteristics for debugging
            for service in self._client.services:
                logger.debug(f"Service: {service.uuid}")
                for char in service.characteristics:
                    logger.debug(f"  Characteristic: {char.uuid}, properties: {char.properties}")

            # Find and log the target characteristic properties
            target_char = None
            for service in self._client.services:
                for char in service.characteristics:
                    if char.uuid.lower() == BLE_CHARACTERISTIC_UUID.lower():
                        target_char = char
                        logger.info(f"Target characteristic properties: {char.properties}")
                        break

            # Subscribe to notifications if supported
            if target_char and "notify" in target_char.properties:
                await self._client.start_notify(
                    BLE_CHARACTERISTIC_UUID,
                    self._notification_handler
                )
                logger.info("Subscribed to notifications")
            else:
                logger.warning("Notify not supported on characteristic")

            self._connected = True
            self._device_address = device_address
            self._char_properties = target_char.properties if target_char else []
            logger.info(f"Connected to MC3000 BLE at {device_address}")

            # Small delay before first command
            await asyncio.sleep(0.2)

            # Try to get version info
            try:
                self._version_info = await self._get_version_async()
                if self._version_info:
                    logger.info(f"BLE Firmware version: {self._version_info.firmware_version}")
                else:
                    logger.warning(
                        "Could not get version info - device may not respond to BLE queries. "
                        "Make sure batteries are inserted in the charger."
                    )
            except Exception as e:
                logger.warning(f"Could not read version info: {e}")

            return True

        except Exception as e:
            self._connected = False
            self._client = None
            self._device_address = None
            self._loop = None
            logger.error(f"Failed to connect to MC3000 BLE: {e}")
            raise MC3000BLEError(f"Failed to connect: {e}")

    async def disconnect_async(self) -> None:
        """Disconnect from the MC3000 BLE device."""
        if self._client:
            try:
                if self._client.is_connected:
                    try:
                        await self._client.stop_notify(BLE_CHARACTERISTIC_UUID)
                    except Exception:
                        pass
                    await self._client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")
            finally:
                self._client = None
                self._connected = False
                self._device_address = None
                self._version_info = None
                self._loop = None
                logger.info("Disconnected from MC3000 BLE")

    def is_connected(self) -> bool:
        """Check if currently connected to a device."""
        if not self._connected or self._client is None:
            return False
        try:
            return self._client.is_connected
        except Exception:
            return False

    async def _send_command(self, command: bytes) -> bool:
        """
        Send a command to the device.

        Args:
            command: Command bytes to send (20 bytes for BLE)

        Returns:
            True if command sent successfully
        """
        if not self.is_connected():
            raise MC3000BLEError("Not connected to device")

        try:
            # MC3000 requires write-with-response even though characteristic
            # advertises write-without-response
            logger.debug(f"Sending command: {command.hex()}")

            await self._client.write_gatt_char(
                BLE_CHARACTERISTIC_UUID,
                command,
                response=True  # MC3000 requires write-with-response
            )
            return True
        except Exception as e:
            logger.error(f"Error sending BLE command: {e}")
            raise MC3000BLEError(f"Send failed: {e}")

    def _prepare_for_response(self):
        """Prepare to receive a response. Must be called BEFORE sending command."""
        self._response_event = asyncio.Event()
        self._response_buffer = b""

    async def _wait_for_response(self, timeout: float = 2.0) -> Optional[bytes]:
        """
        Wait for a response notification that was prepared with _prepare_for_response.

        Args:
            timeout: Response timeout in seconds

        Returns:
            Response bytes or None on timeout
        """
        if not self.is_connected():
            raise MC3000BLEError("Not connected to device")

        if self._response_event is None:
            raise MC3000BLEError("Must call _prepare_for_response before _wait_for_response")

        try:
            await asyncio.wait_for(self._response_event.wait(), timeout=timeout)
            response = self._response_buffer
            logger.debug(f"Got response: {response.hex() if response else 'None'}")
            return response
        except asyncio.TimeoutError:
            logger.debug("Response timeout, trying direct read")
            # Fallback: try direct read from characteristic
            try:
                data = await self._client.read_gatt_char(BLE_CHARACTERISTIC_UUID)
                if data and len(data) >= BLE_PACKET_SIZE and data[0] == 0x0F:
                    logger.debug(f"Got response via read: {data.hex()}")
                    return bytes(data)
            except Exception as e:
                logger.debug(f"Read fallback failed: {e}")
            return None
        finally:
            self._response_event = None

    async def _get_version_async(self) -> Optional[BLEVersionInfo]:
        """Query version info from the device."""
        try:
            cmd = cmd_ble_get_version()
            # Prepare for response BEFORE sending command to avoid race condition
            self._prepare_for_response()
            await self._send_command(cmd)
            response = await self._wait_for_response()
            if response:
                return parse_ble_version(response)
        except Exception as e:
            logger.error(f"Error getting version: {e}")
        return None

    async def get_slot_data_async(self, slot: int) -> Optional[SlotData]:
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
            cmd = cmd_ble_take_mtu(slot)
            # Prepare for response BEFORE sending command to avoid race condition
            self._prepare_for_response()
            await self._send_command(cmd)
            response = await self._wait_for_response()
            if response:
                result = parse_ble_slot_data(response, slot)
                if result is None:
                    logger.warning(f"Failed to parse slot {slot} data: {response.hex()}")
                return result
        except Exception as e:
            logger.error(f"Error getting slot {slot} data via BLE: {e}")
        return None

    async def get_basic_data_async(self) -> Optional[BLEBasicData]:
        """
        Query basic system data from the device.

        Returns:
            BLEBasicData object or None on failure
        """
        if not self.is_connected():
            return None

        try:
            cmd = cmd_ble_get_basic_data()
            # Prepare for response BEFORE sending command to avoid race condition
            self._prepare_for_response()
            await self._send_command(cmd)
            response = await self._wait_for_response()
            if response:
                return parse_ble_basic_data(response)
        except Exception as e:
            logger.error(f"Error getting basic data via BLE: {e}")
        return None

    async def start_processing_async(self) -> bool:
        """
        Send start processing command.

        Note: BLE may not support direct start command - check device response.

        Returns:
            True if command sent successfully
        """
        if not self.is_connected():
            return False

        # BLE protocol may not have a direct start command
        logger.warning("Start processing via BLE may not be supported")
        return False

    async def stop_processing_async(self) -> bool:
        """
        Send stop processing command.

        Note: BLE may not support direct stop command - check device response.

        Returns:
            True if command sent successfully
        """
        if not self.is_connected():
            return False

        # BLE protocol may not have a direct stop command
        logger.warning("Stop processing via BLE may not be supported")
        return False

    @property
    def firmware_version(self) -> Optional[str]:
        """Get firmware version string if available."""
        if self._version_info:
            return self._version_info.firmware_version
        return None

    @property
    def firmware_version_int(self) -> int:
        """Get firmware version as integer (e.g., 111 for 1.11)."""
        if self._version_info:
            return self._version_info.firmware_major * 100 + self._version_info.firmware_minor
        return 0


class BLEConnectionManager:
    """
    Manages BLE connection and polling in a dedicated thread with its own event loop.

    This class is designed for use with Qt applications where the main thread
    runs the Qt event loop. All BLE operations run in a background thread
    with a dedicated asyncio event loop.
    """

    def __init__(self):
        self._ble: Optional[MC3000BLE] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running: bool = False
        self._device_address: Optional[str] = None
        self._slot_data_callback: Optional[Callable[[int, SlotData], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None
        self._connected_callback: Optional[Callable[[bool], None]] = None

    def set_callbacks(
        self,
        slot_data: Optional[Callable[[int, SlotData], None]] = None,
        error: Optional[Callable[[str], None]] = None,
        connected: Optional[Callable[[bool], None]] = None,
    ):
        """Set callback functions for events."""
        self._slot_data_callback = slot_data
        self._error_callback = error
        self._connected_callback = connected

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._ble is not None and self._ble.is_connected()

    async def _run_polling_loop(self):
        """Main polling loop that runs in the background thread."""
        try:
            # Connect
            self._ble = MC3000BLE()
            await self._ble.connect_async(self._device_address)

            if self._connected_callback:
                self._connected_callback(True)

            # Polling loop
            while self._running and self._ble.is_connected():
                for slot in range(4):
                    if not self._running:
                        break
                    try:
                        data = await self._ble.get_slot_data_async(slot)
                        if data and self._slot_data_callback:
                            self._slot_data_callback(slot, data)
                    except Exception as e:
                        if self._error_callback:
                            self._error_callback(f"Slot {slot}: {e}")

                # Wait before next poll cycle
                await asyncio.sleep(1.0)

        except Exception as e:
            logger.error(f"BLE polling error: {e}")
            if self._error_callback:
                self._error_callback(str(e))
        finally:
            if self._ble:
                try:
                    await self._ble.disconnect_async()
                except Exception:
                    pass
            if self._connected_callback:
                self._connected_callback(False)

    def start(self, device_address: str):
        """Start the connection and polling in the current thread's event loop."""
        self._device_address = device_address
        self._running = True
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._run_polling_loop())
        finally:
            self._loop.close()
            self._loop = None

    def stop(self):
        """Signal the manager to stop."""
        self._running = False

    def disconnect(self):
        """Disconnect from the device."""
        self._running = False
