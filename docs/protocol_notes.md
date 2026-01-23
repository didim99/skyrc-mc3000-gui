# MC3000 USB Protocol Notes (from goatpr0n.farm)

Source: https://goatpr0n.farm/2019/03/reverse-engineering-of-the-skyrc-mc3000-battery-charger-usb-protocol/

## USB IDs
- Vendor ID: 0
- Product ID: 1

## Packet Layout (as described in the blog, 1-based byte positions)
1. Always 0
2. Start of message (always 0x0f)
3. Calculated value (length/selector in the original app; see command examples)
4. Command opcode
5. Always 0
6. Slot index (0-3)
7. Checksum (sum of bytes 3-6)
8. Always 0xff
9. Always 0xff

Example system settings command bytes shown in the article:
- `0f 03 5a 00 00 5d ff ff`
- Alternate representations shown: `\x0f\x03\x5a\x00` and `\x00\x0f\x03\x5a\x00\x00\x5d\xff\xff`

## Command/Response Op Codes (blog notes)
- `0xf0`: confirmation sent by charger
- `0x5f`: charger data query (slot index in byte 2 of response in the original app)
- `0x5a`: system data query (selection index in byte 3 of response in the original app)
- `0x55`: data payload with checksum validation (sum bytes 1-63 compared to byte 64)

## System Settings / Machine Info Struct
The blog notes a Python struct for unpacking the machine info portion:

```
MACHINE_INFO_STRUCT = '>3xBBBBBBBBBBBBB6sBBhBBBBbB'
MachineInfo = namedtuple('machine_info',
                         ['Sys_Mem1', 'Sys_Mem2', 'Sys_Mem3', 'Sys_Mem4',
                          'Sys_Advance', 'Sys_tUnit', 'Sys_Buzzer_Tone',
                          'Sys_Life_Hide', 'Sys_LiHv_Hide',
                          'Sys_Eneloop_Hide', 'Sys_NiZn_Hide', 'Sys_Lcd_time',
                          'Sys_Min_Input', 'core_type', 'upgrade_type',
                          'is_encrypted', 'customer_id', 'language_id',
                          'software_version_hi', 'software_version_lo',
                          'hardware_version', 'reserved', 'checksum',
                          'software_version', 'machine_id'])
```

The article suggests unpacking the first 32 bytes of the response using this
struct, then appending a `machine_id` to build the final `MachineInfo`.

## Misc Notes
- The original app validates checksums for `0x55` responses by summing bytes
  1-63 and comparing to byte 64.
- The blog shows a slot-current example: `Current = inPacket[11] * 256 + inPacket[12]`.
- Response dispatch in the original app checks `inPacket[1]` for the opcode.

## Known Limitations

### Starting New Operation After "Finished" State
When a slot completes an operation (status = "Finished"), the USB `start_processing`
command (0x05) may not work to start a new operation. The charger appears to require
physical button interaction to clear the "Finished" state before accepting a new
USB start command.

**Workaround:** Press any button on the charger to clear the finished slot, then use
the GUI to apply new settings and start.

### Global Stop Command Reboots Charger
The `stop_processing` command (0xFE) is a global command that stops all slots and
may cause the charger to reboot/reset. There is no known per-slot stop command
via USB. Avoid using the stop command programmatically.

### Start Command is Global
The `start_processing` command (0x05) starts all slots that are in "Standby" state.
There is no per-slot start command - the charger handles slot selection internally
based on which slots have batteries inserted and are configured.
