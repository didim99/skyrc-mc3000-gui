# SKYRC MC3000 Battery Charger GUI

Cross-platform Python GUI for monitoring the SKYRC MC3000 battery charger.

## Installation

```bash
pip install .
```

On Linux, you also need libhidapi:
```bash
sudo apt install libhidapi-hidraw0
```

## Usage

```bash
mc3000-gui
```

Or run directly:
```bash
python main.py
```

## Linux USB Access

To access the MC3000 without root, create `/etc/udev/rules.d/99-mc3000.rules`:

```
SUBSYSTEM=="usb", ATTR{idVendor}=="0000", ATTR{idProduct}=="0001", MODE="0666"
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0000", ATTRS{idProduct}=="0001", MODE="0666"
```

Then reload:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Features

- Real-time monitoring of all 4 charging slots
- Voltage, current, capacity, temperature, resistance, power, energy display
- Color-coded status indicators
- Cross-platform (Windows, macOS, Linux)
