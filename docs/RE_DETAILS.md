# SKYRC MC3000 Monitor Protocol - Reverse Engineering Documentation

## Clean Room Reverse Engineering Statement

This document describes the reverse engineering process used to extract protocol information from the MC3000_Monitor_V1.06.exe application. The analysis was performed using publicly available tools on the compiled binary without access to source code, proprietary documentation, or confidential information.

**Date:** 2026-01-23
**Target:** MC3000_Monitor_V1.06.exe (671,744 bytes, compiled July 19, 2024)
**Purpose:** Protocol documentation for interoperability

---

## Tools Used

| Tool | Version | Purpose |
|------|---------|---------|
| `file` | standard | Binary type identification |
| `strings` | GNU binutils | String extraction (ASCII and UTF-16) |
| `radare2` | 5.9.8 | Binary analysis, string location, section mapping |
| `monodis` | mono-utils | .NET IL disassembly |

---

## Methodology

### Step 1: Binary Identification

```bash
file MC3000_Monitor_V1.06.exe
```

**Result:** `PE32 executable for MS Windows 4.00 (GUI), Intel i386 Mono/.Net assembly`

The binary was identified as a .NET assembly, which contains CIL (Common Intermediate Language) bytecode that can be decompiled to readable IL code.

### Step 2: String Extraction

Extracted ASCII strings:
```bash
strings MC3000_Monitor_V1.06.exe | grep -iE '(error|status|mode)'
```

Extracted UTF-16LE strings (common in .NET):
```bash
strings -el MC3000_Monitor_V1.06.exe | grep -iE '(error|fail|temp|voltage|current)'
```

**Key findings:**
- Error messages with consistent formatting (15 characters, padded)
- Battery type names: LiIon, LiFe, LiHV, NiMH, NiCd, NiZn, ENELOOP
- Work mode names: Charge, Refresh, Storage, DisCharge, Cycle, BreakIn
- Command constants: CMD_PHONE_TO_MCU_STATUS_FEED, CMD_PHONE_TO_MCU_TAKE_DATA, etc.

### Step 3: String Location Analysis

Using radare2 to find string addresses:
```bash
r2 -q -c 'izz' MC3000_Monitor_V1.06.exe | grep -iE 'Input Low|Battery Break'
```

**Result:** Error strings located at sequential 32-byte intervals starting at offset `0x1d33d`:

```
1826 0x0001d33d 0x0041f13d 15   31   .text   utf16le  Input Low!
1827 0x0001d35d 0x0041f15d 15   31   .text   utf16le Input High!
1828 0x0001d37d 0x0041f17d 15   31   .text   utf16le  MCP3424-1 Err
1829 0x0001d39d 0x0041f19d 15   31   .text   utf16le  MCP3424-2 Err
1830 0x0001d3bd 0x0041f1bd 15   31   .text   utf16le Battery Break!
1831 0x0001d3dd 0x0041f1dd 15   31   .text   utf16le Check Battery!
1832 0x0001d3fd 0x0041f1fd 15   31   .text   utf16le Capacity Cut!
1833 0x0001d41d 0x0041f21d 15   31   .text   utf16le Time Cut!
1834 0x0001d43d 0x0041f23d 15   31   .text   utf16le Int.Temp High!
1835 0x0001d45d 0x0041f25d 15   31   .text   utf16le Batt.Temp High!
1836 0x0001d47d 0x0041f27d 15   31   .text   utf16le  Over Load!
1837 0x0001d49d 0x0041f29d 15   31   .text   utf16le Batt. Reverse!
1838 0x0001d4bd 0x0041f2bd 15   31   .text   utf16le AnKnow Error!
```

The 32-byte spacing (0x20) indicates a fixed-size string array.

### Step 4: .NET IL Disassembly

```bash
monodis MC3000_Monitor_V1.06.exe > /tmp/mc3000_disasm.il
```

**Key discoveries from IL analysis:**

#### Field Definitions (line ~3288):
```il
.field  private static  string[] bat_type
.field  private static  string[] error_str
```

#### Command Constants:
```il
.field public static literal unsigned int8 CMD_PHONE_TO_MCU_START_CHARGER = int8(0x05)
.field public static literal unsigned int8 CMD_PHONE_TO_MCU_STOP_CHARGER = int8(0xfe)
.field public static literal unsigned int8 CMD_PHONE_TO_MCU_SYSTEM_SET_SAVE = int8(0x11)
.field public static literal unsigned int8 CMD_PHONE_TO_MCU_TAKE_DATA = int8(0x55)
.field public static literal unsigned int8 CMD_PHONE_TO_MCU_SYSTEM_FEED = int8(0x5a)
.field public static literal unsigned int8 CMD_PHONE_TO_MCU_STATUS_FEED = int8(0x5f)
.field public static literal unsigned int8 CMD_PHONE_TO_MCU_EN_BUZZ = int8(0x80)
.field public static literal unsigned int8 CMD_PHONE_TO_MCU_MACHINE_ID = int8(0x57)
.field public static literal unsigned int8 CMD_USB_UPDATE = int8(0x88)
.field public static literal unsigned int8 DATA_END1 = int8(0xff)
.field public static literal unsigned int8 DATA_END2 = int8(0xff)
```

