# SkyRC MC3000 BLE Protocol (from APK reverse engineering)

Source: decompiled Android app `MC3000.apk` (classes.dex) using jadx. Key files:
- `/tmp/mc3000_jadx/sources/com/skyrc/mc3000/thread/BleThread.java`
- `/tmp/mc3000_jadx/sources/com/skyrc/mc3000/broadcast/actions/Config.java`
- `/tmp/mc3000_jadx/sources/com/skyrc/mc3000/utils/FastBleUtil.java`
- `/tmp/mc3000_jadx/sources/com/skyrc/mc3000/activity/AddActivity.java`
- `/tmp/mc3000_jadx/sources/com/skyrc/mc3000/activity/SettingFragment.java`
- `/tmp/mc3000_jadx/sources/com/skyrc/mc3000/tools/Constant.java`

This document focuses on BLE/GATT commands and payloads used by the Android app.

---

## GATT

- **Service UUID:** `0000FFE0-0000-1000-8000-00805f9b34fb`
- **Characteristic UUID (Notify + Write):** `0000FFE1-0000-1000-8000-00805f9b34fb`

The app enables notifications on the same characteristic it writes to.

### Device name filters (scan)
The app scans for BLE devices with names:
- `SimpleBLEPeripheral`
- `Charger`
- `HitecCharger`

---

## Packet framing

- BLE packet size: **20 bytes** (default ATT MTU)
- **Byte 0:** always `0x0F`
- **Byte 19:** checksum = sum of bytes 0..18, masked to `0xFF`

> Exception: the **40-byte save profile** command is split into two 20-byte writes.

---

## Command summary (byte 1)

| Command | Direction | Meaning |
|---|---|---|
| `0x55` | host→device / device→host | Status request + status response |
| `0x56` | host→device / device→host | Voltage curve request + response |
| `0x57` | host→device / device→host | Version info request + response |
| `0x61` | host→device / device→host | Get basic settings |
| `0x63` | host→device / device→host | Set basic settings / ACK |
| `0x65` | host→device / device→host | Restore factory / ACK |
| `0x66` | host→device / device→host | Restore calibration / ACK |
| `0x05` | host→device | Start charging |
| `0xFE` | host→device | Stop charging |
| `0x11` | host→device / device→host | Save profile / ACK -> triggers start charge in app |

---

## Status request / response (0x55)

### Request (host→device)
```
[0]  0x0F
[1]  0x55
[2]  slot (0..3)
[3..18] zero
[19] checksum
```
The app cycles through slots 0..3 periodically.

### Response (device→host)
Parsed in `BleThread.parseStatus()`.
```
[0]  0x0F
[1]  0x55
[2]  slot (0..3)
[3]  battery type
[4]  mode
[5]  count
[6]  status
[7]  time_hi
[8]  time_lo         => time seconds (BE)
[9]  voltage_hi
[10] voltage_lo      => mV (BE)
[11] current_hi
[12] current_lo      => mA (BE)
[13] capacity_hi
[14] capacity_lo     => mAh (BE)
[15] temperature     => integer in current unit
[16] internal_hi
[17] internal_lo     => internal resistance mΩ (BE)
[18] led status
[19] checksum
```

### Status codes (byte 6)
- `0` standby
- `1` charge
- `2` discharge
- `3` pause
- `4` completed
- `0x80+` errors (see APK mapping in `Config.status()`)

Error codes (from app):
```
0x80 input volt low
0x81 input volt high
0x82 MCP3424-1 Err
0x83 MCP3424-2 Err
0x84 connect break
0x85 check volt
0x86 capacity cut
0x87 time cut
0x88 sys temp high
0x89 batt temp cut
0x8A short circuit
0x8B polarity
```

---

## Voltage curve request / response (0x56)

### Request (host→device)
```
[0] 0x0F
[1] 0x56
[2] slot (0..3)
[3..18] zero
[19] checksum
```

### Response (device→host)
Total length: **245 bytes** (received via multiple notifications, reassembled).
```
[0]  0x0F
[1]  0x56
[2]  slot
[3]  time_hi
[4]  time_lo          => time seconds; app multiplies by 1000
[5]  unused
[6..244] voltage points (120 values):
          value[i] = (buf[i-1] << 8) | buf[i], for i = 6..244 step 2
```

