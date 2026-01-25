# Extra Chemistries in MC3000 APK

This document summarizes battery chemistries and related defaults found in the Android APK
(`MC3000.apk`), beyond the common Li‑ion/NiMH/NiCd list. Source: decompiled
`com/skyrc/mc3000/tools/Constant.java`.

---

## Chemistry List (from APK)

`Constant.voltage_type` defines the UI/logic chemistry set:

Index | Name | Notes
---|---|---
0 | LiIon | Standard Li‑ion
1 | LiFe | LiFePO4
2 | LiIo4.35 | LiHV 4.35V
3 | NiMH | Nickel‑metal hydride
4 | NiCd | Nickel‑cadmium
5 | NiZn | Nickel‑zinc
6 | Eneloop | Sanyo/Panasonic Eneloop (NiMH variant)
7 | RAM | Listed in APK, not a common chemistry label
8 | LTO | Lithium‑titanate oxide
9 | Na‑Lion | Sodium‑ion

These extra entries are likely present for shared code with other chargers or
future firmware features.

---

## Charge Mode Mapping (UI)

`DeviceUtil.getModels()` uses chemistry name to choose the charge mode list:

- **Li‑type modes**: `charge_model_li`
  - Applies to: LiIon, LiFe, LiIo4.35, LTO, Na‑Lion
- **NiZn / RAM modes**: `charge_model_NiZn`
  - Applies to: NiZn, RAM
- **Other modes**: `charge_model_other`
  - Applies to: NiMH, NiCd, Eneloop

`charge_model_li` includes: Charge, Refresh, Storage, Discharge, Cycle
`charge_model_NiZn` includes: Charge, Refresh, Discharge, Cycle
`charge_model_other` includes: Charge, Refresh, Break‑In, Discharge, Cycle

---

## Default Voltage Ranges (from APK)

All values below are **mV** and stored as floats in `Constant`.
Each array index corresponds to the chemistry index above.

### Discharge end voltage range ("on_keep_voltage_ly_*")
- Max: `on_keep_voltage_ly_max`
- Default: `on_keep_voltage_ly_defoult`
- Min: `on_keep_voltage_ly_min`

Index | Name | Min | Default | Max
---|---|---:|---:|---:
0 | LiIon | 2500 | 3000 | 3650
1 | LiFe | 2000 | 2900 | 3150
2 | LiIo4.35 | 2650 | 3300 | 3750
3 | NiMH | 500 | 1000 | 1100
4 | NiCd | 500 | 1000 | 1100
5 | NiZn | 1000 | 1200 | 1300
6 | Eneloop | 500 | 900 | 1000
7 | RAM | 500 | 900 | 1300
8 | LTO | 1500 | 1800 | 2250
9 | Na‑Lion | 1500 | 2000 | 3500

### Charge end voltage range ("in_keep_voltage_ly_*")
- Max: `in_keep_voltage_ly_max`
- Default: `in_keep_voltage_ly_defoult`
- Min: `in_keep_voltage_ly_min`

Index | Name | Min | Default | Max
---|---|---:|---:|---:
0 | LiIon | 4000 | 4200 | 4250
1 | LiFe | 3400 | 3600 | 3650
2 | LiIo4.35 | 4100 | 4350 | 4400
3 | NiMH | 1470 | 1650 | 1800
4 | NiCd | 1470 | 1650 | 1800
5 | NiZn | 1850 | 1900 | 1950
6 | Eneloop | 1470 | 1650 | 1800
7 | RAM | 1400 | 1650 | 1700
8 | LTO | 2600 | 2850 | 2900
9 | Na‑Lion | 3200 | 4000 | 4150

### Storage voltage range ("over_keep_voltage_ly_*")
- Max: `over_keep_voltage_ly_max`
- Default: `over_keep_voltage_ly_defoult`
- Min: `over_keep_voltage_ly_min`

Index | Name | Min | Default | Max
---|---|---:|---:|---:
0 | LiIon | 3980 | 4150 | 4180
1 | LiFe | 3380 | 3550 | 3580
2 | LiIo4.35 | 4080 | 4250 | 4330
3 | NiMH | 1300 | 1350 | 1450
4 | NiCd | 1300 | 1350 | 1450
5 | NiZn | 1500 | 1600 | 1880
6 | Eneloop | 1300 | 1350 | 1450
7 | RAM | 1400 | 1450 | 1500
8 | LTO | 2580 | 2700 | 2830
9 | Na‑Lion | 3980 | 4150 | 4180

### Li storage voltage range ("li_storge_vol_*")
These are 4 entries only (no chemistry mapping in code). They appear to be
li‑type storage defaults for a subset of Li chemistries.

Index | Value (mV) | Range
---|---:|---
0 | 3650 / 3800 / 4000 | Min / Default / Max
1 | 3150 / 3300 / 3400 | Min / Default / Max
2 | 3750 / 3900 / 4100 | Min / Default / Max
3 | 2250 / 2400 / 2600 | Min / Default / Max

---

## Notes / Hypotheses

- **RAM** is likely a generic “battery” placeholder used by other SkyRC models.
- **LTO** and **Na‑Lion** appear fully parameterized, suggesting the codebase is
  shared with newer hardware even if MC3000 firmware does not expose them.
- The NiZn/RAM mode mapping excludes “Storage” and “Break‑In”, consistent with
  the APK’s `charge_model_NiZn` array.

---

## Source Location

- `com/skyrc/mc3000/tools/Constant.java`
- `com/skyrc/mc3000/utils/DeviceUtil.java`

