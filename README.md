# SKYRC MC3000 Battery Charger GUI

[![PyPI version](https://badge.fury.io/py/skyrc-mc3000-gui.svg)](https://pypi.org/project/skyrc-mc3000-gui/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Cross-platform Python GUI for monitoring and controlling the SKYRC MC3000 battery charger.

## Features

- Real-time monitoring of all 4 charging slots
- Voltage, current, capacity, temperature, resistance, power, energy display
- Slot configuration with battery type selection
- Profile management (save/load charging profiles)
- Charging graphs with history
- Backup and restore slot configurations
- Color-coded status indicators
- Cross-platform (Windows, macOS, Linux)

## Installation

### From PyPI

```bash
pip install skyrc-mc3000-gui
```

### From Source

```bash
git clone https://github.com/nuclearcat/SkyRCMC3000-GUI.git
cd SkyRCMC3000-GUI
pip install .
```

### Linux Dependencies

On Linux, you also need libhidapi:
```bash
# Debian/Ubuntu
sudo apt install libhidapi-hidraw0

# Fedora
sudo dnf install hidapi

# Arch
sudo pacman -S hidapi
```

## Usage

### Run the GUI

```bash
mc3000-gui
```

Or run directly from source:
```bash
python main.py
```

### Command-line Tools

```bash
# Backup/restore tool
mc3000-backup --help
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

## Documentation

- [Protocol Documentation](docs/protocol.rst) - MC3000 USB HID protocol details
- [Protocol Notes](docs/protocol_notes.md) - Additional protocol observations

## Example Code

### Reading Slot Data

```python
from mc3000_usb import MC3000USB
from mc3000_protocol import parse_slot_data

# Connect to charger
usb = MC3000USB()
usb.connect()

# Get real-time data for slot 0
data = usb.get_slot_data(0)
if data:
    print(f"Voltage: {data.voltage_v:.3f} V")
    print(f"Current: {data.current_ma} mA")
    print(f"Capacity: {data.capacity_mah} mAh")
    print(f"Temperature: {data.temperature_c:.1f} C")

usb.disconnect()
```

### Reading Slot Configuration

```python
from mc3000_usb import MC3000USB

usb = MC3000USB()
usb.connect()

# Get settings for slot 0
settings = usb.get_slot_settings(0)
if settings:
    print(f"Battery Type: {settings.battery_type}")
    print(f"Capacity: {settings.capacity_mah} mAh")
    print(f"Charge Current: {settings.charge_current_ma} mA")

usb.disconnect()
```

### Using Profiles

```python
from mc3000_profiles import ProfileManager

pm = ProfileManager()

# List available profiles
for name in pm.list_profiles():
    print(f"Profile: {name}")

# Get a profile
profile = pm.get_profile("NiMH AA 2000mAh")
```

## Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [GitHub Repository](https://github.com/nuclearcat/SkyRCMC3000-GUI)
- [PyPI Package](https://pypi.org/project/skyrc-mc3000-gui/)
- [Issue Tracker](https://github.com/nuclearcat/SkyRCMC3000-GUI/issues)

## Acknowledgments

Protocol implementation based on [GNU DataExplorer](https://www.nongnu.org/dataexplorer/) by Winfried Bruegmann.
