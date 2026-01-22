# MC3000 GUI Examples

Example scripts demonstrating the MC3000 Python API.

## Running Examples

From the examples directory:

```bash
cd examples
python read_slot_data.py
```

Or from anywhere with the package installed:

```bash
python -m examples.read_slot_data
```

## Examples

### read_slot_data.py

Read real-time measurements from all 4 slots (voltage, current, capacity, etc).

```bash
python read_slot_data.py
```

### read_slot_settings.py

Read programmed slot configuration (battery type, charge/discharge currents, etc).

```bash
python read_slot_settings.py
```

### monitor_charging.py

Continuously monitor a single slot during charging with live updates.

```bash
python monitor_charging.py 1   # Monitor slot 1
```

### list_profiles.py

List all available charging profiles (built-in and user-created).

```bash
python list_profiles.py
```

## Using as a Library

After installing the package, you can import modules directly:

```python
from mc3000_usb import MC3000USB
from mc3000_protocol import BATTERY_TYPES, SlotData
from mc3000_profiles import ProfileManager
from mc3000_config import SlotConfig
```
