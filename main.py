#!/usr/bin/env python3
"""
SKYRC MC3000 Battery Charger GUI

Cross-platform GUI application for monitoring the SKYRC MC3000 battery charger.
Displays real-time data for all 4 charging slots including voltage, current,
capacity, temperature, resistance, power, and energy.

Usage:
    python main.py

Requirements:
    - PySide6 (Qt for Python)
    - hid (hidapi Python binding)

On Linux, you may need to set up udev rules for USB HID access without root:
    See mc3000_gui.create_udev_rules_message() for instructions.
"""

import sys


def main():
    """Main entry point."""
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)

    # Import and run GUI
    try:
        from mc3000_gui import run_gui
        sys.exit(run_gui())
    except ImportError as e:
        print(f"Error: Missing required module - {e}")
        print("\nPlease install dependencies with:")
        print("    pip install PySide6 hid")
        print("\nOn Linux, you may also need:")
        print("    sudo apt install libhidapi-hidraw0")
        sys.exit(1)


if __name__ == "__main__":
    main()