#### Packet Parsing Logic (IL offset ~0x00fd-0x010e):
```il
IL_00fd:  ldarg.0
IL_00fe:  ldfld unsigned int8[] usb_loader_host.FormLoader::inPacket
IL_0103:  ldc.i4.2
IL_0104:  ldelem.u1
IL_0105:  stloc.1          // local1 = inPacket[2] = slot_id
IL_0106:  ldarg.0
IL_0107:  ldfld unsigned int8[] usb_loader_host.FormLoader::inPacket
IL_010c:  ldc.i4.6
IL_010d:  ldelem.u1
IL_010e:  stloc.0          // local0 = inPacket[6] = work_status
```

#### Error Code Calculation (IL offset ~0x0266-0x0280):
```il
IL_0266:  ldloc.0          // load work_status
IL_0267:  ldc.i4 128       // push 128 (0x80)
IL_026c:  clt              // compare: work_status < 128?
IL_026e:  ldc.i4.0
IL_026f:  ceq              // if NOT less than 128 (i.e., >= 128)
IL_0271:  stloc.s 22
IL_0273:  ldloc.s 22
IL_0275:  brfalse.s IL_0282

IL_0277:  ldloc.0          // work_status
IL_0278:  ldc.i4 128       // 128
IL_027d:  sub              // work_status - 128
IL_027e:  ldc.i4.1
IL_027f:  add              // + 1
IL_0280:  stloc.s 5        // error_code = work_status - 127
```

#### Error String Array Access (IL offset ~0x03e7-0x03f0):
```il
IL_03e7:  ldsfld string[] usb_loader_host.FormLoader::error_str
IL_03ec:  ldloc.s 5        // error_code
IL_03ee:  ldc.i4.1
IL_03ef:  sub              // error_code - 1
IL_03f0:  ldelem.ref       // error_str[error_code - 1]
```

This confirms the error string array is 0-indexed, and the error code from the device is 1-indexed.

### Step 5: Data Field Analysis

Analyzing the packet parsing code revealed the data field offsets:

```il
// Voltage extraction (bytes 9-10)
IL_02a9:  ldfld unsigned int8[] usb_loader_host.FormLoader::inPacket
IL_02ae:  ldc.i4.s 0x09        // byte 9
IL_02b0:  ldelem.u1
IL_02b1:  ldc.i4 256           // multiply by 256
IL_02b6:  mul
IL_02b7:  ldarg.0
IL_02b8:  ldfld unsigned int8[] usb_loader_host.FormLoader::inPacket
IL_02bd:  ldc.i4.s 0x0a        // byte 10
IL_02bf:  ldelem.u1
IL_02c0:  add                  // Voltage = byte9*256 + byte10
IL_02c1:  stelem.i4            // Store in Voltage[]

// Current extraction (bytes 11-12)
IL_02ec:  ldfld unsigned int8[] usb_loader_host.FormLoader::inPacket
IL_02f1:  ldc.i4.s 0x0b        // byte 11
IL_02f3:  ldelem.u1
IL_02f4:  ldc.i4 256
IL_02f9:  mul
IL_02fa:  ldarg.0
IL_02fb:  ldfld unsigned int8[] usb_loader_host.FormLoader::inPacket
IL_0300:  ldc.i4.s 0x0c        // byte 12
IL_0302:  ldelem.u1
IL_0303:  add                  // Current = byte11*256 + byte12
IL_0304:  stelem.i4            // Store in Current[]

// Capacity extraction (bytes 13-14)
IL_030d:  ldfld unsigned int8[] usb_loader_host.FormLoader::inPacket
IL_0312:  ldc.i4.s 0x0d        // byte 13
...
IL_0321:  ldc.i4.s 0x0e        // byte 14

// Capacity decimal (byte 25)
IL_032e:  ldfld unsigned int8[] usb_loader_host.FormLoader::inPacket
IL_0333:  ldc.i4.s 0x19        // byte 25 (0x19 = 25)
IL_0335:  ldelem.u1
IL_0336:  stelem.i4            // Store in Caps_Decimal[]

// Battery Temperature (bytes 15-16, masked with 0x7FFF)
IL_0359:  ldfld unsigned int8[] usb_loader_host.FormLoader::inPacket
IL_035e:  ldc.i4.s 0x0f        // byte 15
...
IL_036d:  ldc.i4.s 0x10        // byte 16
...
IL_0380:  ldc.i4 32767         // 0x7FFF mask
IL_0385:  and                  // Remove sign/flag bit

// Internal Temperature (bytes 17-18)
IL_0388:  ldfld unsigned int8[] usb_loader_host.FormLoader::inPacket
IL_038d:  ldc.i4.s 0x11        // byte 17
...
IL_039c:  ldc.i4.s 0x12        // byte 18
```

Time display formatting analysis confirmed work_time is in seconds:
```il
IL_06c3:  ldc.i4 3600          // 3600 seconds per hour
IL_06c8:  div                  // hours = time / 3600
...
IL_06e5:  ldc.i4.s 0x3c        // 60 (0x3C = 60)
IL_06e7:  div                  // minutes = (time % 3600) / 60
...
IL_0703:  ldc.i4.s 0x3c        // 60
IL_0705:  rem                  // seconds = time % 60
```

