#!/usr/bin/env python3
"""
MC3000 Factory Default Backup/Restore Utility

Reads current settings from all 4 slots and saves them as factory defaults.
Can also restore factory defaults to the charger.
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from mc3000_usb import MC3000USB, MC3000USBError, MC3000PermissionError
from mc3000_protocol import BATTERY_TYPES, OPERATION_MODES_LI, OPERATION_MODES_NI, OPERATION_MODES_ZN


def get_backup_dir() -> Path:
    """Get the backup directory, creating it if needed."""
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('APPDATA', Path.home()))
    else:  # Linux/Mac
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))

    backup_dir = base / 'mc3000-gui' / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_factory_default_file() -> Path:
    """Get the factory defaults file path."""
    return get_backup_dir() / 'factory_defaults.json'


def slot_settings_to_dict(settings) -> Dict[str, Any]:
    """Convert SlotSettings to a dictionary."""
    return {
        "slot_number": settings.slot_number,
        "battery_type": settings.battery_type,
        "operation_mode": settings.operation_mode,
        "capacity_mah": settings.capacity_mah,
        "charge_current_ma": settings.charge_current_ma,
        "discharge_current_ma": settings.discharge_current_ma,
        "charge_end_voltage_mv": settings.charge_end_voltage_mv,
        "discharge_cut_voltage_mv": settings.discharge_cut_voltage_mv,
        "charge_end_current_ma": settings.charge_end_current_ma,
        "discharge_reduce_current_ma": settings.discharge_reduce_current_ma,
        "num_cycles": settings.num_cycles,
        "cycle_mode": settings.cycle_mode,
        "charge_resting_min": settings.charge_resting_min,
        "discharge_resting_min": settings.discharge_resting_min,
        "cut_temperature_c": settings.cut_temperature_c,
        "cut_time_min": settings.cut_time_min,
        "peak_sense_mv": settings.peak_sense_mv,
        "trickle_current_ma": settings.trickle_current_ma,
        "restart_voltage_mv": settings.restart_voltage_mv,
    }


def dict_to_config_bytes(slot_data: Dict[str, Any], firmware_version: int = 123) -> bytes:
    """Convert a slot dictionary to config bytes for sending to device."""
    from mc3000_config import SlotConfig

    config = SlotConfig(
        slot_number=slot_data.get("slot_number", 0),
        battery_type=slot_data.get("battery_type", 0),
        operation_mode=slot_data.get("operation_mode", 0),
        capacity_mah=slot_data.get("capacity_mah", 2000),
        charge_current_ma=slot_data.get("charge_current_ma", 1000),
        discharge_current_ma=slot_data.get("discharge_current_ma", 500),
        charge_end_voltage_mv=slot_data.get("charge_end_voltage_mv", 1450),
        discharge_cut_voltage_mv=slot_data.get("discharge_cut_voltage_mv", 900),
        charge_end_current_ma=slot_data.get("charge_end_current_ma", 100),
        discharge_reduce_current_ma=slot_data.get("discharge_reduce_current_ma", 300),
        num_cycles=slot_data.get("num_cycles", 1),
        cycle_mode=slot_data.get("cycle_mode", 0),
        charge_resting_min=slot_data.get("charge_resting_min", 3),
        discharge_resting_min=slot_data.get("discharge_resting_min", 3),
        cut_temperature_c=slot_data.get("cut_temperature_c", 45),
        cut_time_min=slot_data.get("cut_time_min", 120),
        peak_sense_mv=slot_data.get("peak_sense_mv", 5),
        trickle_current_ma=slot_data.get("trickle_current_ma", 50),
        restart_voltage_mv=slot_data.get("restart_voltage_mv", 1000),
    )
    return config.to_bytes(firmware_version)


def get_mode_name(battery_type: int, mode: int) -> str:
    """Get the mode name for a battery type."""
    if battery_type <= 2:
        return OPERATION_MODES_LI.get(mode, f"Mode {mode}")
    elif battery_type in (3, 4, 6):
        return OPERATION_MODES_NI.get(mode, f"Mode {mode}")
    else:
        return OPERATION_MODES_ZN.get(mode, f"Mode {mode}")


def backup_factory_defaults(output_file: Optional[Path] = None) -> bool:
    """
    Read current settings from charger and save as factory defaults.

    Args:
        output_file: Optional custom output file path

    Returns:
        True if backup successful
    """
    if output_file is None:
        output_file = get_factory_default_file()

    print("MC3000 Factory Default Backup Utility")
    print("=" * 40)

    mc3000 = MC3000USB()

    try:
        print("\nConnecting to MC3000...")
        mc3000.connect()
        print(f"Connected! Firmware: {mc3000.firmware_version or 'Unknown'}")

        backup_data = {
            "created": datetime.now().isoformat(),
            "firmware_version": mc3000.firmware_version,
            "firmware_version_int": mc3000.firmware_version_int,
            "slots": {}
        }

        print("\nReading slot settings...")
        for slot in range(4):
            settings = mc3000.get_slot_settings(slot)
            if settings:
                backup_data["slots"][str(slot)] = slot_settings_to_dict(settings)
                battery_name = BATTERY_TYPES.get(settings.battery_type, "Unknown")
                mode_name = get_mode_name(settings.battery_type, settings.operation_mode)
                print(f"  Slot {slot + 1}: {battery_name} - {mode_name}, "
                      f"{settings.capacity_mah}mAh, {settings.charge_current_ma}mA")
            else:
                print(f"  Slot {slot + 1}: Failed to read settings")

        mc3000.disconnect()

        if not backup_data["slots"]:
            print("\nError: No slot settings could be read!")
            return False

        # Save to file
        print(f"\nSaving to: {output_file}")
        with open(output_file, 'w') as f:
            json.dump(backup_data, f, indent=2)

        print("\nFactory defaults saved successfully!")
        return True

    except MC3000PermissionError as e:
        print(f"\nPermission error: {e}")
        return False
    except MC3000USBError as e:
        print(f"\nUSB error: {e}")
        return False
    except Exception as e:
        print(f"\nError: {e}")
        return False
    finally:
        mc3000.disconnect()


def restore_factory_defaults(input_file: Optional[Path] = None) -> bool:
    """
    Restore factory defaults to charger.

    Args:
        input_file: Optional custom input file path

    Returns:
        True if restore successful
    """
    if input_file is None:
        input_file = get_factory_default_file()

    print("MC3000 Factory Default Restore Utility")
    print("=" * 40)

    if not input_file.exists():
        print(f"\nError: Factory defaults file not found: {input_file}")
        print("Please run 'backup' first to save current settings.")
        return False

    # Load backup data
    print(f"\nLoading from: {input_file}")
    try:
        with open(input_file, 'r') as f:
            backup_data = json.load(f)
    except Exception as e:
        print(f"Error loading backup file: {e}")
        return False

    print(f"Backup created: {backup_data.get('created', 'Unknown')}")
    print(f"Firmware version: {backup_data.get('firmware_version', 'Unknown')}")

    slots_data = backup_data.get("slots", {})
    if not slots_data:
        print("Error: No slot data in backup file!")
        return False

    # Show what will be restored
    print("\nSettings to restore:")
    for slot_str, settings in sorted(slots_data.items()):
        slot = int(slot_str)
        battery_name = BATTERY_TYPES.get(settings.get("battery_type", 0), "Unknown")
        mode_name = get_mode_name(settings.get("battery_type", 0), settings.get("operation_mode", 0))
        print(f"  Slot {slot + 1}: {battery_name} - {mode_name}, "
              f"{settings.get('capacity_mah', 0)}mAh, {settings.get('charge_current_ma', 0)}mA")

    # Confirm
    response = input("\nRestore these settings to the charger? [y/N]: ")
    if response.lower() != 'y':
        print("Restore cancelled.")
        return False

    mc3000 = MC3000USB()

    try:
        print("\nConnecting to MC3000...")
        mc3000.connect()
        print(f"Connected! Firmware: {mc3000.firmware_version or 'Unknown'}")

        fw_version = mc3000.firmware_version_int or 123

        print("\nRestoring slot settings...")
        success_count = 0
        for slot_str, settings in sorted(slots_data.items()):
            slot = int(slot_str)
            settings["slot_number"] = slot

            try:
                config_bytes = dict_to_config_bytes(settings, fw_version)
                if mc3000.set_slot_config(config_bytes):
                    print(f"  Slot {slot + 1}: Restored successfully")
                    success_count += 1
                else:
                    print(f"  Slot {slot + 1}: Failed to restore")
            except Exception as e:
                print(f"  Slot {slot + 1}: Error - {e}")

        mc3000.disconnect()

        print(f"\nRestored {success_count}/{len(slots_data)} slots successfully!")
        return success_count > 0

    except MC3000PermissionError as e:
        print(f"\nPermission error: {e}")
        return False
    except MC3000USBError as e:
        print(f"\nUSB error: {e}")
        return False
    except Exception as e:
        print(f"\nError: {e}")
        return False
    finally:
        mc3000.disconnect()


def show_factory_defaults(input_file: Optional[Path] = None) -> bool:
    """
    Display saved factory defaults without restoring.

    Args:
        input_file: Optional custom input file path

    Returns:
        True if file exists and was displayed
    """
    if input_file is None:
        input_file = get_factory_default_file()

    print("MC3000 Saved Factory Defaults")
    print("=" * 40)

    if not input_file.exists():
        print(f"\nNo factory defaults saved yet.")
        print(f"Expected file: {input_file}")
        print("\nRun with 'backup' to save current charger settings.")
        return False

    try:
        with open(input_file, 'r') as f:
            backup_data = json.load(f)
    except Exception as e:
        print(f"Error loading backup file: {e}")
        return False

    print(f"\nFile: {input_file}")
    print(f"Created: {backup_data.get('created', 'Unknown')}")
    print(f"Firmware: {backup_data.get('firmware_version', 'Unknown')}")

    slots_data = backup_data.get("slots", {})
    if not slots_data:
        print("\nNo slot data in backup file.")
        return False

    print("\nSaved slot settings:")
    print("-" * 60)

    for slot_str, settings in sorted(slots_data.items()):
        slot = int(slot_str)
        battery_type = settings.get("battery_type", 0)
        battery_name = BATTERY_TYPES.get(battery_type, "Unknown")
        mode_name = get_mode_name(battery_type, settings.get("operation_mode", 0))

        print(f"\nSlot {slot + 1}:")
        print(f"  Battery Type:      {battery_name}")
        print(f"  Mode:              {mode_name}")
        print(f"  Capacity:          {settings.get('capacity_mah', 0)} mAh")
        print(f"  Charge Current:    {settings.get('charge_current_ma', 0)} mA")
        print(f"  Discharge Current: {settings.get('discharge_current_ma', 0)} mA")
        print(f"  Target Voltage:    {settings.get('charge_end_voltage_mv', 0)} mV")
        print(f"  Cut-off Voltage:   {settings.get('discharge_cut_voltage_mv', 0)} mV")
        print(f"  Cycles:            {settings.get('num_cycles', 1)}")
        print(f"  Cut-off Temp:      {settings.get('cut_temperature_c', 45)} C")
        print(f"  Cut-off Time:      {settings.get('cut_time_min', 0)} min")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="MC3000 Factory Default Backup/Restore Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s backup              Save current charger settings as factory defaults
  %(prog)s restore             Restore factory defaults to charger
  %(prog)s show                Display saved factory defaults
  %(prog)s backup -f my.json   Save to custom file
  %(prog)s restore -f my.json  Restore from custom file
        """
    )

    parser.add_argument(
        'action',
        choices=['backup', 'restore', 'show'],
        help="Action to perform: backup, restore, or show saved defaults"
    )

    parser.add_argument(
        '-f', '--file',
        type=Path,
        help="Custom file path for backup/restore (default: ~/.config/mc3000-gui/backups/factory_defaults.json)"
    )

    args = parser.parse_args()

    if args.action == 'backup':
        success = backup_factory_defaults(args.file)
    elif args.action == 'restore':
        success = restore_factory_defaults(args.file)
    elif args.action == 'show':
        success = show_factory_defaults(args.file)
    else:
        parser.print_help()
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