---

## Version info request / response (0x57)

### Request (host→device)
```
[0]  0x0F
[1]  0x57
[2]  0
[3..8] MAC bytes (reverse order)
[9..18] zero
[19] checksum
```
MAC encoding is reversed (AA:BB:CC:DD:EE:FF => FF EE DD CC BB AA).

### Response parsing (device→host)
The app converts the response to a hex string and reads bytes 14..16:
- Firmware version: bytes 14-15 as decimal with 2 digits fraction
- Hardware version: byte 16 scaled

Exact parsing is in `BleThread.analyAvailable()`.

---

## Get/Set basic settings

### Get (0x61)
**Request**: `[0]=0x0F, [1]=0x61, rest zero, checksum`

**Response** fields (from `parseBasicData()`):
```
[2] temp_unit   (0=C, 1=F)
[3] system_beep (0/1)
[4] display
[5] screensaver (0/1)
[6] cooling_fan
[7] input_hi
[8] input_lo    => input voltage mV (BE)
```

### Set (0x63)
Request layout (20 bytes):
```
[0] 0x0F
[1] 0x63
[2] temp_unit
[3] system_beep
[4] display
[5] screensaver
[6] cooling_fan
[7] input_hi
[8] input_lo
[9..18] zero
[19] checksum
```

ACK response: command `0x63` with `[2] == 1` indicates success.

---

## Restore factory / calibration

### Factory reset (0x65)
```
[0] 0x0F
[1] 0x65
[2..18] zero
[19] checksum
```
ACK uses command `0x65` with `[2] == 1` on success.

### Calibration reset (0x66)
```
[0] 0x0F
[1] 0x66
[2..18] zero
[19] checksum
```
ACK uses command `0x66` with `[2] == 1` on success.

---

## Start / Stop charge

### Start (0x05)
```
[0] 0x0F
[1] 0x05
[2] slot (0..3)
[3..18] zero
[19] checksum
```

### Stop (0xFE)
```
[0] 0x0F
[1] 0xFE
[2] slot (0..3)
[3..18] zero
[19] checksum
```

---

## Save profile (0x11) — 40 bytes total

Built in `AddActivity.save()`. Two 20-byte chunks are sent back-to-back.

### Full 40-byte payload
```
[0]  0x0F
[1]  0x11
[2]  slot mask (bit0..bit3)
[3]  battery type
[4]  mode
[5]  capacity_hi
[6]  capacity_lo
[7]  charge_current_hi
[8]  charge_current_lo
[9]  discharge_current_hi
[10] discharge_current_lo
[11] charge_end_voltage_hi
[12] charge_end_voltage_lo
[13] discharge_end_voltage_hi
[14] discharge_end_voltage_lo
[15] charge_end_current_hi
[16] charge_end_current_lo
[17] discharge_end_current_hi
[18] discharge_end_current_lo
[19] charge_rest_time
[20] cycle_count
[21] cycle_mode
[22] negative_voltage_increment (NiMH/NiCd/Eneloop only)
[23] eddy_current (value/10)
[24] storage_voltage_hi
[25] storage_voltage_lo
[26] temp_protect
[27] time_protect_hi
[28] time_protect_lo
[29] discharge_rest_time
[30..38] zero/reserved
[39] checksum (sum of bytes 0..38 & 0xFF)
```

### Send sequence
1) Send bytes 0..19 as first 20-byte packet
2) Send bytes 20..39 as second 20-byte packet

The app then sends `start charge (0x05)` for the slot.

---

## Notes / Differences vs USB protocol

- BLE uses 20-byte packets with 0x0F prefix and checksum at byte 19.
- Status response layout **differs** from USB HID layout (temperature is a single byte here; internal resistance is a 16-bit value at bytes 16–17).
- BLE protocol includes **profile upload** (0x11) and basic settings (0x61/0x63), which were not present in the PC USB monitor app.

---

## Minimal request examples

### Status poll slot 0
```
0F 55 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 64
```
(Checksum 0x64)

### Get basic settings
```
0F 61 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 70
```
(Checksum 0x70)

---

## Next steps

If you want, I can:
- generate a small BLE test client (Python/Node) to send these commands
- add a `ble_capture.md` template for logging raw notifications
- reconcile BLE vs USB protocol differences into a unified spec

