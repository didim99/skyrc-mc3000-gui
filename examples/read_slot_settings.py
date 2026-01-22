#!/usr/bin/env python3
"""
Example: Read slot configuration/settings from MC3000.

This script demonstrates how to read the programmed settings
for each slot (battery type, currents, voltages, etc).
"""

import sys

sys.path.insert(0, '..')

from mc3000_usb import MC3000USB
from mc3000_protocol import BATTERY_TYPES, CYCLE_MODES


def main():
    usb = MC3000USB()

    print("Connecting to MC3000...")
    if not usb.connect():
        print("Failed to connect. Is the charger plugged in?")
        return 1

    print(f"Connected! Firmware: {usb.firmware_version}\n")

    try:
        for slot in range(4):
            settings = usb.get_slot_settings(slot)
            if settings:
                battery_name = BATTERY_TYPES.get(settings.battery_type, "Unknown")
                cycle_mode = CYCLE_MODES.get(settings.cycle_mode, "Unknown")

                print(f"=== Slot {slot + 1} Settings ===")
                print(f"  Battery Type:      {battery_name}")
                print(f"  Capacity:          {settings.capacity_mah} mAh")
                print(f"  Charge Current:    {settings.charge_current_ma} mA")
                print(f"  Discharge Current: {settings.discharge_current_ma} mA")
                print(f"  End Voltage:       {settings.charge_end_voltage_mv} mV")
                print(f"  Cut-off Voltage:   {settings.discharge_cut_voltage_mv} mV")
                print(f"  End Current:       {settings.charge_end_current_ma} mA")
                print(f"  Cycles:            {settings.num_cycles}")
                print(f"  Cycle Mode:        {cycle_mode}")
                print(f"  Rest Time:         {settings.charge_resting_min} min")
                print(f"  Cut-off Temp:      {settings.cut_temperature_c} C")
                print(f"  Cut-off Time:      {settings.cut_time_min} min")
                print()
            else:
                print(f"=== Slot {slot + 1} ===")
                print("  Failed to read settings")
                print()
    finally:
        usb.disconnect()
        print("Disconnected.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