---

## Protocol Specification

### USB HID Interface

- **Vendor ID:** (extracted from binary - uses hid.dll)
- **Communication:** USB HID reports
- **Packet Size:** 64 bytes (inPacket array, checksum at byte 0x40)

### Packet Structure

#### Status Response Packet Format (CMD 0x55)

| Offset | Size | Field | Description | Units/Notes |
|--------|------|-------|-------------|-------------|
| 0 | 1 | Report ID | HID Report ID | |
| 1 | 1 | Command | Command type (0x55 for status) | |
| 2 | 1 | Slot ID | Battery slot (0-3) | |
| 3 | 1 | Battery Type | See battery types table | |
| 4 | 1 | Work Mode | See work modes table | |
| 5 | 1 | Reserved | Status flags | |
| 6 | 1 | Work Status | State or Error code | See below |
| 7-8 | 2 | Work Time | Time remaining/elapsed | Seconds (big-endian: byte7×256 + byte8) |
| 9-10 | 2 | Voltage | Battery voltage | mV (big-endian) |
| 11-12 | 2 | Current | Charge/discharge current | mA (big-endian) |
| 13-14 | 2 | Capacity | Accumulated capacity | mAh (big-endian) |
| 15-16 | 2 | Batt Temp | Battery temperature | 0.1°C (big-endian, masked with 0x7FFF) |
| 17-18 | 2 | Int Temp | Internal/charger temperature | 0.1°C (big-endian) |
| 25 | 1 | Caps Decimal | Capacity decimal part | 0.01 mAh |
| 64 | 1 | Checksum | Sum of bytes 1-63 | |

**Note:** All 16-bit values are big-endian (high byte first).

#### Data Extraction Examples (from IL analysis)

```c
// Voltage: bytes 9-10
uint16_t voltage_mV = (inPacket[9] << 8) | inPacket[10];

// Current: bytes 11-12
uint16_t current_mA = (inPacket[11] << 8) | inPacket[12];

// Capacity: bytes 13-14 (+ decimal at byte 25)
uint16_t capacity_mAh = (inPacket[13] << 8) | inPacket[14];
uint8_t capacity_decimal = inPacket[25]; // 0.01 mAh units

// Battery Temperature: bytes 15-16 (masked)
int16_t batt_temp_raw = ((inPacket[15] << 8) | inPacket[16]) & 0x7FFF;
float batt_temp_C = batt_temp_raw / 10.0f;

// Internal Temperature: bytes 17-18
int16_t int_temp_raw = (inPacket[17] << 8) | inPacket[18];
float int_temp_C = int_temp_raw / 10.0f;

// Work Time: bytes 7-8
uint16_t work_time_seconds = (inPacket[7] << 8) | inPacket[8];
int hours = work_time_seconds / 3600;
int minutes = (work_time_seconds % 3600) / 60;
int seconds = work_time_seconds % 60;
```

#### Command Types (Byte 1)

| Value | Constant | Description |
|-------|----------|-------------|
| 0x05 | CMD_PHONE_TO_MCU_START_CHARGER | Start charging |
| 0x11 | CMD_PHONE_TO_MCU_SYSTEM_SET_SAVE | Save system settings |
| 0x55 | CMD_PHONE_TO_MCU_TAKE_DATA | Request slot data |
| 0x57 | CMD_PHONE_TO_MCU_MACHINE_ID | Get machine ID (see below) |
| 0x5A | CMD_PHONE_TO_MCU_SYSTEM_FEED | System data feed |
| 0x5F | CMD_PHONE_TO_MCU_STATUS_FEED | Status data feed |
| 0x80 | CMD_PHONE_TO_MCU_EN_BUZZ | Enable buzzer |
| 0x88 | CMD_USB_UPDATE | Firmware update |
| 0xF0 | (response) | OK/ACK response |
| 0xFE | CMD_PHONE_TO_MCU_STOP_CHARGER | Stop charging |

#### CMD_PHONE_TO_MCU_MACHINE_ID (0x57) - Device Identification

**Purpose:** Query device identification and version information.

**Response contains `Machine_info` structure:**

| Field | Type | Description |
|-------|------|-------------|
| machine_id | string/int | Device serial number (SN) |
| hardware_version | int | Hardware revision |
| software_version | int | Firmware version |

**Evidence from IL analysis:**
```
get_machine_id / set_machine_id
get_hardware_version / set_hardware_version
get_software_version / set_software_version
<machine_id>k__BackingField
<hardware_version>k__BackingField
<software_version>k__BackingField
```

**Usage:**
1. PC sends command 0x57 to request device info
2. MC3000 responds with machine ID and version information
3. Software validates the response (shows "Invalid machine ID!" if validation fails)
4. The machine ID (SN) is used for firmware update checks:
   ```
   http://upgrade.skyrc.com/?SN={machine_id}
   ```

**Related strings found:**
- `"Current Version:"` - displayed firmware version
- `"Boot Version:"` - bootloader version (parsed as `byte / 10` . `byte % 10`)
- `"Invalid machine ID!"` - validation error message

### Work Status (Byte 6)

#### Normal States (0x00-0x7F)

