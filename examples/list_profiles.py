#!/usr/bin/env python3
"""
Example: List available charging profiles.

This script demonstrates how to use the ProfileManager
to list and inspect saved charging profiles.
"""

import sys

sys.path.insert(0, '..')

from mc3000_profiles import ProfileManager
from mc3000_protocol import BATTERY_TYPES


def main():
    pm = ProfileManager()

    profiles = pm.list_profiles()

    if not profiles:
        print("No profiles found.")
        return 0

    print(f"Found {len(profiles)} profiles:\n")

    for name in sorted(profiles):
        profile = pm.get_profile(name)
        if profile:
            battery_name = BATTERY_TYPES.get(profile.get('battery_type', 0), "Unknown")
            builtin = " (built-in)" if pm.is_builtin(name) else ""

            print(f"  {name}{builtin}")
            print(f"    Battery:  {battery_name}")
            print(f"    Capacity: {profile.get('capacity_mah', 0)} mAh")
            print(f"    Charge:   {profile.get('charge_current_ma', 0)} mA")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
