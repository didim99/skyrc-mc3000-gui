#!/usr/bin/env python3
"""
Example: Continuously monitor charging progress.

This script demonstrates how to monitor a slot in real-time,
printing updates every second until charging completes.
"""

import sys
import time

sys.path.insert(0, '..')

from mc3000_usb import MC3000USB


def main():
    if len(sys.argv) < 2:
        print("Usage: python monitor_charging.py <slot>")
        print("  slot: 1-4")
        return 1

    slot = int(sys.argv[1]) - 1
    if slot < 0 or slot > 3:
        print("Error: slot must be 1-4")
        return 1

    usb = MC3000USB()

    print("Connecting to MC3000...")
    if not usb.connect():
        print("Failed to connect. Is the charger plugged in?")
        return 1

    print(f"Monitoring Slot {slot + 1}... (Ctrl+C to stop)\n")

    try:
        while True:
            data = usb.get_slot_data(slot)
            if data:
                print(f"\r{data.status_name:12} | "
                      f"{data.voltage_v:6.3f}V | "
                      f"{data.current_ma:5}mA | "
                      f"{data.capacity_mah:5}mAh | "
                      f"{data.temperature_c:5.1f}C | "
                      f"{data.power_mw:5}mW", end="", flush=True)

                # Stop if finished
                if data.status == 4:  # Finished
                    print("\n\nCharging complete!")
                    break

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    finally:
        usb.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