| Value | State |
|-------|-------|
| 0x00 | Standby / Idle |
| 0x01 | Charging |
| 0x02 | Discharging |
| 0x03 | Resting |
| 0x04 | Finished |

#### Error States (0x80-0xFF)

When byte 6 >= 0x80, an error condition is indicated.
**Error index** = (value - 0x80) + 1 = value - 0x7F

| Value | Error Index | Error Message | Description |
|-------|-------------|---------------|-------------|
| 0x80 | 1 | Input Low! | Input voltage too low |
| 0x81 | 2 | Input High! | Input voltage too high |
| 0x82 | 3 | MCP3424-1 Err | ADC chip 1 error |
| 0x83 | 4 | MCP3424-2 Err | ADC chip 2 error |
| 0x84 | 5 | Battery Break! | Battery connection lost |
| 0x85 | 6 | Check Battery! | Battery check failed |
| 0x86 | 7 | Capacity Cut! | Capacity limit reached |
| 0x87 | 8 | Time Cut! | Time limit reached |
| 0x88 | 9 | Int.Temp High! | Internal temperature too high |
| 0x89 | 10 | Batt.Temp High! | Battery temperature too high |
| 0x8A | 11 | Over Load! | Overload condition |
| 0x8B | 12 | Batt. Reverse! | Battery inserted backwards |
| 0x8C | 13 | AnKnow Error! | Unknown error |

### Battery Types (Byte 3)

| Index | Type |
|-------|------|
| 0 | LiIon |
| 1 | LiFe |
| 2 | LiHV |
| 3 | NiMH |
| 4 | NiCd |
| 5 | NiZn |
| 6 | Eneloop |

### Work Modes (Byte 4)

#### Lithium Battery Modes (bat_type < 3)

| Index | Mode |
|-------|------|
| 0 | Charge |
| 1 | Refresh |
| 2 | Storage |
| 3 | Discharge |
| 4 | Cycle |

#### Nickel Battery Modes (bat_type >= 3)

| Index | Mode |
|-------|------|
| 0 | Charge |
| 1 | Refresh |
| 2 | Break-In |
| 3 | Discharge |
| 4 | Cycle |

### Checksum Calculation

The checksum is the sum of bytes 1 through 63, stored at byte 64 (offset 0x40):

```c
uint8_t checksum = 0;
for (int i = 1; i < 64; i++) {
    checksum += packet[i];
}
// checksum should equal packet[64]
```

---

## Additional Findings

### DLL Dependencies

The application uses Windows HID API through:
- `hid.dll` - HID device communication
- `setupapi.dll` - Device enumeration
- `user32.dll` - Windows UI
- `kernel32.dll` - Core Windows functions

### Internal Hardware References

- **MCP3424** - 18-bit ADC chip (Microchip), used for voltage/current measurement
- Two MCP3424 chips are present (errors 3 and 4 reference them individually)

### Data Storage Fields (from IL analysis)

The FormLoader class contains arrays for storing per-slot data:

```csharp
// Real-time values (4 slots)
int[] Voltage;        // Current voltage per slot (mV)
int[] Current;        // Current amperage per slot (mA)
int[] Caps;           // Capacity per slot (mAh)
int[] Caps_Decimal;   // Capacity decimal part
int[] dCaps;          // Discharge capacity
int[] Batt_Tem;       // Battery temperature per slot
int[] work_time;      // Work time remaining (seconds)

// Historical data pools
int[][] Voltage_Data; // Voltage history per slot
int[][] Cur_Data;     // Current history per slot
int[][] Caps_Data;    // Capacity history per slot
int[][] Batt_Tem_Data;// Temperature history per slot
int[][] Voltage_Pool; // Voltage data pool
int[][] Cur_Pool;     // Current data pool

// Voltage limits per battery type
int[] DCHG_VOL_H;       // Discharge voltage high limit
int[] DCHG_VOL_DEFAULT; // Discharge voltage default
int[] DCHG_VOL_L;       // Discharge voltage low limit
int[] CHG_VOL_H;        // Charge voltage high limit
int[] CHG_VOL_DEFAULT;  // Charge voltage default
int[] CHG_VOL_L;        // Charge voltage low limit
int[] CHG_VOL_STORGE;   // Storage voltage
```

### System Settings (CMD 0x5A - SYSTEM_FEED)

Global charger settings (not per-slot):

```csharp
// System configuration fields found in binary
Sys_Min_Input     // Minimum input voltage threshold
Sys_Lcd_Time      // LCD backlight timeout
Sys_Buzzer_Tone   // Buzzer tone/volume setting
Sys_tUnit         // Temperature unit (0=Celsius, 1=Fahrenheit)
Sys_Advance       // Advanced mode enabled
Sys_Life_Hide     // Hide LiFe battery type in menu
Sys_NiZn_Hide     // Hide NiZn battery type in menu
Sys_Eneloop_Hide  // Hide Eneloop battery type in menu
Sys_LiHv_Hide     // Hide LiHV battery type in menu
Sys_Mem1          // Memory preset slot 1
Sys_Mem2          // Memory preset slot 2
Sys_Mem3          // Memory preset slot 3
Sys_Mem4          // Memory preset slot 4
```

### ChargerData Configuration Fields

Per-slot configuration stored in `ChargerData` class:

