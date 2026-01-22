#!/usr/bin/env python3
"""Debug script to show raw data from MC3000."""

from mc3000_usb import MC3000USB
from mc3000_protocol import cmd_query_slot, cmd_take_mtu, cmd_get_system_settings
import time

def main():
    usb = MC3000USB()
    print("Connecting to MC3000...")
    usb.connect()
    print("Connected!")

    # Get system settings
    print("\n=== System Settings ===")
    cmd = cmd_get_system_settings()
    print(f"Command: {cmd[:8].hex()}")
    usb._send_command(cmd)
    time.sleep(0.02)
    response = usb._read_response()
    if response:
        print(f"Response ({len(response)} bytes): {response.hex()}")
        print(f"First 32 bytes as list: {list(response[:32])}")

    # Query each slot with TakeMtuData (0x55) for real-time data
    for slot in range(4):
        print(f"\n=== Slot {slot} (Real-time MTU data) ===")
        cmd = cmd_take_mtu(slot)
        print(f"Command: {cmd[:8].hex()}")
        usb._send_command(cmd)
        time.sleep(0.02)
        response = usb._read_response()
        if response:
            print(f"Response ({len(response)} bytes): {response.hex()}")
            print(f"First 32 bytes as list: {list(response[:32])}")
            print(f"  Byte 1 (slot?):      {response[1]}")
            print(f"  Byte 2 (batt type):  {response[2]}")
            print(f"  Byte 3 (op mode):    {response[3]}")
            print(f"  Byte 4 (cycle#):     {response[4]}")
            print(f"  Byte 5 (status):     {response[5]}")
            print(f"  Bytes 8-9 (voltage): {response[8]}, {response[9]} -> {(response[8] << 8) | response[9]} mV = {((response[8] << 8) | response[9])/1000:.3f} V")
            print(f"  Bytes 10-11 (current): {response[10]}, {response[11]} -> {(response[10] << 8) | response[11]} mA")
            print(f"  Bytes 12-13 (capacity): {response[12]}, {response[13]} -> {(response[12] << 8) | response[13]} mAh")
            print(f"  Bytes 14-15 (temp):  {response[14]}, {response[15]} -> {(response[14] << 8) | response[15]} (0.1C) = {((response[14] << 8) | response[15])/10:.1f} C")
            print(f"  Bytes 16-17 (resist): {response[16]}, {response[17]} -> {(response[16] << 8) | response[17]} mOhm")
            print(f"  Bytes 20-21 (energy): {response[20]}, {response[21]} -> {(response[20] << 8) | response[21]} mWh")
            print(f"  Bytes 22-23 (power): {response[22]}, {response[23]} -> {(response[22] << 8) | response[23]} mW")
        else:
            print("No response!")

    usb.disconnect()
    print("\nDone!")

if __name__ == "__main__":
    main()
