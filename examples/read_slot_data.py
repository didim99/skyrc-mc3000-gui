#!/usr/bin/env python3
"""
Example: Read real-time data from all MC3000 slots.

This script demonstrates how to connect to the MC3000 charger
and read real-time measurements from all 4 slots.
"""

import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, '..')

from mc3000_usb import MC3000USB
from mc3000_protocol import BATTERY_TYPES, STATUS_CODES


def main():
    usb = MC3000USB()

    print("Connecting to MC3000...")
    if not usb.connect():
        print("Failed to connect. Is the charger plugged in?")
        return 1

    print(f"Connected! Firmware: {usb.firmware_version}\n")

    try:
        for slot in range(4):
            data = usb.get_slot_data(slot)
            if data:
                print(f"=== Slot {slot + 1} ===")
                print(f"  Battery:     {data.battery_type_name}")
                print(f"  Mode:        {data.operation_mode_name}")
                print(f"  Status:      {data.status_name}")
                print(f"  Time:        {data.work_time_formatted}")
                print(f"  Voltage:     {data.voltage_v:.3f} V")
                print(f"  Current:     {data.current_ma} mA")
                print(f"  Capacity:    {data.capacity_mah} mAh")
                print(f"  Batt Temp:   {data.temperature_c:.1f} C")
                print(f"  Int Temp:    {data.internal_temp_c:.1f} C")
                print(f"  Power:       {data.power_w:.2f} W")
                print()
            else:
                print(f"=== Slot {slot + 1} ===")
                print("  No data available")
                print()
    finally:
        usb.disconnect()
        print("Disconnected.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