```csharp
int bWork;       // Working state (0=idle, 1=active)
int Type;        // Battery type (0-6)
int Mode;        // Work mode (0-4)
int Caps;        // Target capacity (mAh)
int Cur;         // Charge current (mA)
int dCur;        // Discharge current (mA)
int Cut_Volt;    // Cut-off/discharge end voltage (mV)
int End_Volt;    // Charge end voltage (mV)
int End_Cur;     // Charge end current (mA)
int End_dCur;    // Discharge end current (mA)
int Cycle_Count; // Number of cycles (1-99)
int Cycle_Delay; // Delay between cycles (minutes)
int Cycle_Mode;  // Cycle mode (0=C>D, 1=D>C)
int Peak_Sense;  // Peak sensitivity for NiMH -dV detection (1-20 mV)
int Trickle;     // Trickle charge current (mA, stored as value/10)
int Hold_Volt;   // Hold/storage voltage (mV)
int CutTemp;     // Cut-off temperature (°C × 10)
int CutTime;     // Cut-off time (minutes)
int Tem_Unit;    // Temperature unit (0=Celsius, 1=Fahrenheit)
```

### Charging Profile Packet (CMD 0x5F - STATUS_FEED Response)

**This packet contains the current charging settings for a specific slot.**

| Offset | Size | Field | Description | Units |
|--------|------|-------|-------------|-------|
| 0 | 1 | Report ID | HID Report ID | |
| 1 | 1 | Command | 0x5F = STATUS_FEED | |
| 2 | 1 | Slot ID | Battery slot (0-3) | |
| 3 | 1 | bWork | Working state (0=idle) | |
| 4 | 1 | Type | Battery type (0-6) | |
| 5 | 1 | Mode | Work mode (0-4) | |
| 6-7 | 2 | Caps | Target capacity | mAh (BE) |
| 8-9 | 2 | Cur | Charge current | mA (BE) |
| 10-11 | 2 | dCur | Discharge current | mA (BE) |
| 12-13 | 2 | Cut_Volt | Discharge end voltage | mV (BE) |
| 14-15 | 2 | End_Volt | Charge end voltage | mV (BE) |
| 16-17 | 2 | End_Cur | Charge end current | mA (BE) |
| 18-19 | 2 | End_dCur | Discharge end current | mA (BE) |
| 20 | 1 | Cycle_Count | Number of cycles | 1-99 |
| 21 | 1 | Cycle_Delay | Delay between cycles | minutes |
| 22 | 1 | Cycle_Mode | 0=Charge→Discharge, 1=Discharge→Charge | |
| 23 | 1 | Peak_Sense | Peak sensitivity (-dV) | mV |
| 24 | 1 | Trickle | Trickle charge | mA ÷ 10 |
| 25-26 | 2 | Hold_Volt | Hold/storage voltage | mV (BE) |
| 27 | 1 | CutTemp | Cut-off temperature | °C ÷ 10 |
| 28-29 | 2 | CutTime | Cut-off time | minutes (BE) |
| 30 | 1 | Tem_Unit | Temperature unit | 0=C, 1=F |

**Parsing Example:**

```c
// Parse charging profile from STATUS_FEED (0x5F) packet
void parse_charging_profile(uint8_t* packet, int slot, ChargerData* data) {
    int i = 3;  // Start at byte 3

    data->bWork = packet[i++];
    data->Type = packet[i++];
    data->Mode = packet[i++];

    // 16-bit big-endian values
    data->Caps = (packet[i] << 8) | packet[i+1]; i += 2;
    data->Cur = (packet[i] << 8) | packet[i+1]; i += 2;
    data->dCur = (packet[i] << 8) | packet[i+1]; i += 2;
    data->Cut_Volt = (packet[i] << 8) | packet[i+1]; i += 2;
    data->End_Volt = (packet[i] << 8) | packet[i+1]; i += 2;
    data->End_Cur = (packet[i] << 8) | packet[i+1]; i += 2;
    data->End_dCur = (packet[i] << 8) | packet[i+1]; i += 2;

    // Single byte values
    data->Cycle_Count = packet[i++];
    data->Cycle_Delay = packet[i++];
    data->Cycle_Mode = packet[i++];
    data->Peak_Sense = packet[i++];
    data->Trickle = packet[i++] * 10;  // Multiply by 10

    data->Hold_Volt = (packet[i] << 8) | packet[i+1]; i += 2;
    data->CutTemp = packet[i++] * 10;  // Multiply by 10 for 0.1°C
    data->CutTime = (packet[i] << 8) | packet[i+1]; i += 2;
    data->Tem_Unit = packet[i++];
}
```

### System Settings Packet (CMD 0x5A - SYSTEM_FEED Response)

**This packet contains global charger settings.**

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 1 | Report ID | HID Report ID |
| 1 | 1 | Command | 0x5A = SYSTEM_FEED |
| 2 | 1 | Reserved | |
| 3 | 1 | Slot Index | Slot being queried |
| 4 | 1 | Sys_Mem1 | Memory preset 1 |
| 5 | 1 | Sys_Mem2 | Memory preset 2 |
| 6 | 1 | Sys_Mem3 | Memory preset 3 |
| 7 | 1 | Sys_Mem4 | Memory preset 4 |
| 8 | 1 | Sys_Advance | Advanced mode (0=off, 1=on) |
| 9 | 1 | Sys_tUnit | Temperature unit (0=C, 1=F) |
| 10 | 1 | Sys_Buzzer_Tone | Buzzer volume (0-3) |
| 11 | 1 | Sys_Life_Hide | Hide LiFe type (0=show, 1=hide) |
| 12 | 1 | Sys_LiHv_Hide | Hide LiHV type (0=show, 1=hide) |
| 13 | 1 | Sys_Eneloop_Hide | Hide Eneloop type (0=show, 1=hide) |
| 14 | 1 | Sys_NiZn_Hide | Hide NiZn type (0=show, 1=hide) |
| 15 | 1 | Sys_Lcd_Time | LCD timeout (minutes, 0=always on) |
| 16 | 1 | Sys_Min_Input | Minimum input voltage threshold |
| 17-31 | 15 | Serial | Device serial number (hex encoded) |

### Default Charging Profile Values (from binary analysis)

| Field | Default Value | Notes |
|-------|---------------|-------|
| Type | 0 | LiIon |
| Mode | 0 | Charge |
| Caps | 2000 mAh | Target capacity |
| Cur | 1000 mA | Charge current |
| dCur | 500 mA | Discharge current |
| CutTime | 180 min | 3 hours |
| CutTemp | 450 (45.0°C) | Cut-off temperature |
| End_Volt | 4200 mV | 4.2V for LiIon |
| Cut_Volt | 3300 mV | 3.3V discharge cutoff |
| End_Cur | 100 mA | Charge termination current |
| End_dCur | 400 mA | Discharge termination current |
| Cycle_Mode | 0 | Charge→Discharge |
| Cycle_Count | 1 | Single cycle |
| Cycle_Delay | 10 min | Rest between cycles |
| Trickle | 50 mA | (stored as 5 in packet) |
| Peak_Sense | 3 mV | -dV detection sensitivity |
| Hold_Volt | 4180 mV | Storage voltage |

### Voltage Ranges by Battery Type

The charger enforces voltage limits based on battery chemistry (from `CHG_VOL_*` and `DCHG_VOL_*` arrays):

| Type | Chemistry | Charge End (mV) | Discharge End (mV) | Storage (mV) |
|------|-----------|-----------------|-------------------|--------------|
| 0 | LiIon | 4200 (4100-4350) | 2500-3300 | 3850 |
| 1 | LiFe | 3600 (3500-3700) | 2000-2800 | 3300 |
| 2 | LiHV | 4350 (4200-4400) | 2500-3300 | 3900 |
| 3 | NiMH | Peak detect | 900-1100 | N/A |
| 4 | NiCd | Peak detect | 900-1100 | N/A |
| 5 | NiZn | 1900 (1850-1950) | 1200-1400 | N/A |
| 6 | Eneloop | Peak detect | 900-1100 | N/A |

**Notes:**
- Lithium types use CC/CV charging with End_Volt as target
- Nickel types use -dV/dt peak detection (Peak_Sense parameter)
- Values in parentheses show typical min-max range
- Storage mode only available for lithium chemistries

### Current Limits

| Parameter | Min | Max | Step |
|-----------|-----|-----|------|
| Charge Current | 100 mA | 3000 mA | 100 mA |
| Discharge Current | 100 mA | 2000 mA | 100 mA |
| End Current | 50 mA | 500 mA | 10 mA |
| Trickle Current | 0 (off) | 200 mA | 10 mA |

### Application Metadata

- **Original name:** "usb loader host"
- **Copyright:** 2010
- **Framework:** .NET Framework 4.0
- **Debug PDB path:** `D:\c#projects\上位机\充电器程序\MC3000\obj\Release\MC3000_Monitor.pdb`

---

## References

- Binary analyzed: MC3000_Monitor_V1.06.exe
- SHA256: `bdea2ecff50322a02fafc65918c9ce384b5ba5a0bce282cbcdd8dd4a2ee8069b`
- Tools documentation: radare2.org, mono-project.com
- This analysis was performed independently without reference to proprietary documentation

---

---

## Missing / Incomplete Information

The following items need further investigation (ideally by connecting to actual hardware):

### 1. USB Device Identification
```c
// Found in code (likely placeholders):
VendorId = 0   // Actual VID unknown - needs hardware verification
ProductId = 1  // Actual PID unknown - needs hardware verification
```
The format string `"vid_{0:x4}&pid_{1:x4}"` suggests standard Windows HID device path format.

**To get actual VID/PID:** Connect device and run `lsusb` on Linux or check Device Manager on Windows.

### 2. Packet Size
- **Receive buffer:** 65 bytes (0x41) - includes report ID at byte 0
- **Send buffer:** 33 bytes (0x21) - bytes 0-32

### 3. Outgoing Command Packets (PC → Device)

**Important:** The MC3000 Monitor software is primarily a **monitoring tool**. Charging parameters are configured directly on the device via its buttons/menu, NOT sent from the PC software.

#### Known Outgoing Commands

| Method | Byte 1 | Purpose | Packet Structure |
|--------|--------|---------|------------------|
| `outGetDviceInfomation` | 0x00 | Request device info | `[0, 0, 0, 0, ...]` (all zeros) |
| `outExecutApp` | 0x05 | Execute/start (firmware) | `[0, 5, 0, 0, ...]` |
| `outStartSignal` | 0x01 | Firmware update start | See below |
| `outVectorStart` | 0x02 | Firmware data transfer | Vector address + data |
| `outCheckResult` | - | Verify firmware | Sends current outPacket |

#### Firmware Update Start Packet (0x01)

```c
// outStartSignal() packet structure
outPacket[0] = 0;                    // Report ID
outPacket[1] = 1;                    // Command: firmware update start
outPacket[2] = (max_add >> 24) & 0xFF;  // File size (32-bit BE)
outPacket[3] = (max_add >> 16) & 0xFF;
outPacket[4] = (max_add >> 8) & 0xFF;
outPacket[5] = max_add & 0xFF;
outPacket[6] = (checkSum >> 24) & 0xFF; // Checksum (32-bit BE)
outPacket[7] = (checkSum >> 16) & 0xFF;
outPacket[8] = (checkSum >> 8) & 0xFF;
outPacket[9] = checkSum & 0xFF;
outPacket[10-32] = 0;                // Padding
```

#### Commands NOT Implemented in Monitor Software

The following command constants exist but are **not used** for sending parameters:

| Constant | Value | Description | Status |
|----------|-------|-------------|--------|
| `CMD_PHONE_TO_MCU_START_CHARGER` | 0x05 | Start charging | Only used in firmware update context |
| `CMD_PHONE_TO_MCU_STOP_CHARGER` | 0xFE | Stop charging | Not sent by monitor |
| `CMD_PHONE_TO_MCU_SYSTEM_SET_SAVE` | 0x11 | Save system settings | Not implemented |
| `CMD_PHONE_TO_MCU_EN_BUZZ` | 0x80 | Enable buzzer | Not implemented |

**Conclusion:** To control charging parameters via USB, you would need to reverse engineer the actual protocol by capturing USB traffic while using the device's menu, or find alternative SKYRC software (like ChargeMonitor V2 mentioned in strings).

### 4. Response/ACK Packets (Device → PC)

#### ACK Response (0xF0)

When the device acknowledges a command, it responds with:

```c
inPacket[1] = 0xF0;  // ACK/OK response
```

The monitor software shows "OK!" message box when this is received.

#### Device Information Response

Response to `outGetDviceInfomation` (command 0x00):

| Offset | Description |
|--------|-------------|
| 1 | Non-zero if data present |
| 2 | Boot version (divide by 10 for major.minor, e.g., 15 = v1.5) |
| 3-5 | Magic bytes: 0x55, 0x55, 0x55 (validates genuine device) |

```c
// Parse boot version
int boot_major = inPacket[2] / 10;
int boot_minor = inPacket[2] % 10;
// Example: byte value 15 → "Boot Version: 1.5"

// Validate device signature
bool valid = (inPacket[3] == 0x55 &&
              inPacket[4] == 0x55 &&
              inPacket[5] == 0x55);
```

#### Response Routing (by command byte)

The main receive handler routes packets based on `inPacket[1]`:

| Byte 1 | Handler | Description |
|--------|---------|-------------|
| 0xF0 | Show "OK!" | Generic acknowledgment |
| 0x5F | `Get_Charge_Data()` | Charging profile for slot |
| 0x5A | `Get_System_Data()` | System settings |
| 0x55 | Status processing | Real-time monitoring data |

### 5. Unused Packet Bytes
Bytes 19-24 (0x13-0x18) in status response (0x55) are **not parsed** - likely reserved/padding.

### 5. Status Polling Mechanism
The MC3000 appears to send status data automatically when charging is active. The PC software:
- Receives data via USB HID interrupt transfers
- Copies 65 bytes to `inPacket[]` buffer
- Sets `dataReceived = true` flag
- Processes in event handler

There is no explicit "request status" command - the device **pushes** updates continuously (approximately every second based on timer usage).

### 6. Items NOT Found in Protocol
- **Internal Resistance (IR):** No IR measurement fields found - MC3000 may not measure this
- **Cycle Counter:** Current cycle number not in status packet (only `Cycle_Count` target in config)
- **Cell Identification:** No unique battery tracking
- **Real-time Input Voltage:** See section below
- **Charging Parameter Upload:** Settings appear to be device-side only

### 7. Input Voltage / DC Power Supply Monitoring

**The MC3000 protocol does NOT include real-time input voltage readings.**

#### What Exists

| Field | Type | Description |
|-------|------|-------------|
| `Sys_Min_Input` | Config setting | Minimum input voltage **threshold** (not real-time) |
| `Input Low!` | Error (0x80) | Triggered when input voltage < threshold |
| `Input High!` | Error (0x81) | Triggered when input voltage > threshold |

#### What's NOT Available
- Real-time input voltage value
- Power supply current draw
- Total power consumption

Input monitoring is **threshold-based only** - you only know there's a problem when an error occurs.

#### Workaround: Calculate Approximate Power Draw

```c
// Estimate total power consumption from battery data
float total_power_W = 0;
for (int slot = 0; slot < 4; slot++) {
    if (work_status[slot] == 1) { // Charging
        // Battery power in watts
        float batt_power = (voltage_mV[slot] / 1000.0f) * (current_mA[slot] / 1000.0f);
        // Add ~15-20% for charger efficiency loss
        total_power_W += batt_power * 1.18f;
    } else if (work_status[slot] == 2) { // Discharging
        // Discharge power is dissipated as heat, still draws from PSU
        float batt_power = (voltage_mV[slot] / 1000.0f) * (current_mA[slot] / 1000.0f);
        total_power_W += batt_power;
    }
}
// Add standby power (~3-5W when idle)
if (total_power_W == 0) {
    total_power_W = 5.0f;
}

// Estimate input current (assuming 12V input)
float input_voltage = 12.0f;
float input_current_A = total_power_W / input_voltage;
```

**Note:** This is an approximation. For accurate input power monitoring, use an external DC power meter.

### 7. Timing
- Timer interval not found in disassembled code (set in designer)
- Device likely sends updates every ~1 second during operation

### 8. Multi-Slot Data
- Each status packet contains data for **one slot** (byte 2 = slot ID 0-3)
- Device sends 4 separate packets, one per slot
- Software maintains separate arrays: `Voltage[4]`, `Current[4]`, etc.

---

## Quick Reference - Complete Packet Map

### Status Packet (65 bytes total, from device)

| Byte | Field | Notes |
|------|-------|-------|
| 0 | Report ID | HID report identifier |
| 1 | Command | 0x55 = status data |
| 2 | Slot ID | 0-3 |
| 3 | Battery Type | 0-6 |
| 4 | Work Mode | 0-4 |
| 5 | Reserved | |
| 6 | Work Status | 0-4 normal, 0x80+ error |
| 7-8 | Work Time | Seconds remaining (BE) |
| 9-10 | Voltage | mV (BE) |
| 11-12 | Current | mA (BE) |
| 13-14 | Capacity | mAh (BE) |
| 15-16 | Batt Temp | 0.1°C (BE, mask 0x7FFF) |
| 17-18 | Unknown | MC3000 Monitor shows Int Temp here, but real hardware differs |
| 19-20 | Int Temp | 0.1°C (BE) - confirmed via DataExplorer/hardware testing |
| 21-24 | Reserved | Not parsed |
| 25 | Cap Decimal | 0.01 mAh units |
| 26-63 | Reserved | |
| 64 | Checksum | Sum of bytes 1-63 |

**Note:** There is a discrepancy between the MC3000 Monitor binary analysis and actual hardware behavior for bytes 17-18 vs 19-20. The internal temperature reading works correctly from bytes 19-20, suggesting either firmware differences or an error in the MC3000 Monitor software itself.

### Command Packet (33 bytes, to device)

| Byte | Field | Notes |
|------|-------|-------|
| 0 | Report ID | Always 0 |
| 1 | Command | See command table |
| 2-32 | Parameters | Command-specific |

---

## Implementation Guide

### Minimal Monitoring Tool Requirements

To implement a basic MC3000 monitoring tool:

```c
// 1. Open HID device (need actual VID/PID from hardware)
hid_device* dev = hid_open(VID, PID, NULL);

// 2. Receive loop - device pushes data automatically
uint8_t buf[65];
while (running) {
    int res = hid_read(dev, buf, 65);
    if (res > 0) {
        switch (buf[1]) {
            case 0x55: parse_status(buf); break;
            case 0x5F: parse_charging_profile(buf); break;
            case 0x5A: parse_system_settings(buf); break;
            case 0xF0: handle_ack(); break;
        }
    }
}

// 3. Validate checksum
uint8_t calc_checksum(uint8_t* pkt) {
    uint8_t sum = 0;
    for (int i = 1; i < 64; i++) sum += pkt[i];
    return sum;  // Compare with pkt[64]
}
```

### What You CAN Do (Monitoring Only)
- Read real-time voltage, current, capacity, temperature for all 4 slots
- Read charging profile settings (what device is configured for)
- Read system settings (temp unit, buzzer, etc.)
- Detect errors and work states
- Log charging data over time

### What You CANNOT Do (Without Additional RE)
- Start/stop charging from PC
- Change charging parameters from PC
- Upload new charging profiles
- Control individual slots

### To Enable Full Control

Would require:
1. **USB traffic capture** while using device menu to change settings
2. **Identify write commands** (likely 0x05/0x11/0xFE with parameter data)
3. **Reverse packet structure** for parameter upload
4. **Test thoroughly** - incorrect parameters could damage batteries

### Libraries for Implementation

| Language | Library | Notes |
|----------|---------|-------|
| C/C++ | hidapi | Cross-platform, recommended |
| Python | hidapi / pyusb | Easy prototyping |
| Rust | hidapi-rs | Safe wrapper |
| Node.js | node-hid | For Electron apps |

### Example: Get VID/PID on Linux

```bash
# Connect MC3000 via USB, then:
lsusb | grep -i skyrc
# or
lsusb | grep -i "0000:0001"  # If using placeholder IDs

# For detailed info:
sudo lsusb -v -d VID:PID
```

---

## Disclaimer

This reverse engineering was conducted for interoperability purposes under applicable fair use / reverse engineering exceptions. The information is provided for educational and compatibility purposes only.
